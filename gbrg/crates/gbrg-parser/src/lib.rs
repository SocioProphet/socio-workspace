//! # gbrg-parser — code-structure parser for the Governed Blast-Radius Graph
//!
//! Turns a source file into the exact primitives the GBRG spine already knows how
//! to persist: [`SemanticCell`]s (nodes) and [`GraphEdge`]s. It consumes the
//! `gbrg-core` model verbatim (never redefines it) and uses `tree-sitter` grammars
//! (all MIT-licensed) to extract structure.
//!
//! ## What is REAL here
//! * Cell extraction for functions, classes/structs/traits/interfaces, imports and
//!   modules, each with `symbol_name`, `kind`, `file_path`, `loc_start`/`loc_end`
//!   (1-based lines) and `ast_hash` = sha256 of the node's source slice (via
//!   [`gbrg_core::ast_hash_of`]).
//! * `calls` edges resolved **intra-file**: a call expression's callee name is
//!   matched against the functions defined in the same file.
//! * `imports` edges: the file's module cell → each import cell.
//! * `inherits` edges resolved **intra-file**: a class's base/trait name matched
//!   against classes/traits defined in the same file.
//!
//! ## What is a documented STUB (follow-up)
//! * **Cross-file resolution.** A callee or base type that is not defined in the
//!   same file is left unresolved (no edge). Cross-file resolution by symbol name /
//!   import graph is the next step and is intentionally NOT done here. Unresolved
//!   counts are surfaced on [`ParseResult`] so the gap is measurable, not hidden.

use std::fmt;
use std::fs;
use std::io;
use std::path::Path;

use gbrg_core::{ast_hash_of, cell_iri_to_node_id, CellKind, EdgeKind, GraphEdge, SemanticCell};
use tree_sitter::{Node, Parser};

/// Languages this parser can handle (each backed by an MIT tree-sitter grammar).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Language {
    Rust,
    Python,
    TypeScript,
}

impl Language {
    /// Guess a language from a file extension. `None` for unsupported extensions.
    pub fn from_path(path: &Path) -> Option<Language> {
        match path.extension().and_then(|e| e.to_str()) {
            Some("rs") => Some(Language::Rust),
            Some("py") => Some(Language::Python),
            Some("ts") | Some("tsx") | Some("mts") | Some("cts") => Some(Language::TypeScript),
            _ => None,
        }
    }

    fn short(self) -> &'static str {
        match self {
            Language::Rust => "rust",
            Language::Python => "python",
            Language::TypeScript => "typescript",
        }
    }

    fn ts_language(self) -> tree_sitter::Language {
        match self {
            Language::Rust => tree_sitter_rust::LANGUAGE.into(),
            Language::Python => tree_sitter_python::LANGUAGE.into(),
            Language::TypeScript => tree_sitter_typescript::LANGUAGE_TYPESCRIPT.into(),
        }
    }

    fn spec(self) -> LangSpec {
        match self {
            Language::Rust => LangSpec {
                func_kinds: &["function_item"],
                class_kinds: &["struct_item", "enum_item", "trait_item", "union_item"],
                module_kinds: &["mod_item"],
                import_kinds: &["use_declaration"],
                call_kinds: &["call_expression"],
            },
            Language::Python => LangSpec {
                func_kinds: &["function_definition"],
                class_kinds: &["class_definition"],
                module_kinds: &[],
                import_kinds: &["import_statement", "import_from_statement"],
                call_kinds: &["call"],
            },
            Language::TypeScript => LangSpec {
                func_kinds: &["function_declaration", "method_definition"],
                class_kinds: &["class_declaration", "interface_declaration"],
                module_kinds: &["internal_module", "module"],
                import_kinds: &["import_statement"],
                call_kinds: &["call_expression"],
            },
        }
    }
}

/// Per-language tree-sitter node-kind vocabulary.
struct LangSpec {
    func_kinds: &'static [&'static str],
    class_kinds: &'static [&'static str],
    module_kinds: &'static [&'static str],
    import_kinds: &'static [&'static str],
    call_kinds: &'static [&'static str],
}

