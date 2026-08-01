//! # `gbrg-analyze` — demo CLI
//!
//! The demo surface for the END-TO-END GBRG pipeline. Point it at a real source
//! **file** OR a **directory** and it prints the emitted
//! [`BlastRadiusProofArtifact`]s as pretty JSON.
//!
//! ```text
//!   gbrg-analyze <file> [--lang rust|python|typescript]
//!   gbrg-analyze <dir>          # walks every supported source file under <dir>
//! ```
//!
//! For a single file, if `--lang` is omitted the language is guessed from the
//! extension (`.rs` → rust, `.py` → python, `.ts`/`.tsx`/`.mts`/`.cts` →
//! typescript). For a directory, each file's language is auto-detected by
//! extension and `--lang` is ignored; cross-file calls are resolved and test files
//! wire `TESTED_BY` edges, so the output spans the full `epistemicLevel` spectrum.
//!
//! Output is a JSON array of ProofArtifacts on stdout (so it pipes into `jq`);
//! all diagnostics (including the epistemicLevel spread) go to stderr. Exit code is
//! non-zero on any parse/ingest error.

use std::path::PathBuf;
use std::process::ExitCode;

use gbrg_analyze::{
    analyze_file, analyze_path_report, build_whatif_graph, AnalyzePathReport,
    DEFAULT_CHURN_WINDOW_DAYS,
};
use gbrg_core::{what_if, BlastRadiusProofArtifact, Mutation, ScoringConfig};
use gbrg_parser::Language;

fn lang_from_str(s: &str) -> Option<Language> {
    match s.to_ascii_lowercase().as_str() {
        "rust" | "rs" => Some(Language::Rust),
        "python" | "py" => Some(Language::Python),
        "typescript" | "ts" | "tsx" => Some(Language::TypeScript),
        _ => None,
    }
}

fn usage() -> &'static str {
    "usage: gbrg-analyze <file|dir> [--lang rust|python|typescript]  (--lang ignored for a dir)"
}

/// Print the JSON array of artifacts to stdout; return an exit code.
fn emit(artifacts: &[BlastRadiusProofArtifact]) -> ExitCode {
    match serde_json::to_string_pretty(artifacts) {
        Ok(json) => {
            println!("{json}");
            ExitCode::SUCCESS
        }
        Err(e) => {
            eprintln!("error: serialising artifacts: {e}");
            ExitCode::FAILURE
        }
    }
}

/// Human-readable evidence summary for a directory walk (to stderr).
fn print_report_summary(root: &std::path::Path, report: &AnalyzePathReport) {
    eprintln!(
        "gbrg-analyze: {} → {} file(s) parsed ({} test file(s)), {} cell(s) ingested, \
         {} scored, {} test cell(s) excluded",
        root.display(),
        report.files_parsed,
        report.test_files,
        report.cells_total,
        report.cells_scored,
        report.test_cells,
    );
    eprintln!(
        "gbrg-analyze: cross-file calls resolved={} ambiguous={} external={}; \
         inherits resolved={}; TESTED_BY edges={}; churny files={}",
        report.xfile_calls_resolved,
        report.xfile_calls_ambiguous,
        report.xfile_calls_external,
        report.xfile_inherits_resolved,
        report.tested_by_edges,
        report.churn_files_nonzero,
    );
    let spread = report.level_spread();
    let rendered: Vec<String> = spread.iter().map(|(lvl, n)| format!("{lvl}={n}")).collect();
    eprintln!(
        "gbrg-analyze: epistemicLevel spread → {}",
        rendered.join("  ")
    );
}

