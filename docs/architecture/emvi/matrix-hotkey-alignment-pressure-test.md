# Matrix Hotkey Alignment Pressure Test

Status: Draft v0.1

## Purpose

This note records what Matrix keyboard behavior taught us about EMVI.
The goal is not to copy Matrix wholesale, but to pressure-test the shell against
a real dense keyboard surface.

## Main findings

### 1. Contextual key ownership is real
Composer, autocomplete, room list, and dialogs each own their local keys.
This supports EMVI's focus-owner model.

### 2. Escape is layered unwind
Escape should dismiss the innermost transient surface first.

### 3. Arrows are local region-navigation keys
Up/Down work well for room lists, autocomplete, and local movement.

### 4. Completion surfaces need Tab precedence
When a completion popup is open, Tab belongs to completion first.

### 5. Enter behavior is not globally uniform
In text surfaces, Enter may remain newline while explicit commit chords handle send/execute.

## Design deltas for EMVI

- give completion popups Tab precedence
- gate Up/Down escape from multiline text to boundary conditions
- keep local composer/editor namespace protected
- support explicit panel/layout toggles as a first-class concept
- add attention-queue style navigation as a future primitive
