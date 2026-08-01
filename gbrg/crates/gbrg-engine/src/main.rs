//! `gbrg-engine` — the authoritative GBRG containment engine as an HTTP service.
//!
//! One POST endpoint runs the REAL `gbrg_core::emit_containment_artifact` (via
//! `gbrg_analyze::containment::run`) over a topology supplied in the request body,
//! and returns the `ContainmentProofArtifact` JSON. This is what the
//! prophet-platform Go `gbrg-containment` front-door calls so there is ONE
//! authoritative algorithm rather than a Go copy that can drift.
//!
//! Endpoints (bind 0.0.0.0:$PORT, default 8080):
//!
//!   GET  /healthz     — liveness/readiness (chart probe path)
//!   POST /containment — body is a topology JSON (source/direction/scope/keep_labels/
//!                       cut/allow/edges); response is a ContainmentProofArtifact.

use tiny_http::{Header, Method, Response, Server};

fn json_header() -> Header {
    Header::from_bytes(&b"Content-Type"[..], &b"application/json"[..]).unwrap()
}

fn main() {
    let port = std::env::var("PORT").unwrap_or_else(|_| "8080".to_string());
    let addr = format!("0.0.0.0:{port}");
    let server = Server::http(&addr).unwrap_or_else(|e| {
        eprintln!("gbrg-engine: cannot bind {addr}: {e}");
        std::process::exit(1);
    });
    eprintln!("gbrg-engine serving on {addr} (GET /healthz, POST /containment)");

    for mut req in server.incoming_requests() {
        let method = req.method().clone();
        let url = req.url().to_string();
        let mut body = String::new();
        if *req.method() == Method::Post {
            let _ = req.as_reader().read_to_string(&mut body);
        }
        let (code, out) = handle(&method, &url, &body);
        let response = Response::from_string(out)
            .with_status_code(code)
            .with_header(json_header());
        let _ = req.respond(response);
    }
}

/// Route + compute a response. Pure (no I/O) so it is unit-testable without a socket.
fn handle(method: &Method, url: &str, body: &str) -> (u16, String) {
    match (method, url) {
        (Method::Get, "/healthz") => (
            200,
            r#"{"status":"ok","service":"gbrg-engine"}"#.to_string(),
        ),
        (Method::Post, "/containment") => match gbrg_analyze::containment::run(body) {
            Ok(json) => (200, json),
            // The engine's own errors are the caller's 400s (bad topology).
            Err(e) => (400, format!(r#"{{"error":{}}}"#, quote(&e))),
        },
        (Method::Get, "/containment") | (Method::Post, "/healthz") => {
            (405, r#"{"error":"method not allowed"}"#.to_string())
        }
        _ => (404, r#"{"error":"not found"}"#.to_string()),
    }
}

/// Minimal JSON string quoting for the error message (no serde dep needed here).
fn quote(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push(' '),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    const FOOTHOLD: &str = r#"{"source":"vvv-648e9d56f1a","direction":"downstream","scope":"full","allow":["edr-epp"],"edges":[
        {"from":"vvv-648e9d56f1a","to":"wks-2970","label":"SMB"},
        {"from":"wks-2970","to":"dc-01","label":"SMB"},
        {"from":"vvv-648e9d56f1a","to":"edr-epp","label":"EDR"}]}"#;

    #[test]
    fn healthz_ok() {
        let (code, body) = handle(&Method::Get, "/healthz", "");
        assert_eq!(code, 200);
        assert!(body.contains("\"ok\""));
    }

    #[test]
    fn containment_runs_the_real_engine() {
        let (code, body) = handle(&Method::Post, "/containment", FOOTHOLD);
        assert_eq!(code, 200, "body={body}");
        // The authoritative engine's artifact, humanized.
        assert!(
            body.contains("\"epistemicLevel\":\"empirical\""),
            "body={body}"
        );
        assert!(
            body.contains("edr-epp"),
            "residual keeps the allow-listed EDR: {body}"
        );
    }

    #[test]
    fn bad_topology_is_a_400() {
        let (code, _) = handle(&Method::Post, "/containment", "not json");
        assert_eq!(code, 400);
    }

    #[test]
    fn method_and_route_guards() {
        assert_eq!(handle(&Method::Get, "/containment", "").0, 405);
        assert_eq!(handle(&Method::Get, "/nope", "").0, 404);
    }
}
