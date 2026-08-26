"""Regression tests for reveal-broadcast finalization hardening [SKRYBITDEV-666].

Covers the two failure surfaces that previously had no coverage:
- vin[0] witness must be a valid taproot Schnorr signature (64/65 bytes);
- a failed broadcast must surface bitcoind's testmempoolaccept reject-reason.
"""

from __future__ import annotations

import pytest

from counters_proto.server.mint_routes import _reject_reason, _taproot_keypath_witness


# --- vin[0] witness validation ---------------------------------------------

def test_witness_accepts_64_byte_schnorr():
    sig = b"\x11" * 64
    assert _taproot_keypath_witness(sig) == [sig]


@pytest.mark.parametrize("suffix", [0x01, 0x02, 0x03, 0x81, 0x82, 0x83])
def test_witness_accepts_65_byte_schnorr_with_valid_sighash(suffix):
    sig = b"\x22" * 64 + bytes([suffix])
    assert _taproot_keypath_witness(sig) == [sig]


@pytest.mark.parametrize("suffix", [0x00, 0x04, 0x41, 0x84, 0xff])
def test_witness_rejects_invalid_sighash_suffix(suffix):
    # BIP341: 0x00 (valid only as the implicit 64-byte form) and any non-listed
    # byte must be rejected before it reaches sendrawtransaction.
    sig = b"\x22" * 64 + bytes([suffix])
    with pytest.raises(ValueError, match="sighash type"):
        _taproot_keypath_witness(sig)


@pytest.mark.parametrize("bad", [b"", b"\x00" * 63, b"\x00" * 66, b"\x00" * 71])
def test_witness_rejects_wrong_length(bad):
    # e.g. a DER/ECDSA sig from a non-taproot wallet path (~71 bytes)
    with pytest.raises(ValueError, match="taproot Schnorr"):
        _taproot_keypath_witness(bad)


def test_witness_normalizes_bytearray_to_bytes():
    out = _taproot_keypath_witness(bytearray(b"\x33" * 64))
    assert out == [b"\x33" * 64]
    assert isinstance(out[0], bytes)


# --- broadcast reject-reason surfacing -------------------------------------

def test_reject_reason_prefers_testmempoolaccept():
    checks = [{"txid": "ab", "allowed": False, "reject-reason": "min relay fee not met"}]
    assert _reject_reason(checks, RuntimeError("rpc -26")) == "min relay fee not met"


def test_reject_reason_falls_back_to_error_when_no_checks():
    assert _reject_reason(None, RuntimeError("connection refused")) == "connection refused"
    assert _reject_reason([], RuntimeError("boom")) == "boom"


def test_reject_reason_falls_back_when_field_missing():
    checks = [{"txid": "ab", "allowed": False}]  # no reject-reason
    assert _reject_reason(checks, RuntimeError("rpc error")) == "rpc error"


def test_reject_reason_handles_null_first_entry():
    assert _reject_reason([None], RuntimeError("fallback")) == "fallback"