impl LangSpec {
    fn is_func(&self, k: &str) -> bool {
        self.func_kinds.contains(&k)
    }
    fn is_class(&self, k: &str) -> bool {
        self.class_kinds.contains(&k)
    }
    fn is_module(&self, k: &str) -> bool {
        self.module_kinds.contains(&k)
    }
    fn is_import(&self, k: &str) -> bool {
        self.import_kinds.contains(&k)
    }
    fn is_call(&self, k: &str) -> bool {
        self.call_kinds.contains(&k)
    }
}

/// A call site whose callee is not defined in the same file. Surfaced so a
/// repo-level pass ([`gbrg_analyze::analyze_path`]) can resolve it cross-file by
/// symbol name once every file's cells are known.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct UnresolvedCall {
    /// IRI of the enclosing caller cell (a function, or the file module).
    pub caller_iri: String,
    /// The callee's simple (final-segment) symbol name, e.g. `helper`.
    pub callee_symbol: String,
    /// True if the caller is a test cell (so a cross-file match becomes a
    /// `TESTED_BY` edge, not a `CALLS` edge).
    pub caller_is_test: bool,
}

/// An inheritance base not defined in the same file (cross-file follow-up).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct UnresolvedInherit {
    /// IRI of the subclass/impl-type cell.
    pub subclass_iri: String,
    /// The base type's simple symbol name.
    pub base_symbol: String,
}

/// The output of [`parse_file`]: the cells and edges to hand to the spine's writer.
#[derive(Clone, Debug, Default)]
pub struct ParseResult {
    pub cells: Vec<SemanticCell>,
    pub edges: Vec<GraphEdge>,
    /// Call sites whose callee could not be resolved to an in-file function.
    /// These are the cross-file follow-up (documented stub), surfaced for honesty.
    /// `unresolved_call_sites.len()` == this count.
    pub unresolved_calls: usize,
    /// Inheritance bases not defined in this file (cross-file follow-up).
    /// `unresolved_inherit_sites.len()` == this count.
    pub unresolved_inherits: usize,
    /// Detail for every unresolved call site (caller + callee symbol + test flag).
    /// This is what a repo-level pass resolves cross-file; the bare count above is
    /// kept for back-compat.
    pub unresolved_call_sites: Vec<UnresolvedCall>,
    /// Detail for every unresolved inheritance base (subclass + base symbol).
    pub unresolved_inherit_sites: Vec<UnresolvedInherit>,
    /// IRIs of cells detected as **test** code (test functions, functions inside a
    /// `#[cfg(test)]`/`tests` module, and — for whole test files — the file module
    /// and every function/method in it). A repo-level pass uses this to (a) turn a
    /// test's calls into `TESTED_BY` edges and (b) EXCLUDE test cells from scoring.
    pub test_cells: Vec<String>,
}

/// Error type for [`parse_file`].
#[derive(Debug)]
pub enum ParseError {
    Io(io::Error),
    /// tree-sitter rejected the grammar (ABI mismatch, etc.).
    Language(String),
    /// tree-sitter returned no tree for the input.
    NoTree,
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ParseError::Io(e) => write!(f, "io error: {e}"),
            ParseError::Language(e) => write!(f, "tree-sitter language error: {e}"),
            ParseError::NoTree => write!(f, "tree-sitter produced no tree"),
        }
    }
}

impl std::error::Error for ParseError {}

impl From<io::Error> for ParseError {
    fn from(e: io::Error) -> Self {
        ParseError::Io(e)
    }
}

/// Parse a source file into GBRG [`SemanticCell`]s and [`GraphEdge`]s.
///
/// `file_path` is used verbatim in every cell's stable IRI, so the same file at the
/// same path always yields the same `NodeId`s (via [`cell_iri_to_node_id`]).
pub fn parse_file(path: impl AsRef<Path>, language: Language) -> Result<ParseResult, ParseError> {
    let path = path.as_ref();
    let source = fs::read(path)?;
    let file_path = path.to_string_lossy().into_owned();
    parse_source(&source, &file_path, language)
}

