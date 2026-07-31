// E2E fixture for gbrg-analyze.
//
// `helper` is an UNTESTED function called by FIVE other functions in this file,
// giving it a real fan-in (in-degree) of 5 once ingested into the graph. The
// whole point: the pipeline must recover that fan-in off the frozen index and
// derive a real `epistemicLevel` for it (speculative — reached by no test,
// dependents within the default bounded threshold of 15).

pub fn helper() -> i32 {
    40 + 2
}

pub fn caller_one() -> i32 {
    helper()
}

pub fn caller_two() -> i32 {
    helper()
}

pub fn caller_three() -> i32 {
    helper()
}

pub fn caller_four() -> i32 {
    helper()
}

pub fn caller_five() -> i32 {
    helper()
}
