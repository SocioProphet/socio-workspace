//! `gbrg-engine` — the authoritative GBRG containment engine as an HTTP service.
//!
//! Runs the REAL `gbrg_core::emit_containment_artifact` (via
//! `gbrg_analyze::containment::run`) and returns the `ContainmentProofArtifact`
//! JSON. This is the ONE authoritative containment service — it fully replaces the
//! retired Go `gbrg-containment` reimplementation (there is no Go copy to drift).
//!
//! Endpoints (bind 0.0.0.0:$PORT, default 8080):
//!
//!   GET  /healthz                          — liveness/readiness (chart probe path)
//!   GET  /containment?scope=full|selective — sever the built-in demo foothold (the
//!                                            drop-in for the old Go GET interface)
//!   POST /containment                      — body is a topology JSON
//!                                            (source/direction/scope/keep_labels/cut/
//!                                            allow/edges); arbitrary graphs

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
    let (path, query) = url.split_once('?').unwrap_or((url, ""));
    match (method, path) {
        (Method::Get, "/healthz") => (
            200,
            r#"{"status":"ok","service":"gbrg-engine"}"#.to_string(),
        ),
        // The drop-in for the retired Go gbrg-containment GET interface: sever the
        // built-in demo foothold at the requested scope.
        (Method::Get, "/containment") => run_or_400(&demo_topology_json(scope_from_query(query))),
        (Method::Post, "/containment") => run_or_400(body),
        (Method::Post, "/healthz") => (405, r#"{"error":"method not allowed"}"#.to_string()),
        _ => (404, r#"{"error":"not found"}"#.to_string()),
    }
}

/// Run the engine over a topology JSON, mapping engine errors to 400 (bad topology).
fn run_or_400(input: &str) -> (u16, String) {
    match gbrg_analyze::containment::run(input) {
        Ok(json) => (200, json),
        Err(e) => (400, format!(r#"{{"error":{}}}"#, quote(&e))),
    }
}

/// Extract `scope` from a query string; defaults to `full`.
fn scope_from_query(query: &str) -> &str {
    query
        .split('&')
        .find_map(|kv| kv.strip_prefix("scope="))
        .filter(|s| *s == "selective" || *s == "full")
        .unwrap_or("full")
}

/// The built-in demo foothold: an SMB chain to a high-value DC + file server, an RDP
/// path, and the allow-listed EDR channel — the same fixture the retired Go service
/// served, now computed by the authoritative engine.
fn demo_topology_json(scope: &str) -> String {
    format!(
        r#"{{"source":"vvv-648e9d56f1a","direction":"downstream","scope":"{scope}","keep_labels":["RDP","EDR"],"allow":["edr-epp"],"edges":[
        {{"from":"vvv-648e9d56f1a","to":"wks-2970","label":"SMB"}},
        {{"from":"wks-2970","to":"dc-01","label":"SMB"}},
        {{"from":"dc-01","to":"file-srv","label":"SMB"}},
        {{"from":"vvv-648e9d56f1a","to":"wks-0d06","label":"RDP"}},
        {{"from":"vvv-648e9d56f1a","to":"edr-epp","label":"EDR"}}]}}"#
    )
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
        assert_eq!(handle(&Method::Post, "/healthz", "").0, 405);
        assert_eq!(handle(&Method::Get, "/nope", "").0, 404);
    }

    #[test]
    fn get_demo_full_severs_the_foothold() {
        let (code, body) = handle(&Method::Get, "/containment?scope=full", "");
        assert_eq!(code, 200, "body={body}");
        assert!(
            body.contains("\"epistemicLevel\":\"empirical\""),
            "body={body}"
        );
        assert!(
            body.contains("\"containedCount\":4"),
            "full demo contains 4: {body}"
        );
        assert!(body.contains("edr-epp"), "residual keeps the EDR: {body}");
    }

    #[test]
    fn get_demo_selective_keeps_rdp() {
        let (code, body) = handle(&Method::Get, "/containment?scope=selective", "");
        assert_eq!(code, 200, "body={body}");
        assert!(
            body.contains("\"severedScope\":\"selective\""),
            "body={body}"
        );
        assert!(
            body.contains("wks-0d06"),
            "selective keeps the RDP path: {body}"
        );
    }

    #[test]
    fn get_demo_defaults_to_full() {
        assert_eq!(scope_from_query(""), "full");
        assert_eq!(scope_from_query("scope=selective"), "selective");
        assert_eq!(scope_from_query("scope=bogus"), "full");
        let (code, body) = handle(&Method::Get, "/containment", "");
        assert_eq!(code, 200);
        assert!(body.contains("\"severedScope\":\"full\""), "body={body}");
    }
}
