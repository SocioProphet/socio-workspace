//! # `gbrg-analyze` — demo CLI
//!
//! The demo surface for the END-TO-END GBRG pipeline. Point it at a real source
//! file and it prints the emitted [`BlastRadiusProofArtifact`]s as pretty JSON.
//!
//! ```text
//!   gbrg-analyze <file> [--lang rust|python|typescript]
//! ```
//!
//! If `--lang` is omitted the language is guessed from the file extension
//! (`.rs` → rust, `.py` → python, `.ts`/`.tsx`/`.mts`/`.cts` → typescript).
//!
//! Output is a JSON array of ProofArtifacts on stdout (so it pipes into `jq`);
//! all diagnostics go to stderr. Exit code is non-zero on any parse/ingest error.

use std::path::PathBuf;
use std::process::ExitCode;

use gbrg_analyze::analyze_file;
use gbrg_core::ScoringConfig;
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
    "usage: gbrg-analyze <file> [--lang rust|python|typescript]"
}

fn main() -> ExitCode {
    let mut args = std::env::args().skip(1);
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
                    eprintln!("error: more than one file given\n{}", usage());
                    return ExitCode::from(2);
                }
                file = Some(PathBuf::from(other));
            }
        }
    }

    let file = match file {
        Some(f) => f,
        None => {
            eprintln!("error: no file given\n{}", usage());
            return ExitCode::from(2);
        }
    };

    // Resolve language: explicit --lang wins, else guess from the extension.
    let language = match lang_arg {
        Some(s) => match lang_from_str(&s) {
            Some(l) => l,
            None => {
                eprintln!("error: unsupported --lang `{s}` (rust|python|typescript)");
                return ExitCode::from(2);
            }
        },
        None => match Language::from_path(&file) {
            Some(l) => l,
            None => {
                eprintln!(
                    "error: cannot infer language from `{}`; pass --lang",
                    file.display()
                );
                return ExitCode::from(2);
            }
        },
    };

    let config = ScoringConfig::default();
    match analyze_file(&file, language, &config) {
        Ok(artifacts) => {
            eprintln!(
                "gbrg-analyze: {} → {} ProofArtifact(s) [{:?}]",
                file.display(),
                artifacts.len(),
                language
            );
            // The money artifact: a JSON array of ProofArtifacts on stdout.
            match serde_json::to_string_pretty(&artifacts) {
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
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}
