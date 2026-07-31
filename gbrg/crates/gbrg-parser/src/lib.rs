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

/// The output of [`parse_file`]: the cells and edges to hand to the spine's writer.
#[derive(Clone, Debug, Default)]
pub struct ParseResult {
    pub cells: Vec<SemanticCell>,
    pub edges: Vec<GraphEdge>,
    /// Call sites whose callee could not be resolved to an in-file function.
    /// These are the cross-file follow-up (documented stub), surfaced for honesty.
    pub unresolved_calls: usize,
    /// Inheritance bases not defined in this file (cross-file follow-up).
    pub unresolved_inherits: usize,
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
    let mut ctx = Ctx {
        source,
        file_path,
        language,
        spec: &spec,
        result: ParseResult::default(),
        func_by_name: std::collections::HashMap::new(),
        class_by_name: std::collections::HashMap::new(),
        pending_calls: Vec::new(),
        pending_inherits: Vec::new(),
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

    let mut cursor = root.walk();
    let children: Vec<Node> = root.children(&mut cursor).collect();
    for child in children {
        ctx.walk(child, Some(module_iri.clone()));
    }

    ctx.resolve();
    Ok(ctx.result)
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
    result: ParseResult,
    /// symbol_name -> cell IRI, for intra-file call resolution.
    func_by_name: std::collections::HashMap<String, String>,
    /// symbol_name -> cell IRI, for intra-file inheritance resolution.
    class_by_name: std::collections::HashMap<String, String>,
    /// (caller_iri, callee_symbol) collected during the walk, resolved at the end.
    pending_calls: Vec<(String, String)>,
    /// (subclass_iri, base_symbol) collected during the walk.
    pending_inherits: Vec<(String, String)>,
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

    /// Recursive tree walk. `enclosing_fn` is the IRI of the nearest enclosing
    /// definition (function or module) — the caller for any call site found below.
    fn walk(&mut self, node: Node, enclosing_fn: Option<String>) {
        let kind = node.kind();

        if self.spec.is_func(kind) {
            let symbol = self.name_of(&node).unwrap_or_else(|| "<anon>".to_string());
            let iri = def_iri(self.language, self.file_path, &symbol);
            self.push_cell(iri.clone(), CellKind::Function, symbol.clone(), &node);
            self.func_by_name.entry(symbol).or_insert_with(|| iri.clone());
            // Descend with THIS function as the enclosing caller.
            self.walk_children(node, Some(iri));
            return;
        }

        if self.spec.is_class(kind) {
            let symbol = self.name_of(&node).unwrap_or_else(|| "<anon>".to_string());
            let iri = def_iri(self.language, self.file_path, &symbol);
            self.push_cell(iri.clone(), CellKind::Class, symbol.clone(), &node);
            self.class_by_name.entry(symbol).or_insert_with(|| iri.clone());
            self.collect_inherits(&node, &iri);
            // Methods inside become their own function cells with their own scope.
            self.walk_children(node, enclosing_fn);
            return;
        }

        // Rust `impl Trait for Type` is not a class node but carries an INHERITS
        // relationship (Type inherits Trait).
        if self.language == Language::Rust && kind == "impl_item" {
            self.collect_rust_impl_inherits(&node);
            self.walk_children(node, enclosing_fn);
            return;
        }

        if self.spec.is_module(kind) {
            let symbol = self.name_of(&node).unwrap_or_else(|| "<anon-mod>".to_string());
            let iri = def_iri(self.language, self.file_path, &symbol);
            self.push_cell(iri.clone(), CellKind::Module, symbol, &node);
            self.walk_children(node, enclosing_fn);
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

        self.walk_children(node, enclosing_fn);
    }

    fn walk_children(&mut self, node: Node, enclosing_fn: Option<String>) {
        let mut cursor = node.walk();
        let children: Vec<Node> = node.children(&mut cursor).collect();
        for child in children {
            self.walk(child, enclosing_fn.clone());
        }
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
    fn resolve(&mut self) {
        for (caller_iri, callee) in std::mem::take(&mut self.pending_calls) {
            match self.func_by_name.get(&callee) {
                Some(callee_iri) if *callee_iri != caller_iri => {
                    self.result.edges.push(GraphEdge {
                        from: cell_iri_to_node_id(&caller_iri),
                        to: cell_iri_to_node_id(callee_iri),
                        kind: EdgeKind::Calls,
                        weight: 1.0,
                    });
                }
                // Self-recursion (callee == caller) is skipped to avoid noise;
                // everything else that doesn't resolve is a cross-file follow-up.
                Some(_) => {}
                None => self.result.unresolved_calls += 1,
            }
        }

        for (sub_iri, base) in std::mem::take(&mut self.pending_inherits) {
            match self.class_by_name.get(&base) {
                Some(base_iri) => {
                    self.result.edges.push(GraphEdge {
                        from: cell_iri_to_node_id(&sub_iri),
                        to: cell_iri_to_node_id(base_iri),
                        kind: EdgeKind::Inherits,
                        weight: 1.0,
                    });
                }
                None => self.result.unresolved_inherits += 1,
            }
        }
    }
}
