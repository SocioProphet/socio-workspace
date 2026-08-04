"""Exhaustive proof-as-tests for holographic Merkle-leaf dispersal (Rabin IDA over GF(256))."""
import itertools
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.holographic_ida import (  # noqa: E402
    _EXP, _inv, _mul, disperse, merkle_root, reconstruct,
)


# ── GF(256) field correctness (the foundation the proof stands on) ────────────────────────────

def test_generator_three_covers_the_whole_field():
    # a correct log/exp table over generator 3 visits every nonzero element exactly once.
    assert sorted(_EXP[:255]) == list(range(1, 256))


def test_multiplicative_inverse():
    for a in range(1, 256):
        assert _mul(a, _inv(a)) == 1


def test_mul_identity_and_zero():
    for a in range(256):
        assert _mul(a, 1) == a and _mul(a, 0) == 0


# ── the holographic property: ANY k of n reconstruct the WHOLE leaf ───────────────────────────

def test_roundtrip_all_fragments():
    leaf = b"the whole leaf, exactly"
    d = disperse(leaf, 4, 7)
    assert reconstruct(d.fragments, 4, d.orig_len) == leaf


def test_any_k_of_n_reconstructs_exhaustively():
    leaf = os.urandom(50)
    k, n = 4, 8
    d = disperse(leaf, k, n)
    root = merkle_root(leaf)
    subsets = list(itertools.combinations(d.xs, k))
    for combo in subsets:
        rec = reconstruct({x: d.fragments[x] for x in combo}, k, d.orig_len)
        assert rec == leaf and merkle_root(rec) == root
    assert len(subsets) == 70  # C(8,4) — every one of them works


def test_fewer_than_k_cannot_reconstruct():
    d = disperse(os.urandom(40), 5, 9)
    try:
        reconstruct({x: d.fragments[x] for x in d.xs[:4]}, 5, d.orig_len)
    except ValueError:
        pass
    else:
        raise AssertionError("k-1 fragments must not reconstruct")


def test_more_than_k_fragments_also_reconstruct():
    leaf = os.urandom(33)
    d = disperse(leaf, 3, 9)
    assert reconstruct({x: d.fragments[x] for x in d.xs[:7]}, 3, d.orig_len) == leaf  # 7 >= 3


# ── integrity across the trust mesh: a tampered fragment is caught ────────────────────────────

def test_tampered_fragment_breaks_the_merkle_root():
    leaf = os.urandom(48)
    k, n = 4, 8
    d = disperse(leaf, k, n)
    root = merkle_root(leaf)
    bad = dict(d.fragments)
    bad[3] = bytes([bad[3][0] ^ 0x01]) + bad[3][1:]     # flip one bit in fragment 3
    incl = reconstruct({x: bad[x] for x in [1, 2, 3, 4]}, k, d.orig_len)   # includes the liar
    excl = reconstruct({x: bad[x] for x in [1, 2, 4, 5]}, k, d.orig_len)   # excludes the liar
    assert merkle_root(incl) != root      # the corruption is DETECTED (root won't verify)
    assert merkle_root(excl) == root      # the honest quorum reconstructs the true leaf


# ── edge shapes ───────────────────────────────────────────────────────────────────────────────

def test_various_sizes_including_empty_and_binary():
    for size in (0, 1, 5, 6, 7, 100, 255):
        leaf = os.urandom(size)
        d = disperse(leaf, 3, 5)
        assert reconstruct({x: d.fragments[x] for x in d.xs[:3]}, 3, d.orig_len) == leaf


def test_k_equals_one_is_replication():
    leaf = b"replicated"
    d = disperse(leaf, 1, 4)
    for x in d.xs:
        assert reconstruct({x: d.fragments[x]}, 1, d.orig_len) == leaf  # any single fragment == whole


def test_k_equals_n_no_redundancy_still_exact():
    leaf = os.urandom(30)
    d = disperse(leaf, 5, 5)
    assert reconstruct(d.fragments, 5, d.orig_len) == leaf


def test_rejects_bad_params():
    for k, n in ((0, 3), (4, 3), (1, 256)):
        try:
            disperse(b"x", k, n)
        except ValueError:
            pass
        else:
            raise AssertionError(f"bad params must raise: k={k} n={n}")


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"holographic_ida: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