/// Same as [`parse_file`] but over in-memory bytes (used by tests and callers that
/// already hold the source).
pub fn parse_source(
    source: &[u8],
    file_path: &str,
    language: Language,
) -> Result<ParseResult, ParseError> {
    let mut parser = Parser::new();
    parser
        .set_language(&language.ts_language())
        .map_err(|e| ParseError::Language(e.to_string()))?;
    let tree = parser.parse(source, None).ok_or(ParseError::NoTree)?;

    let spec = language.spec();
    // Whole-file test classification (Rust integration test / pytest / jest file).
    let file_is_test = is_test_file(Path::new(file_path), language);
    let mut ctx = Ctx {
        source,
        file_path,
        language,
        spec: &spec,
        file_is_test,
        result: ParseResult::default(),
        func_by_name: std::collections::HashMap::new(),
        class_by_name: std::collections::HashMap::new(),
        pending_calls: Vec::new(),
        pending_inherits: Vec::new(),
        test_cells: std::collections::HashSet::new(),
        import_counter: 0,
    };

    // Always emit a Module cell standing for the file itself — the anchor for
    // IMPORTS edges and for module-level call sites.
    let module_iri = module_iri(language, file_path);
    let module_stem = Path::new(file_path)
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or(file_path)
        .to_string();
    let root = tree.root_node();
    ctx.push_cell(
        module_iri.clone(),
        CellKind::Module,
        module_stem,
        &root,
    );
    // A whole test file's module is itself test code.
    if file_is_test {
        ctx.test_cells.insert(module_iri.clone());
    }

    // Walk the top-level items with attribute tracking (so `#[test]` /
    // `#[cfg(test)]` attach to the item they precede). The file module is the
    // enclosing caller for module-scope call sites; `file_is_test` seeds test scope.
    ctx.walk_children(root, Some(module_iri.clone()), file_is_test);

    ctx.resolve();
    // Publish the detected test-cell set (sorted for deterministic output).
    let mut test_cells: Vec<String> = ctx.test_cells.into_iter().collect();
    test_cells.sort();
    ctx.result.test_cells = test_cells;
    Ok(ctx.result)
}

/// Whether `path` is, as a whole, a **test file** for `language` — i.e. every
/// definition in it is test code. Content-independent (path-based) by design so
/// callers can pre-classify a file before parsing.
///
/// Rules (deliberately conservative to avoid false positives on fixtures):
/// * **Rust** — the file's *immediate parent directory* is named `tests` (Cargo's
///   integration-test convention, e.g. `crate/tests/foo.rs`). A file under
///   `tests/fixtures/…` has parent `fixtures`, so it is NOT a test file — fixtures
///   are data, not tests.
/// * **Python** — the file stem starts with `test_` or ends with `_test`
///   (pytest / unittest discovery convention).
/// * **TypeScript** — the file name contains `.test.` or `.spec.` (Jest / Vitest
///   convention), e.g. `foo.test.ts`, `foo.spec.tsx`.
///
/// Inline `#[cfg(test)]` modules inside an otherwise-normal source file are NOT
/// caught here (they are not whole-file tests); the parser detects those from the
/// attribute during the walk.
pub fn is_test_file(path: &Path, language: Language) -> bool {
    let name = path
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or_default();
    let stem = path.file_stem().and_then(|s| s.to_str()).unwrap_or_default();
    match language {
        Language::Rust => path
            .parent()
            .and_then(|p| p.file_name())
            .and_then(|n| n.to_str())
            .map(|d| d == "tests")
            .unwrap_or(false),
        Language::Python => stem.starts_with("test_") || stem.ends_with("_test"),
        Language::TypeScript => name.contains(".test.") || name.contains(".spec."),
    }
}

/// True if any of `attrs` (raw `#[…]` attribute source strings) marks the annotated
/// item as test code: `#[test]`, `#[tokio::test]`, `#[cfg(test)]`, etc. Rust-only;
/// other languages carry no attributes here so this is never consulted for them.
fn attrs_mark_test(attrs: &[String]) -> bool {
    attrs.iter().any(|a| a.contains("test"))
}

fn module_iri(lang: Language, file_path: &str) -> String {
    format!("code://{}/{}", lang.short(), file_path)
}

fn def_iri(lang: Language, file_path: &str, symbol: &str) -> String {
    format!("code://{}/{}#{}", lang.short(), file_path, symbol)
}

