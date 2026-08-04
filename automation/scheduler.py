"""
APScheduler-based job scheduler for autonomous registry management.

Jobs
----
- Every 1 minute  : drain the webhook event queue
- Every 1 hour    : registry rebuild (≈200 API calls)
- Every day 02:00 : deep scan       (≈800 API calls)
- On-demand       : trigger propagation for a specific repo
"""

import logging
import os
import signal
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

_ROOT = Path(__file__).resolve().parents[1]

# Tools the detectors/executors shell out to. Present in the repo; MUST be in the image.
_REQUIRED_TOOLS = (
    "check_vendored_artifact_graph.py",
    "lift_vendor_freshness_to_graph.py",
    "generate_workspace_resolved_lock.py",
    "validate_vendor_freshness.py",
    "check_source_exposure.py",
)


def preflight(root: Optional[Path] = None) -> None:
    """Fail FAST if this deployment cannot actually run the self-heal loop.

    A green heartbeat over a loop whose every job ImportErrors is the exact 'instruments lie'
    trap: the scheduler jobs catch their own import failures and keep beating, so `healthz`
    (heartbeat-only) reports alive while nothing heals. This eagerly imports the vendored
    kernel + engines the jobs need and verifies the tools they invoke exist; if anything is
    missing it raises, so the process exits non-zero (CrashLoopBackOff) — loud, not silent.
    """
    root = root or _ROOT
    try:
        # importing these pulls in third_party/procyber (the kernel) and engines/
        from automation import responder, executors, detectors  # noqa: F401
    except Exception as exc:
        raise RuntimeError(
            "preflight FAILED: the self-heal loop cannot import its dependencies — the image "
            "is missing the vendored kernel (third_party/) or engines/. Refusing to run a "
            f"daemon that would beat a green heartbeat while every job fails. Cause: {exc}"
        ) from exc
    missing = [f"tools/{t}" for t in _REQUIRED_TOOLS if not (root / "tools" / t).exists()]
    if missing:
        raise RuntimeError(
            f"preflight FAILED: required tool(s) missing from the image: {missing}. "
            "Detectors/executors that shell out to them would fail silently behind a green "
            "heartbeat. Refusing to start."
        )
    logger.info("preflight OK: kernel + engines import, %d tools present", len(_REQUIRED_TOOLS))

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.executors.pool import ThreadPoolExecutor
    _APSCHEDULER_AVAILABLE = True
except ImportError:  # pragma: no cover
    _APSCHEDULER_AVAILABLE = False
    BackgroundScheduler = None  # type: ignore[assignment,misc]

from automation.rate_limiter import RateLimiter
from automation.durable_queue import DurableQueue, state_dir
from automation import liveness

# API call cost estimates
COST_REGISTRY_REBUILD = 200
COST_DEEP_SCAN = 800
COST_PROCESS_EVENT = 10
COST_PROPAGATION = 50
ON_DEMAND_DELAY_SECONDS = 1

# Adaptive scheduling threshold
BACKOFF_USAGE_THRESHOLD = 0.80