/// `gbrg-analyze whatif <path> --cell <id> --mutation add_tests|remove_dependent`
///
/// Deterministic recompute-and-diff: build the graph from `<path>`, recompute the
/// target cell's ProofArtifact on an in-memory-EDITED copy of that graph, and diff
/// vs baseline. This is NOT counterfactual causal inference (see whatif.rs / WHATIF.md).
/// Prints the [`gbrg_core::WhatIfResult`] as JSON on stdout; summary to stderr.
fn run_whatif(mut args: impl Iterator<Item = String>) -> ExitCode {
    let mut path: Option<PathBuf> = None;
    let mut cell: Option<String> = None;
    let mut mutation: Option<Mutation> = None;

    while let Some(a) = args.next() {
        match a.as_str() {
            "--cell" | "-c" => match args.next() {
                Some(v) => cell = Some(v),
                None => {
                    eprintln!("error: --cell requires a value\n{}", whatif_usage());
                    return ExitCode::from(2);
                }
            },
            "--mutation" | "-m" => match args.next() {
                Some(v) => match Mutation::parse(&v) {
                    Some(m) => mutation = Some(m),
                    None => {
                        eprintln!(
                            "error: unknown --mutation `{v}` (add_tests|remove_dependent)\n{}",
                            whatif_usage()
                        );
                        return ExitCode::from(2);
                    }
                },
                None => {
                    eprintln!("error: --mutation requires a value\n{}", whatif_usage());
                    return ExitCode::from(2);
                }
            },
            "-h" | "--help" => {
                println!("{}", whatif_usage());
                return ExitCode::SUCCESS;
            }
            other if other.starts_with('-') => {
                eprintln!("error: unknown flag `{other}`\n{}", whatif_usage());
                return ExitCode::from(2);
            }
            other => {
                if path.is_some() {
                    eprintln!("error: more than one path given\n{}", whatif_usage());
                    return ExitCode::from(2);
                }
                path = Some(PathBuf::from(other));
            }
        }
    }

    let (path, cell, mutation) = match (path, cell, mutation) {
        (Some(p), Some(c), Some(m)) => (p, c, m),
        _ => {
            eprintln!(
                "error: whatif needs <path> --cell <id> --mutation <m>\n{}",
                whatif_usage()
            );
            return ExitCode::from(2);
        }
    };

    let config = ScoringConfig::default();
    let (graph, churn_by_file) = match build_whatif_graph(&path, &config, DEFAULT_CHURN_WINDOW_DAYS)
    {
        Ok(g) => g,
        Err(e) => {
            eprintln!("error: building graph from {}: {e}", path.display());
            return ExitCode::FAILURE;
        }
    };

    // Hold the target cell's REAL per-file churn constant across before/after so the
    // reported delta is attributable to the hypothetical edit alone (dead=false).
    let churn = graph
        .cells()
        .iter()
        .find(|c| c.cell_id == cell)
        .and_then(|c| churn_by_file.get(&c.file_path).copied())
        .unwrap_or(0.0);

    match what_if(&graph, &cell, mutation, churn, false, &config) {
        Ok(result) => {
            eprintln!("gbrg-analyze whatif: {}", result.summary);
            eprintln!("gbrg-analyze whatif: method = {}", result.method);
            match result.to_json_pretty() {
                Ok(json) => {
                    println!("{json}");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    eprintln!("error: serialising WhatIfResult: {e}");
                    ExitCode::FAILURE
                }
            }
        }
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}

fn whatif_usage() -> &'static str {
    "usage: gbrg-analyze whatif <file|dir> --cell <cell_id> --mutation add_tests|remove_dependent"
}

fn main() -> ExitCode {
    // Subcommand dispatch: `whatif` is the recompute-and-diff surface; anything else
    // is the default parse→score pipeline (single file or directory walk).
    let mut argv = std::env::args().skip(1).peekable();
    if argv.peek().map(String::as_str) == Some("whatif") {
        let _ = argv.next(); // consume "whatif"
        return run_whatif(argv);
    }

    let mut args = argv;
    let mut file: Option<PathBuf> = None;
    let mut lang_arg: Option<String> = None;

    while let Some(a) = args.next() {
        match a.as_str() {
            "--lang" | "-l" => {
                lang_arg = args.next();
                if lang_arg.is_none() {
                    eprintln!("error: --lang requires a value\n{}", usage());
                    return ExitCode::from(2);
                }
            }
            "-h" | "--help" => {
                println!("{}", usage());
                return ExitCode::SUCCESS;
            }
            other if other.starts_with('-') => {
                eprintln!("error: unknown flag `{other}`\n{}", usage());
                return ExitCode::from(2);
            }
            other => {
                if file.is_some() {
                    eprintln!("error: more than one path given\n{}", usage());
                    return ExitCode::from(2);
                }
                file = Some(PathBuf::from(other));
            }
        }
    }

    let path = match file {
        Some(f) => f,
        None => {
            eprintln!("error: no path given\n{}", usage());
            return ExitCode::from(2);
        }
    };

    let config = ScoringConfig::default();

    // DIRECTORY: walk it — auto-detect per-file language, resolve cross-file, wire
    // TESTED_BY + churn, and score every non-test cell.
    if path.is_dir() {
        if lang_arg.is_some() {
            eprintln!(
                "gbrg-analyze: note: --lang is ignored for a directory (auto-detected per file)"
            );
        }
        match analyze_path_report(&path, &config, DEFAULT_CHURN_WINDOW_DAYS) {
            Ok(report) => {
                print_report_summary(&path, &report);
                emit(&report.artifacts)
            }
            Err(e) => {
                eprintln!("error: {e}");
                ExitCode::FAILURE
            }
        }
    } else {
        // SINGLE FILE: resolve language (explicit --lang wins, else by extension).
        let language = match lang_arg {
            Some(s) => match lang_from_str(&s) {
                Some(l) => l,
                None => {
                    eprintln!("error: unsupported --lang `{s}` (rust|python|typescript)");
                    return ExitCode::from(2);
                }
            },
            None => match Language::from_path(&path) {
                Some(l) => l,
                None => {
                    eprintln!(
                        "error: cannot infer language from `{}`; pass --lang",
                        path.display()
                    );
                    return ExitCode::from(2);
                }
            },
        };

        match analyze_file(&path, language, &config) {
            Ok(artifacts) => {
                eprintln!(
                    "gbrg-analyze: {} → {} ProofArtifact(s) [{:?}]",
                    path.display(),
                    artifacts.len(),
                    language
                );
                emit(&artifacts)
            }
            Err(e) => {
                eprintln!("error: {e}");
                ExitCode::FAILURE
            }
        }
    }
}
