// Fixture for gbrg-parser: A calls B, B calls C (intra-file call chain).
// Also exercises `impl Trait for Type` (inherits) and a `use` (imports).

use std::fmt;

pub trait Greeter {
    fn greet(&self) -> String;
}

pub struct Robot;

impl Greeter for Robot {
    fn greet(&self) -> String {
        "beep".to_string()
    }
}

pub fn a() {
    b();
}

fn b() {
    c();
}

fn c() -> i32 {
    let _ = fmt::Error;
    42
}
