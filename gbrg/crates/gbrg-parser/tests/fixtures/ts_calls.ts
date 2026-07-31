// Fixture for gbrg-parser: A calls B, B calls C, and Dog extends Animal.
import { readFileSync } from "fs";

class Animal {
  sound(): string {
    return "...";
  }
}

class Dog extends Animal {
  sound(): string {
    return "woof";
  }
}

function a(): void {
  b();
}

function b(): void {
  c();
}

function c(): number {
  return 42;
}
