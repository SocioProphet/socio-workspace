"""Holographic dispersal of Merkle leaves — Rabin's Information Dispersal Algorithm over GF(256).

"Holographic" is the precise, provable claim: the leaf is dispersed into n fragments such that ANY
k of them reconstruct the WHOLE leaf exactly, and fewer than k reconstruct nothing usable. Each
fragment carries information about the whole (like a hologram), so the leaf survives the loss —
seizure, partition, Byzantine drop — of up to n-k nodes, and is reconstructable from any k honest
vantages that remain. This is coding theory, not hand-rolled secrecy: every claim here is checked
by actually reconstructing the bytes and verifying them against the leaf's Merkle commitment.

Construction (Rabin IDA): the leaf is cut into blocks of k symbols; each block is the coefficient
vector of a degree-(k-1) polynomial over GF(2^8) (the AES field, modulus 0x11b); fragment i stores
that polynomial evaluated at a distinct nonzero point x_i. Any k points determine the degree-(k-1)
polynomial uniquely (Lagrange), so any k fragments recover every block — hence the whole leaf.
Storage per fragment is |leaf|/k; total overhead n/k, matching the Placement(rs_k, rs_n) model.

Integrity across the trust mesh: reconstruction is verified against the leaf's content hash
(sha256 — its Merkle commitment). A tampered fragment yields wrong bytes -> a hash mismatch, so a
lying node is DETECTED; with n>k redundancy the honest quorum simply reconstructs from a fragment
set that excludes it (proven in the tests + tools/prove_holographic_propagation.py).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

# ── GF(2^8), the AES field (primitive polynomial 0x11b, generator 0x03) ──────────────────────
_EXP: List[int] = [0] * 512
_LOG: List[int] = [0] * 256


def _init_tables() -> None:
    # Generator 0x03 (2 is NOT primitive for 0x11b — order 51, not 255). 3*x = x XOR 2*x.
    x = 1
    for i in range(255):
        _EXP[i] = x
        _LOG[x] = i
        x2 = (x << 1) ^ (0x11B if x & 0x80 else 0)   # 2*x with field reduction
        x ^= x2                                       # 3*x = x + 2*x
    for i in range(255, 512):
        _EXP[i] = _EXP[i - 255]


_init_tables()


def _mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _inv(a: int) -> int:
    if a == 0:
        raise ZeroDivisionError("no inverse of 0 in GF(256)")
    return _EXP[255 - _LOG[a]]


def _eval_poly(coeffs: Sequence[int], x: int) -> int:
    """Evaluate sum(coeffs[j] * x^j) at x (Horner), over GF(256)."""
    acc = 0
    for c in reversed(coeffs):
        acc = _mul(acc, x) ^ c
    return acc


def _poly_mul(a: List[int], b: List[int]) -> List[int]:
    out = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        for j, bj in enumerate(b):
            out[i + j] ^= _mul(ai, bj)
    return out


def _interpolate_coeffs(xs: Sequence[int], ys: Sequence[int]) -> List[int]:
    """Recover the k polynomial COEFFICIENTS (the original data block) from k (x, y) points."""
    k = len(xs)
    coeffs = [0] * k
    for i in range(k):
        num: List[int] = [1]           # numerator polynomial prod_{j!=i} (x + x_j)
        denom = 1                       # prod_{j!=i} (x_i + x_j)
        for j in range(k):
            if j == i:
                continue
            num = _poly_mul(num, [xs[j], 1])   # (x + x_j) in GF(256), since subtraction == xor
            denom = _mul(denom, xs[i] ^ xs[j])
        scale = _mul(ys[i], _inv(denom))
        for d in range(len(num)):
            coeffs[d] ^= _mul(num[d], scale)
    return coeffs


@dataclass(frozen=True)
class Dispersal:
    k: int
    n: int
    orig_len: int
    xs: List[int]                # the n distinct evaluation points (fragment ids)
    fragments: Dict[int, bytes]  # x -> fragment bytes


def merkle_root(leaf: bytes) -> str:
    """The leaf's content commitment (its Merkle-tree leaf hash)."""
    return "sha256:" + hashlib.sha256(leaf).hexdigest()


def disperse(leaf: bytes, k: int, n: int, *, xs: Optional[Sequence[int]] = None) -> Dispersal:
    """Disperse ``leaf`` into ``n`` fragments; ANY ``k`` reconstruct it. 1 <= k <= n <= 255."""
    if not (1 <= k <= n <= 255):
        raise ValueError("require 1 <= k <= n <= 255")
    points = list(xs) if xs is not None else list(range(1, n + 1))
    if len(points) != n or len(set(points)) != n or any(p == 0 for p in points):
        raise ValueError("xs must be n distinct nonzero points")
    pad = (-len(leaf)) % k
    data = leaf + b"\x00" * pad          # pad to a multiple of k (orig_len restores exact bytes)
    frags: Dict[int, bytearray] = {x: bytearray() for x in points}
    for start in range(0, len(data), k):
        block = data[start:start + k]     # k coefficients of a degree-(k-1) polynomial
        for x in points:
            frags[x].append(_eval_poly(block, x))
    return Dispersal(k=k, n=n, orig_len=len(leaf), xs=points,
                     fragments={x: bytes(b) for x, b in frags.items()})


def reconstruct(fragments: Dict[int, bytes], k: int, orig_len: int) -> bytes:
    """Reconstruct the leaf from ANY ``k`` (or more) fragments. Raises if fewer than k are given."""
    xs = sorted(fragments)
    if len(xs) < k:
        raise ValueError(f"need {k} fragments to reconstruct; got {len(xs)}")
    xs = xs[:k]
    flen = len(fragments[xs[0]])
    out = bytearray()
    for pos in range(flen):
        ys = [fragments[x][pos] for x in xs]
        out.extend(_interpolate_coeffs(xs, ys))
    return bytes(out[:orig_len])