struct Ctx<'a> {
    source: &'a [u8],
    file_path: &'a str,
    language: Language,
    spec: &'a LangSpec,
    /// The whole file is test code (Rust integration test / pytest / jest file).
    file_is_test: bool,
    result: ParseResult,
    /// symbol_name -> cell IRI, for intra-file call resolution.
    func_by_name: std::collections::HashMap<String, String>,
    /// symbol_name -> cell IRI, for intra-file inheritance resolution.
    class_by_name: std::collections::HashMap<String, String>,
    /// (caller_iri, callee_symbol) collected during the walk, resolved at the end.
    pending_calls: Vec<(String, String)>,
    /// (subclass_iri, base_symbol) collected during the walk.
    pending_inherits: Vec<(String, String)>,
    /// IRIs of cells detected as test code (see [`ParseResult::test_cells`]).
    test_cells: std::collections::HashSet<String>,
    import_counter: usize,
}

impl<'a> Ctx<'a> {
    fn node_text(&self, node: &Node) -> String {
        node.utf8_text(self.source).unwrap_or("").to_string()
    }

    /// Create a cell and append it. Returns the derived IRI (already passed in).
    fn push_cell(&mut self, iri: String, kind: CellKind, symbol: String, node: &Node) {
        let slice = &self.source[node.start_byte()..node.end_byte()];
        let cell = SemanticCell {
            cell_id: iri,
            kind,
            language: self.language.short().to_string(),
            file_path: self.file_path.to_string(),
            symbol_name: symbol,
            ast_hash: ast_hash_of(slice),
            // tree-sitter rows are 0-based; store 1-based lines.
            loc_start: (node.start_position().row as u32) + 1,
            loc_end: (node.end_position().row as u32) + 1,
            generated: false,
        };
        self.result.cells.push(cell);
    }

    fn name_of(&self, node: &Node) -> Option<String> {
        node.child_by_field_name("name").map(|n| self.node_text(&n))
    }

    /// Recursive tree walk.
    ///
    /// * `enclosing_fn` — IRI of the nearest enclosing definition (function or
    ///   module); the caller for any call site found below.
    /// * `in_test` — true when we are lexically inside test scope (a whole test
    ///   file, a `#[cfg(test)]`/`tests` module, or a test function). Every function
    ///   found in test scope is recorded as a test cell.
    /// * `attrs` — raw source of the `#[…]` attributes that immediately precede
    ///   `node` (Rust only; empty otherwise), used to spot `#[test]`/`#[cfg(test)]`.
    fn walk(&mut self, node: Node, enclosing_fn: Option<String>, in_test: bool, attrs: &[String]) {
        let kind = node.kind();

        if self.spec.is_func(kind) {
            let symbol = self.name_of(&node).unwrap_or_else(|| "<anon>".to_string());
            let iri = def_iri(self.language, self.file_path, &symbol);
            self.push_cell(iri.clone(), CellKind::Function, symbol.clone(), &node);
            self.func_by_name.entry(symbol.clone()).or_insert_with(|| iri.clone());
            // A function is test code if we are already in test scope, the whole
            // file is a test, its own attributes mark it (`#[test]`), or (Python)
            // its name follows the pytest/unittest convention.
            let is_test = in_test
                || self.file_is_test
                || attrs_mark_test(attrs)
                || self.name_is_test(&symbol);
            if is_test {
                self.test_cells.insert(iri.clone());
            }
            // Descend with THIS function as the enclosing caller; propagate test
            // scope so nested items are classified consistently.
            self.walk_children(node, Some(iri), is_test);
            return;
        }

        if self.spec.is_class(kind) {
            let symbol = self.name_of(&node).unwrap_or_else(|| "<anon>".to_string());
            let iri = def_iri(self.language, self.file_path, &symbol);
            self.push_cell(iri.clone(), CellKind::Class, symbol.clone(), &node);
            self.class_by_name.entry(symbol).or_insert_with(|| iri.clone());
            self.collect_inherits(&node, &iri);
            // Methods inside become their own function cells with their own scope.
            self.walk_children(node, enclosing_fn, in_test);
            return;
        }

        // Rust `impl Trait for Type` is not a class node but carries an INHERITS
        // relationship (Type inherits Trait).
        if self.language == Language::Rust && kind == "impl_item" {
            self.collect_rust_impl_inherits(&node);
            self.walk_children(node, enclosing_fn, in_test);
            return;
        }

        if self.spec.is_module(kind) {
            let symbol = self.name_of(&node).unwrap_or_else(|| "<anon-mod>".to_string());
            let iri = def_iri(self.language, self.file_path, &symbol);
            self.push_cell(iri.clone(), CellKind::Module, symbol.clone(), &node);
            // A `#[cfg(test)]` module (or one literally named `tests`) puts every
            // definition below it into test scope.
            let mod_is_test = in_test
                || self.file_is_test
                || attrs_mark_test(attrs)
                || symbol == "tests"
                || symbol == "test";
            if mod_is_test {
                self.test_cells.insert(iri);
            }
            self.walk_children(node, enclosing_fn, mod_is_test);
            return;
        }

        if self.spec.is_import(kind) {
            self.import_counter += 1;
            let text = self.node_text(&node);
            let symbol = text.lines().next().unwrap_or("").trim().to_string();
            let iri = def_iri(
                self.language,
                self.file_path,
                &format!("import:{}", self.import_counter),
            );
            self.push_cell(iri.clone(), CellKind::Import, symbol, &node);
            // IMPORTS edge: file module DEPENDS ON the import.
            let from = cell_iri_to_node_id(&module_iri(self.language, self.file_path));
            let to = cell_iri_to_node_id(&iri);
            self.result.edges.push(GraphEdge {
                from,
                to,
                kind: EdgeKind::Imports,
                weight: 1.0,
            });
            // No need to descend into an import.
            return;
        }

        if self.spec.is_call(kind) {
            if let Some(callee) = self.callee_name(&node) {
                let caller = enclosing_fn
                    .clone()
                    .unwrap_or_else(|| module_iri(self.language, self.file_path));
                self.pending_calls.push((caller, callee));
            }
            // Keep descending — arguments may contain nested calls.
        }

        self.walk_children(node, enclosing_fn, in_test);
    }

