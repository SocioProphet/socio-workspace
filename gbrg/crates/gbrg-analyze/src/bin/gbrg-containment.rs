//! `gbrg-containment` — the authoritative containment engine as a CLI.
//!
//! Reads a topology JSON (a file argument, or stdin) and prints a
//! `ContainmentProofArtifact` on stdout. This is `gbrg_core::emit_containment_artifact`
//! over an arbitrary graph — the same algorithm the prophet-platform Go front-door
//! should exec instead of reimplementing.
//!
//! ```text
//!   gbrg-containment topology.json
//!   echo '{"source":"f","scope":"full","allow":["edr"],"edges":[...]}' | gbrg-containment
//! ```

use std::io::Read;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let input = if args.len() > 1 && args[1] != "-" {
        match std::fs::read_to_string(&args[1]) {
            Ok(s) => s,
            Err(e) => {
                eprintln!("gbrg-containment: read {}: {e}", args[1]);
                std::process::exit(1);
            }
        }
    } else {
        let mut buf = String::new();
        if let Err(e) = std::io::stdin().read_to_string(&mut buf) {
            eprintln!("gbrg-containment: read stdin: {e}");
            std::process::exit(1);
        }
        buf
    };

    match gbrg_analyze::containment::run(&input) {
        Ok(json) => println!("{json}"),
        Err(e) => {
            eprintln!("gbrg-containment: {e}");
            std::process::exit(1);
        }
    }
}