class RegistryScheduler:
    """Wraps APScheduler with registry-specific jobs and adaptive backoff.

    Parameters
    ----------
    rate_limiter:
        Shared :class:`~automation.rate_limiter.RateLimiter` instance.
    event_queue:
        A :class:`queue.Queue` populated by the webhook handler.
    propagation_handler:
        Callable that receives a single event dict and processes it.
    registry_rebuild_fn:
        Callable invoked for hourly registry rebuilds.
    deep_scan_fn:
        Callable invoked for daily deep scans.
    """

    def __init__(
        self,
        rate_limiter: RateLimiter,
        event_queue=None,
        propagation_handler: Optional[Callable] = None,
        registry_rebuild_fn: Optional[Callable] = None,
        deep_scan_fn: Optional[Callable] = None,
    ) -> None:
        if not _APSCHEDULER_AVAILABLE:
            raise RuntimeError(
                "APScheduler is not installed. "
                "Run: pip install apscheduler"
            )

        self.rate_limiter = rate_limiter
        self.event_queue = event_queue
        self.propagation_handler = propagation_handler or self._noop_handler
        self.registry_rebuild_fn = registry_rebuild_fn or self._default_rebuild
        self.deep_scan_fn = deep_scan_fn or self._default_deep_scan

        self._metrics: dict = {
            "jobs_run": 0,
            "jobs_failed": 0,
            "jobs_skipped": 0,
            "events_processed": 0,
            "rebuilds_run": 0,
            "deep_scans_run": 0,
        }

        jobstores = {"default": MemoryJobStore()}
        executors = {"default": ThreadPoolExecutor(max_workers=4)}
        self._scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            timezone="UTC",
        )
        self._register_jobs()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background scheduler."""
        self._scheduler.start()
        logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """Stop the scheduler."""
        self._scheduler.shutdown(wait=wait)
        logger.info("Scheduler stopped")

    def trigger_propagation(self, repo_full_name: str) -> None:
        """On-demand: schedule an immediate propagation for *repo_full_name*."""
        self._scheduler.add_job(
            self._run_propagation,
            "date",
            run_date=datetime.now(timezone.utc) + timedelta(seconds=ON_DEMAND_DELAY_SECONDS),
            args=[{"repo": repo_full_name, "on_demand": True}],
            id=f"on_demand_{repo_full_name}_{int(time.time())}",
            misfire_grace_time=60,
        )
        logger.info("Queued on-demand propagation for %s", repo_full_name)

    def get_metrics(self) -> dict:
        return dict(self._metrics)

    # ------------------------------------------------------------------
    # Job registration
    # ------------------------------------------------------------------

    def _register_jobs(self) -> None:
        # Process webhook queue every minute
        self._scheduler.add_job(
            self._process_queue,
            "interval",
            minutes=1,
            id="process_queue",
            misfire_grace_time=30,
        )

        # Hourly registry rebuild
        self._scheduler.add_job(
            self._run_registry_rebuild,
            "interval",
            hours=1,
            id="registry_rebuild",
            misfire_grace_time=300,
        )

        # Daily deep scan at 02:00 UTC
        self._scheduler.add_job(
            self._run_deep_scan,
            "cron",
            hour=2,
            minute=0,
            id="deep_scan",
            misfire_grace_time=600,
        )

        # SENSE: run detectors every minute. Each detector turns a real failure into an
        # evidence-bearing beacon on the inbox (the front of the self-heal spine). Runs
        # ahead of the responder so a detected drift is decided on the next drain.
        self._scheduler.add_job(
            self._run_detectors,
            "interval",
            minutes=1,
            id="detectors",
            misfire_grace_time=30,
        )

        # Drain the beacon inbox every minute: the reasoned responder decides
        # fix/alert/escalate for each beacon and (execute=True) carries out verified-safe
        # auto-fixes. Detectors fill the inbox; the responder acts on it.
        self._scheduler.add_job(
            self._run_responder,
            "interval",
            minutes=1,
            id="responder",
            misfire_grace_time=30,
        )

        # OBSERVE: aggregate receipts into a scrapeable metrics file and log SRE alerts.
        self._scheduler.add_job(
            self._run_telemetry,
            "interval",
            minutes=1,
            id="telemetry",
            misfire_grace_time=30,
        )

        # LEARN (hourly): turn the receipt stream into safe policy-demotion recommendations
        # for a human to apply. Never mutates governance itself.
        self._scheduler.add_job(
            self._run_learning,
            "interval",
            hours=1,
            id="learning",
            misfire_grace_time=300,
        )

    # ------------------------------------------------------------------
    # Job implementations
    # ------------------------------------------------------------------

    def _process_queue(self) -> None:
        if self.event_queue is None:
            return

        processed = 0
        while not self.event_queue.empty():
            if self.rate_limiter.usage_fraction() >= BACKOFF_USAGE_THRESHOLD:
                logger.warning(
                    "Skipping queue processing: API usage > %.0f%%",
                    BACKOFF_USAGE_THRESHOLD * 100,
                )
                self._metrics["jobs_skipped"] += 1
                break

            if not self.rate_limiter.acquire(cost=COST_PROCESS_EVENT):
                self._metrics["jobs_skipped"] += 1
                break

            try:
                event = self.event_queue.get_nowait()
            except Exception:
                break

            self._run_propagation(event)
            processed += 1

        if processed:
            logger.info("Processed %d queued events", processed)

    def _run_propagation(self, event: dict) -> None:
        self._metrics["jobs_run"] += 1
        try:
            self.propagation_handler(event)
            self._metrics["events_processed"] += 1
        except Exception as exc:
            self._metrics["jobs_failed"] += 1
            logger.exception("Propagation failed for event %s: %s", event, exc)
            self._exponential_retry(self._run_propagation, event)

    def _run_registry_rebuild(self) -> None:
        if self.rate_limiter.usage_fraction() >= BACKOFF_USAGE_THRESHOLD:
            logger.warning("Skipping registry rebuild: API usage > 80%%")
            self._metrics["jobs_skipped"] += 1
            return

        if not self.rate_limiter.acquire(cost=COST_REGISTRY_REBUILD):
            self._metrics["jobs_skipped"] += 1
            return

        self._metrics["jobs_run"] += 1
        try:
            self.registry_rebuild_fn()
            self._metrics["rebuilds_run"] += 1
            logger.info("Registry rebuild complete")
        except Exception as exc:
            self._metrics["jobs_failed"] += 1
            logger.exception("Registry rebuild failed: %s", exc)

    def _run_learning(self) -> None:
        """Record safe policy-demotion recommendations from observed outcomes (advisory)."""
        self._metrics["jobs_run"] += 1
        try:
            from automation import learning
            recs = learning.run_once()
            for rec in recs:
                logger.warning("SELF-HEAL LEARNING recommend: %s", rec["rationale"])
        except Exception as exc:
            self._metrics["jobs_failed"] += 1
            logger.exception("Learning run failed: %s", exc)

    def _run_telemetry(self) -> None:
        """Aggregate receipts -> metrics.prom (scrapeable) and log any firing SRE alert."""
        self._metrics["jobs_run"] += 1
        try:
            from automation import telemetry
            metrics = telemetry.collect()
            telemetry.write_metrics_file(telemetry.render_prometheus(metrics))
            for alert in telemetry.alerts(metrics):
                logger.warning("SELF-HEAL ALERT [%s] %s: %s",
                               alert["severity"], alert["kind"], alert["message"])
        except Exception as exc:
            self._metrics["jobs_failed"] += 1
            logger.exception("Telemetry run failed: %s", exc)

    def _run_detectors(self) -> None:
        """Run the SENSE stage: emit evidence-bearing beacons for detected failures.

        Imported lazily so the scheduler still constructs when engines/yaml are
        unavailable; a detector failure records but never crashes the daemon.
        """
        self._metrics["jobs_run"] += 1
        try:
            from automation import detectors  # lazy: keeps engine/yaml import off the path
            emitted = detectors.run_detectors()
            if emitted:
                logger.info("Detectors emitted %d beacon(s)", len(emitted))
        except Exception as exc:
            self._metrics["jobs_failed"] += 1
            logger.exception("Detector run failed: %s", exc)

    def _run_responder(self) -> None:
        """Drain beacons and let the reasoned responder decide on each.

        The responder consumes the vendored semantic kernel (boundary -> IRI ->
        meet(Law, Evidence) -> action) and emits decision receipts to state/decisions/.
        Imported lazily so the scheduler still constructs when the kernel/vendor tree
        is unavailable (the responder job simply records the failure).
        """
        self._metrics["jobs_run"] += 1
        try:
            from automation import responder  # lazy: keeps kernel import off the hot path
            from automation.policy import load_policy
            from automation.suppression import Suppressor
            # execute=True: a verified-safe auto_fix (e.g. mirror-drift re-sync) is carried
            # out by its registered executor, which verifies the artifact and rolls back on
            # failure. The declared policy (registry/self-heal-policy.yaml) governs the
            # decision; if absent, the opinionated default applies. The suppressor coalesces a
            # persistent condition (e.g. a stale cross-repo vendor) to one decision per
            # policy cooldown, so the daemon does not re-escalate the same thing every cycle.
            receipts = responder.run_once(
                execute=True,
                policy=load_policy(),
                suppressor=Suppressor(state_dir() / "suppressions.json"),
            )
            if receipts:
                logger.info("Responder decided on %d beacon(s)", len(receipts))
            # Route escalation-class decisions to the WordOps ChatOps fabric — out of the log-void
            # into an operator's incident room (quarantine=A4 containment, escalate=A0 human).
            from automation import wordops
            for r in receipts:
                incident = wordops.route(r)
                if incident is not None:
                    logger.warning("WORDOPS incident [%s/%s] %s",
                                   incident["severity"], incident["autonomy_class"], incident["summary"])
            # The core decision cycle completed — record progress so health stays green.
            # If this job instead crashes every tick, progress goes stale and healthz degrades.
            liveness.progress()
        except Exception as exc:
            self._metrics["jobs_failed"] += 1
            logger.exception("Responder run failed: %s", exc)

    def _run_deep_scan(self) -> None:
        if self.rate_limiter.usage_fraction() >= BACKOFF_USAGE_THRESHOLD:
            logger.warning("Skipping deep scan: API usage > 80%%")
            self._metrics["jobs_skipped"] += 1
            return

        if not self.rate_limiter.acquire(cost=COST_DEEP_SCAN):
            self._metrics["jobs_skipped"] += 1
            return

        self._metrics["jobs_run"] += 1
        try:
            self.deep_scan_fn()
            self._metrics["deep_scans_run"] += 1
            logger.info("Deep scan complete")
        except Exception as exc:
            self._metrics["jobs_failed"] += 1
            logger.exception("Deep scan failed: %s", exc)

    # ------------------------------------------------------------------
    # Retry helper
    # ------------------------------------------------------------------

    def _exponential_retry(
        self,
        fn: Callable,
        arg: dict,
        max_retries: int = 3,
        base_delay: float = 2.0,
    ) -> None:
        for attempt in range(1, max_retries + 1):
            delay = base_delay ** attempt
            logger.info("Retry %d/%d in %.1fs", attempt, max_retries, delay)
            time.sleep(delay)
            try:
                fn(arg)
                return
            except Exception as exc:
                logger.warning("Retry %d failed: %s", attempt, exc)
        logger.error("All retries exhausted for %s", arg)

    # ------------------------------------------------------------------
    # Default no-op implementations
    # ------------------------------------------------------------------

    @staticmethod
    def _noop_handler(event: dict) -> None:
        logger.debug("No propagation handler registered; event=%s", event)

    @staticmethod
    def _default_rebuild() -> None:
        logger.info("[stub] Registry rebuild job ran")

    @staticmethod
    def _default_deep_scan() -> None:
        logger.info("[stub] Deep scan job ran")


# ----------------------------------------------------------------------------
# Honest default handler + beacon sink
# ----------------------------------------------------------------------------

def _beacon_inbox() -> DurableQueue:
    """The responder inbox: structured beacons a reasoned responder will consume."""
    return DurableQueue(state_dir() / "beacons")


def observe_and_beacon(event: dict) -> None:
    """Default event handler for the running daemon.

    OBSERVES a drained event and emits a structured beacon to the responder inbox.
    It deliberately takes NO world-remediating action: choosing fix vs. alert vs.
    escalate is the job of a reasoned responder (not wired in this change), so the
    honest default is to record and beacon, never to silently act or to pretend a
    simulation was a fix.
    """
    beacon = {
        "kind": "event_observed",
        "event": event,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "decision": "deferred: no reasoned responder wired yet",
    }
    _beacon_inbox().put(beacon)
    logger.info("Observed event; emitted beacon (repo=%s)", event.get("repo", "?"))


# ----------------------------------------------------------------------------
# Daemon entrypoint — what `python -m automation.scheduler` now actually runs
# ----------------------------------------------------------------------------

def build_scheduler(event_queue=None, propagation_handler: Optional[Callable] = None) -> "RegistryScheduler":
    """Construct a fully wired RegistryScheduler for the daemon.

    Uses the durable cross-process queue (so events enqueued by the webhook process
    are actually drained here) and the observe-and-beacon handler by default.
    """
    return RegistryScheduler(
        rate_limiter=RateLimiter(),
        event_queue=event_queue if event_queue is not None else DurableQueue(),
        propagation_handler=propagation_handler or observe_and_beacon,
    )


def run(heartbeat_interval: float = 30.0) -> None:
    """Start the scheduler and block, emitting a heartbeat each tick.

    This function was missing entirely: `python -m automation.scheduler` imported the
    module and exited, so the scheduler never ran (metrics recorded runs_total: 0).
    It now starts the background scheduler, writes a fresh heartbeat that
    `automation.healthz` checks, and shuts down cleanly on SIGTERM/SIGINT.
    """
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    interval = float(os.environ.get("SOCIOSPHERE_HEARTBEAT_INTERVAL", heartbeat_interval))

    # Refuse to run a daemon that would beat a green heartbeat while every job fails.
    preflight()

    scheduler = build_scheduler()
    scheduler.start()
    liveness.beat()       # first heartbeat before we start waiting
    liveness.progress()   # optimistic first progress; the responder job refreshes it each tick
    logger.info("Scheduler daemon started (heartbeat every %.0fs)", interval)

    stop = threading.Event()

    def _handle_signal(signum, _frame) -> None:
        logger.info("Received signal %s; shutting down", signum)
        stop.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    try:
        while not stop.wait(interval):
            liveness.beat()
    finally:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler daemon stopped")


def main() -> None:
    run()


if __name__ == "__main__":
    main()