    /// Walk `node`'s children in order, attaching each run of leading
    /// `attribute_item` siblings to the item that follows them (Rust attributes are
    /// preceding siblings of the annotated item, e.g. `#[test]` then `fn …`).
    fn walk_children(&mut self, node: Node, enclosing_fn: Option<String>, in_test: bool) {
        let mut cursor = node.walk();
        let children: Vec<Node> = node.children(&mut cursor).collect();
        let mut pending_attrs: Vec<String> = Vec::new();
        for child in children {
            if child.kind() == "attribute_item" {
                pending_attrs.push(self.node_text(&child));
                continue;
            }
            self.walk(child, enclosing_fn.clone(), in_test, &pending_attrs);
            pending_attrs.clear();
        }
    }

    /// Python/pytest convention: a function named `test_*` (or exactly `test`) is a
    /// test. Only consulted for Python; Rust uses attributes, TypeScript uses the
    /// file name.
    fn name_is_test(&self, symbol: &str) -> bool {
        self.language == Language::Python && (symbol.starts_with("test_") || symbol == "test")
    }

    /// Extract the callee's simple name from a call node's `function` field.
    /// Reduces `a::b::c`, `x.y.z`, `self.foo` to the final identifier segment.
    fn callee_name(&self, call: &Node) -> Option<String> {
        let func = call.child_by_field_name("function")?;
        let text = self.node_text(&func);
        let seg = text
            .rsplit("::")
            .next()
            .unwrap_or(&text)
            .rsplit('.')
            .next()
            .unwrap_or(&text);
        // Strip turbofish/generics and stray whitespace.
        let seg = seg.split('<').next().unwrap_or(seg).trim();
        if seg.is_empty() {
            None
        } else {
            Some(seg.to_string())
        }
    }

    /// Python/TypeScript inheritance: pull base type names from the class node.
    fn collect_inherits(&mut self, class: &Node, subclass_iri: &str) {
        match self.language {
            Language::Python => {
                if let Some(supers) = class.child_by_field_name("superclasses") {
                    let mut cursor = supers.walk();
                    let kids: Vec<Node> = supers.children(&mut cursor).collect();
                    for k in kids {
                        if k.kind() == "identifier" || k.kind() == "attribute" {
                            let name = self.node_text(&k);
                            let name = name.rsplit('.').next().unwrap_or(&name).to_string();
                            self.pending_inherits
                                .push((subclass_iri.to_string(), name));
                        }
                    }
                }
            }
            Language::TypeScript => {
                // class_heritage contains extends_clause / implements_clause; walk
                // for type identifiers.
                let mut cursor = class.walk();
                let kids: Vec<Node> = class.children(&mut cursor).collect();
                for k in kids {
                    if k.kind() == "class_heritage" || k.kind() == "extends_type_clause" {
                        self.collect_ts_type_identifiers(&k, subclass_iri);
                    }
                }
            }
            Language::Rust => { /* handled via impl_item */ }
        }
    }

