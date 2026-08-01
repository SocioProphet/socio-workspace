//! Tests for the authoritative `gbrg-containment` CLI logic.
//!
//! Drives `gbrg_analyze::containment::run` over the SAME network topology the
//! prophet-platform Go front-door fakes, proving the real engine (a) agrees on the
//! containment result and (b) humanizes NodeIds back to endpoint names.

use serde_json::Value;

// The foothold topology: an SMB chain to a high-value DC + file server, an RDP
// path, and the allow-listed EDR control channel.
const TOPO_EDGES: &str = r#"
  [ {"from":"vvv-648e9d56f1a","to":"wks-2970","label":"SMB"},
    {"from":"wks-2970","to":"dc-01","label":"SMB"},
    {"from":"dc-01","to":"file-srv","label":"SMB"},
    {"from":"vvv-648e9d56f1a","to":"wks-0d06","label":"RDP"},
    {"from":"vvv-648e9d56f1a","to":"edr-epp","label":"EDR"} ]"#;

fn run(json: &str) -> Value {
    let out = gbrg_analyze::containment::run(json).expect("run ok");
    serde_json::from_str(&out).expect("valid artifact JSON")
}

fn names(v: &Value, key: &str) -> Vec<String> {
    v[key]
        .as_array()
        .unwrap()
        .iter()
        .map(|x| x.as_str().unwrap().to_string())
        .collect()
}

#[test]
fn full_isolation_contains_all_but_the_allowlisted_edr() {
    let input = format!(
        r#"{{"source":"vvv-648e9d56f1a","direction":"downstream","scope":"full","allow":["edr-epp"],"edges":{TOPO_EDGES}}}"#
    );
    let a = run(&input);

    assert_eq!(
        a["baselineReachableCount"], 5,
        "foothold reaches all 5 nodes"
    );
    assert_eq!(
        a["containedCount"], 4,
        "everything but the EDR channel is contained"
    );
    assert_eq!(
        names(&a, "residualReachable"),
        vec!["edr-epp"],
        "only the allow-listed EDR remains"
    );
    assert_eq!(
        a["source"], "vvv-648e9d56f1a",
        "source is humanized back to its name"
    );
    assert_eq!(
        a["epistemicLevel"], "empirical",
        "a real sever is observed/empirical"
    );
    assert_eq!(a["severedScope"], "full");
}

#[test]
fn selective_keeps_rdp_but_cuts_the_smb_chain() {
    let input = format!(
        r#"{{"source":"vvv-648e9d56f1a","direction":"downstream","scope":"selective","keep_labels":["RDP","EDR"],"allow":["edr-epp"],"edges":{TOPO_EDGES}}}"#
    );
    let a = run(&input);

    let residual = names(&a, "residualReachable");
    assert!(
        residual.contains(&"wks-0d06".to_string()),
        "RDP path stays reachable: {residual:?}"
    );
    assert!(
        residual.contains(&"edr-epp".to_string()),
        "EDR stays reachable: {residual:?}"
    );
    assert!(
        !residual.contains(&"dc-01".to_string()),
        "the SMB chain to the DC is cut: {residual:?}"
    );
    assert_eq!(
        a["containedCount"], 3,
        "the three SMB-chain nodes are contained"
    );
    assert_eq!(a["epistemicLevel"], "empirical");
}

#[test]
fn no_op_sever_is_downgraded_to_speculative() {
    // A source that reaches nothing: the sever contains nothing, so the engine must
    // NOT present it as a clean containment.
    let input = r#"{"source":"lonely-host","direction":"downstream","scope":"full","edges":[{"from":"other","to":"x","label":"SMB"}]}"#;
    let a = run(input);
    assert_eq!(a["containedCount"], 0);
    assert_eq!(
        a["epistemicLevel"], "speculative",
        "a no-op sever is never a settled containment"
    );
}

#[test]
fn bad_input_is_a_clean_error() {
    assert!(gbrg_analyze::containment::run("not json").is_err());
    assert!(
        gbrg_analyze::containment::run(r#"{"scope":"full","edges":[]}"#).is_err(),
        "missing source"
    );
    assert!(
        gbrg_analyze::containment::run(r#"{"source":"f","scope":"sideways","edges":[]}"#).is_err(),
        "bad scope"
    );
}
