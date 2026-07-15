#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "orion-osiris-excavation-migration.yaml"

REQUIRED_ALLOWED = {
    "map_first_ux_pattern",
    "grouped_layer_grammar",
    "selected_entity_panel_pattern",
    "fixture_scenario_sketches",
    "source_ledger_metadata",
    "public_feed_candidate_inventory",
}

REQUIRED_BLOCKED = {
    "stealthFetch",
    "scanner_route_runtime",
    "sweep_route_runtime",
    "osint_panel_execution_behavior",
    "ungated_recon_ui",
    "inherited_route_handlers_as_authority",
    "live_feed_truth_assumptions",
    "credentials_or_api_keys_from_osiris",
    "customer_or_real_target_data_in_osiris",
}

REQUIRED_REPOS = {
    "mdheller/osiris",
    "SocioProphet/gaia-world-model",
    "SocioProphet/orion-field-intelligence",
    "SocioProphet/SCOPE-D",
    "SocioProphet/prophet-platform",
    "SocioProphet/ontogenesis",
    "SocioProphet/sociosphere",
}

REQUIRED_VALIDATION_COMMANDS = {
    "python3 scripts/validate_orion_osiris_source_records.py",
    "python3 scripts/validate_facility_risk_fixtures.py",
}


def fail(message: str) -> int:
    print(f"ERR: {message}", file=sys.stderr)
    return 1


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def as_list(value: Any, field: str) -> list[Any]:
    require(isinstance(value, list) and value, f"{field} must be non-empty list")
    return value


def as_dict(value: Any, field: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{field} must be mapping")
    return value


def collect_repos(value: Any) -> set[str]:
    repos: set[str] = set()
    if isinstance(value, dict):
        if isinstance(value.get("repo"), str):
            repos.add(value["repo"])
        # `owner` carries a repo slug too (owner: SocioProphet/sociosphere) — the
        # coordinating repo is a participant in the lane, and REQUIRED_REPOS has
        # always expected it. Guard on "/" so only slug-shaped owners count.
        owner = value.get("owner")
        if isinstance(owner, str) and "/" in owner:
            repos.add(owner)
        for child in value.values():
            repos |= collect_repos(child)
    elif isinstance(value, list):
        for child in value:
            repos |= collect_repos(child)
    return repos


def main() -> int:
    if yaml is None:
        return fail("PyYAML is required")
    try:
        data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
        require(isinstance(data, dict), "registry must be mapping")
        require(data.get("kind") == "CrossRepoMigrationLane", "kind mismatch")
        require(data.get("version") == "0.1.0", "version mismatch")
        require(data.get("lane_id") == "orion-osiris-excavation-migration", "lane_id mismatch")
        require(data.get("coordination_issue") == "SocioProphet/sociosphere#406", "coordination issue mismatch")

        quarantine = as_dict(data.get("quarantine_source"), "quarantine_source")
        require(quarantine.get("repo") == "mdheller/osiris", "quarantine source must be mdheller/osiris")
        require(quarantine.get("status") == "quarantine_metadata_only", "OSIRIS source must remain quarantine metadata only")
        blocked_use = set(as_list(quarantine.get("blocked_use"), "quarantine blocked_use"))
        for term in ["product runtime", "production deployment", "scanner execution authority", "direct dependency for Prophet Platform"]:
            require(term in blocked_use, f"missing quarantine blocked use: {term}")

        lane = as_dict(data.get("product_lane"), "product_lane")
        repos = collect_repos(data)
        require(REQUIRED_REPOS <= repos, f"missing required repos: {sorted(REQUIRED_REPOS - repos)}")

        gaia = as_dict(lane.get("source_evidence_owner"), "source_evidence_owner")
        require(gaia.get("issue") == "SocioProphet/gaia-world-model#29", "Gaia issue mismatch")
        require("python3 scripts/validate_orion_osiris_source_records.py" in set(as_list(gaia.get("validation"), "Gaia validation")), "missing Gaia validation command")

        orion = as_dict(lane.get("field_intelligence_owner"), "field_intelligence_owner")
        require(orion.get("issue") == "SocioProphet/orion-field-intelligence#2", "Orion issue mismatch")
        require("python3 scripts/validate_facility_risk_fixtures.py" in set(as_list(orion.get("validation"), "Orion validation")), "missing Orion validation command")

        scope = as_dict(lane.get("recon_action_boundary"), "recon_action_boundary")
        require(scope.get("repo") == "SocioProphet/SCOPE-D", "SCOPE-D boundary repo mismatch")
        require(scope.get("issue") is None, "SCOPE-D issue must remain null while issues are disabled")
        require("docs/osiris-scanner-sweep-quarantine.md" in as_list(scope.get("current_artifacts"), "SCOPE-D artifacts"), "missing SCOPE-D quarantine doc")

        platform = as_dict(lane.get("runtime_binding_consumer"), "runtime_binding_consumer")
        require(platform.get("issue") == "SocioProphet/prophet-platform#506", "Prophet Platform issue mismatch")
        require(platform.get("status") == "planned_after_gaia_orion_contract_stabilization", "Prophet Platform must remain planned until seam stabilizes")

        allowed = set(as_list(data.get("allowed_inheritance"), "allowed_inheritance"))
        require(REQUIRED_ALLOWED <= allowed, f"missing allowed inheritance items: {sorted(REQUIRED_ALLOWED - allowed)}")
        blocked = set(as_list(data.get("blocked_inheritance"), "blocked_inheritance"))
        require(REQUIRED_BLOCKED <= blocked, f"missing blocked inheritance items: {sorted(REQUIRED_BLOCKED - blocked)}")

        deps = as_list(data.get("required_dependency_direction"), "required_dependency_direction")
        dep_pairs = {(d.get("from"), d.get("to"), d.get("relation")) for d in deps if isinstance(d, dict)}
        require(("mdheller/osiris", "SocioProphet/gaia-world-model", "excavation_metadata_to_source_records") in dep_pairs, "missing OSIRIS -> Gaia edge")
        require(("mdheller/osiris", "SocioProphet/orion-field-intelligence", "excavation_metadata_to_event_map_mvp") in dep_pairs, "missing OSIRIS -> Orion edge")
        require(("mdheller/osiris", "SocioProphet/SCOPE-D", "scanner_sweep_findings_to_quarantine_boundary") in dep_pairs, "missing OSIRIS -> SCOPE-D edge")
        require(("SocioProphet/orion-field-intelligence", "SocioProphet/prophet-platform", "marker_and_decision_artifacts_consumed_by_runtime_later") in dep_pairs, "missing Orion -> Prophet Platform edge")

        all_validation = set()
        for owner in [gaia, orion]:
            all_validation |= set(as_list(owner.get("validation"), "validation"))
        require(REQUIRED_VALIDATION_COMMANDS <= all_validation, "required validation commands missing")

        non_goals = "\n".join(as_list(data.get("non_goals"), "non_goals")).lower()
        for term in ["does not implement gaia adapters", "does not implement orion ui", "direct osiris code", "live target action"]:
            require(term in non_goals, f"missing non-goal term: {term}")
    except Exception as exc:
        return fail(str(exc))
    print("OK: Orion/OSIRIS migration lane registry validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