    fn collect_ts_type_identifiers(&mut self, node: &Node, subclass_iri: &str) {
        let mut cursor = node.walk();
        let kids: Vec<Node> = node.children(&mut cursor).collect();
        for k in kids {
            match k.kind() {
                "type_identifier" | "identifier" => {
                    let name = self.node_text(&k);
                    self.pending_inherits
                        .push((subclass_iri.to_string(), name));
                }
                _ => self.collect_ts_type_identifiers(&k, subclass_iri),
            }
        }
    }

    /// Rust `impl Trait for Type`: emit (Type inherits Trait).
    fn collect_rust_impl_inherits(&mut self, impl_node: &Node) {
        let trait_node = impl_node.child_by_field_name("trait");
        let type_node = impl_node.child_by_field_name("type");
        if let (Some(tr), Some(ty)) = (trait_node, type_node) {
            let base = self.node_text(&tr);
            let base = base
                .rsplit("::")
                .next()
                .unwrap_or(&base)
                .split('<')
                .next()
                .unwrap_or(&base)
                .trim()
                .to_string();
            let sub = self.node_text(&ty);
            let sub = sub
                .rsplit("::")
                .next()
                .unwrap_or(&sub)
                .split('<')
                .next()
                .unwrap_or(&sub)
                .trim()
                .to_string();
            let sub_iri = def_iri(self.language, self.file_path, &sub);
            self.pending_inherits.push((sub_iri, base));
        }
    }

    /// Resolve pending calls/inherits against the in-file symbol tables.
    ///
    /// A call whose caller is a **test cell** resolves to a `TESTED_BY` edge
    /// (caller test → callee) rather than a `CALLS` edge, so it flips the callee's
    /// `test_coverage_reach` without inflating its code-dependent count. Everything
    /// that does not resolve in-file is surfaced on [`ParseResult::unresolved_call_sites`]
    /// (with the caller's test flag) for cross-file resolution by a repo-level pass.
    fn resolve(&mut self) {
        let pending_calls = std::mem::take(&mut self.pending_calls);
        for (caller_iri, callee) in pending_calls {
            let caller_is_test = self.test_cells.contains(&caller_iri);
            match self.func_by_name.get(&callee) {
                Some(callee_iri) if *callee_iri != caller_iri => {
                    let kind = if caller_is_test {
                        EdgeKind::TestedBy
                    } else {
                        EdgeKind::Calls
                    };
                    self.result.edges.push(GraphEdge {
                        from: cell_iri_to_node_id(&caller_iri),
                        to: cell_iri_to_node_id(callee_iri),
                        kind,
                        weight: 1.0,
                    });
                }
                // Self-recursion (callee == caller) is skipped to avoid noise;
                // everything else that doesn't resolve is a cross-file follow-up.
                Some(_) => {}
                None => {
                    self.result.unresolved_calls += 1;
                    self.result.unresolved_call_sites.push(UnresolvedCall {
                        caller_iri,
                        callee_symbol: callee,
                        caller_is_test,
                    });
                }
            }
        }

        let pending_inherits = std::mem::take(&mut self.pending_inherits);
        for (sub_iri, base) in pending_inherits {
            match self.class_by_name.get(&base) {
                Some(base_iri) => {
                    self.result.edges.push(GraphEdge {
                        from: cell_iri_to_node_id(&sub_iri),
                        to: cell_iri_to_node_id(base_iri),
                        kind: EdgeKind::Inherits,
                        weight: 1.0,
                    });
                }
                None => {
                    self.result.unresolved_inherits += 1;
                    self.result.unresolved_inherit_sites.push(UnresolvedInherit {
                        subclass_iri: sub_iri,
                        base_symbol: base,
                    });
                }
            }
        }
    }
}
