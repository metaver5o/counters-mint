"""Browser-wallet minting via PSBT.

Flow:
  1. POST /mint/prepare   — build inscription, return commit address + dust amount
  2. POST /mint/reveal    — receive commit_txid + source UTXO, build reveal PSBT
                            (server pre-signs vin[1] with ephemeral reveal key;
                             vin[0] is left for the browser wallet to sign)
  3. POST /mint/broadcast — receive wallet-signed PSBT, finalize + broadcast
  4. GET  /mint/status/:id — poll for confirmed counter number

Only numeric (unnamed) assets for now — no XCP required, just BTC fees.
"""

from __future__ import annotations

import base64
import json
import logging
import math
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler

from .. import tap, builder
from ..bitcoind import BitcoindClient, BitcoindError
from ..commands.inscribe import _extract_issuance_outputs, random_numeric_asset, DUST, COIN
from ..config import Config
from ..counterparty import CounterpartyClient, CounterpartyError

log = logging.getLogger("counters.mint")

REVEAL_VSIZE_ESTIMATE = 700   # conservative vbytes for any reveal tx
MIN_RELAY_FEE = 1             # sat/vB

# ---------------------------------------------------------------------------
# Session storage
# ---------------------------------------------------------------------------

_sessions: dict[str, dict] = {}
_lock = threading.Lock()


def _new_session(**kwargs) -> str:
    sid = secrets.token_hex(16)
    with _lock:
        _sessions[sid] = {"created": time.time(), **kwargs}
    return sid


def _get_session(sid: str) -> dict | None:
    with _lock:
        return _sessions.get(sid)


def _update_session(sid: str, **kwargs) -> None:
    with _lock:
        if sid in _sessions:
            _sessions[sid].update(kwargs)


# ---------------------------------------------------------------------------
# Minimal PSBT (BIP 174) builder + parser
# ---------------------------------------------------------------------------

def _varint(n: int) -> bytes:
    if n < 0xfd:
        return bytes([n])
    if n <= 0xffff:
        return b"\xfd" + n.to_bytes(2, "little")
    return b"\xfe" + n.to_bytes(4, "little")


def _psbt_kv(key: bytes, value: bytes) -> bytes:
    return _varint(len(key)) + key + _varint(len(value)) + value


def _witness_field(items: list[bytes]) -> bytes:
    """Serialize a witness stack as used in PSBT_IN_FINAL_SCRIPTWITNESS."""
    out = _varint(len(items))
    for item in items:
        out += _varint(len(item)) + item
    return out


def build_reveal_psbt(
    unsigned_tx: tap.Tx,
    source_value: int,
    source_spk: bytes,
    commit_value: int,
    commit_spk: bytes,
    reveal_witness: list[bytes],      # pre-signed witness for vin[1]
) -> bytes:
    """Return a partial PSBT: vin[1] finalized, vin[0] awaiting wallet signature."""
    magic = b"psbt\xff"

    # --- global: unsigned tx ---
    g = _psbt_kv(b"\x00", unsigned_tx.serialize(force_witness=False))
    g += b"\x00"

    # --- input 0: wallet UTXO (vin[0], to be signed by browser wallet) ---
    witness_utxo_0 = source_value.to_bytes(8, "little") + tap.ser_script(source_spk)
    i0 = _psbt_kv(b"\x01", witness_utxo_0)
    i0 += b"\x00"

    # --- input 1: commit P2TR, pre-finalized (vin[1]) ---
    # BIP 174: when PSBT_IN_FINAL_SCRIPTWITNESS is present, other input data absent.
    # Wallets skip signing finalized inputs and copy the witness into the final tx.
    i1 = _psbt_kv(b"\x07", _witness_field(reveal_witness))  # PSBT_IN_FINAL_SCRIPTWITNESS
    i1 += b"\x00"

    # --- output maps: empty ---
    o0 = b"\x00"
    o1 = b"\x00"

    return magic + g + i0 + i1 + o0 + o1


def parse_signed_psbt(psbt_hex: str) -> tuple[bytes, list[bytes]]:
    """Extract vin[0]'s witness from a wallet-signed PSBT.

    Returns (vin0_tap_key_sig_64, vin1_final_witness_items).
    Raises ValueError on malformed input.
    """
    data = bytes.fromhex(psbt_hex)
    if data[:5] != b"psbt\xff":
        raise ValueError("not a PSBT")

    pos = 5

    def read_varint(d: bytes, p: int) -> tuple[int, int]:
        b = d[p]
        if b < 0xfd:
            return b, p + 1
        if b == 0xfd:
            return int.from_bytes(d[p+1:p+3], "little"), p + 3
        return int.from_bytes(d[p+1:p+5], "little"), p + 5

    def read_map(d: bytes, p: int) -> tuple[dict[bytes, bytes], int]:
        rec: dict[bytes, bytes] = {}
        while p < len(d):
            klen, p = read_varint(d, p)
            if klen == 0:
                return rec, p
            key = d[p:p+klen]; p += klen
            vlen, p = read_varint(d, p)
            val = d[p:p+vlen]; p += vlen
            rec[key] = val
        return rec, p

    # skip global map
    _, pos = read_map(data, pos)

    # parse input 0 map
    inp0, pos = read_map(data, pos)

    # parse input 1 map (pre-finalized by server)
    inp1, pos = read_map(data, pos)

    # vin[0] signature: PSBT_IN_TAP_KEY_SIG (0x13) = 64-byte Schnorr sig
    sig = inp0.get(b"\x13")
    if not sig:
        # Try PSBT_IN_PARTIAL_SIG (0x02 prefix) for non-taproot wallets
        for k, v in inp0.items():
            if k[:1] == b"\x02" and len(k) == 34:
                sig = v  # DER sig; wallet can handle legacy finalization
                break
    if not sig:
        raise ValueError("no signature found for input 0 in PSBT")

    # vin[1] final witness (PSBT_IN_FINAL_SCRIPTWITNESS = 0x07)
    raw_witness = inp1.get(b"\x07", b"")
    witness_items: list[bytes] = []
    if raw_witness:
        p = 0
        count, p = read_varint(raw_witness, p)
        for _ in range(count):
            ilen, p = read_varint(raw_witness, p)
            witness_items.append(raw_witness[p:p+ilen])
            p += ilen

    return sig, witness_items


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decode_body(b64: str) -> bytes:
    try:
        return base64.b64decode(b64)
    except Exception:
        raise ValueError("body_b64 is not valid base64")


def _get_commit_vout(btc: BitcoindClient, txid: str, commit_spk_hex: str) -> tuple[int, int]:
    """Return (vout_index, value_sats) of the commit output in txid."""
    try:
        raw = btc._call("getrawtransaction", [txid, True])
    except BitcoindError as e:
        raise ValueError(f"commit tx not found: {e}")
    for out in raw.get("vout", []):
        if out.get("scriptPubKey", {}).get("hex") == commit_spk_hex:
            return out["n"], round(out["value"] * COIN)
    raise ValueError("commit output not found in tx — wrong txid or commit not in mempool?")


def _addr_to_spk(btc: BitcoindClient, address: str) -> bytes:
    try:
        info = btc._call("validateaddress", [address])
        return bytes.fromhex(info["scriptPubKey"])
    except (BitcoindError, KeyError):
        raise ValueError(f"cannot derive scriptPubKey for {address}")


# ---------------------------------------------------------------------------
# Endpoint handlers
# ---------------------------------------------------------------------------

def _prepare(handler: BaseHTTPRequestHandler, config: Config) -> None:
    """POST /mint/prepare
    Body: {content_type, body_b64, supply, divisible, fee_rate, wallet_address}
    Returns: {session_id, commit_address, commit_value_sats, min_source_sats}
    """
    length = int(handler.headers.get("Content-Length", 0))
    try:
        req = json.loads(handler.rfile.read(length))
        content_type = str(req.get("content_type", "application/octet-stream"))[:128].encode()
        body = _decode_body(str(req.get("body_b64", "")))
        supply = int(req.get("supply", 1))
        divisible = bool(req.get("divisible", False))
        fee_rate = float(req.get("fee_rate", 2))
        wallet_address = str(req.get("wallet_address", ""))
    except (ValueError, KeyError, TypeError) as e:
        _json(handler, {"error": f"invalid request: {e}"}, 400)
        return

    if not wallet_address:
        _json(handler, {"error": "wallet_address required"}, 400)
        return

    fee_rate = max(fee_rate, MIN_RELAY_FEE)
    asset = random_numeric_asset()
    quantity = supply * COIN if divisible else supply

    insc = builder.build_inscription(content_type, body, asset=asset.encode())

    reveal_fee = math.ceil(REVEAL_VSIZE_ESTIMATE * fee_rate)
    min_source_sats = reveal_fee + DUST + 100   # source UTXO must cover reveal fee + change

    sid = _new_session(
        insc_seckey=insc.reveal_seckey,
        insc_xonly=insc.reveal_xonly,
        insc_leaf=insc.leaf,
        insc_merkle=insc.merkle_root,
        insc_control=insc.control_block,
        insc_commit_address=insc.commit_address,
        insc_commit_spk=insc.commit_script_pubkey.hex(),
        asset=asset,
        quantity=quantity,
        divisible=divisible,
        fee_rate=fee_rate,
        wallet_address=wallet_address,
        commit_txid=None,
        reveal_txid=None,
        status="prepared",
    )

    _json(handler, {
        "session_id": sid,
        "commit_address": insc.commit_address,
        "commit_value_sats": DUST,          # wallet sends exactly dust to commit addr
        "min_source_sats": min_source_sats,  # source UTXO must be at least this
        "asset": asset,
    })


def _reveal(handler: BaseHTTPRequestHandler, config: Config) -> None:
    """POST /mint/reveal
    Body: {session_id, commit_txid,
           source_utxo: {txid, vout, value, script_pubkey_hex}}
    Returns: {reveal_psbt_hex}
    """
    length = int(handler.headers.get("Content-Length", 0))
    try:
        req = json.loads(handler.rfile.read(length))
        sid = str(req["session_id"])
        commit_txid = str(req["commit_txid"])
        src = req["source_utxo"]
        source_txid = str(src["txid"])
        source_vout = int(src["vout"])
        source_value = int(src["value"])
        source_spk = bytes.fromhex(str(src["script_pubkey_hex"]))
    except (ValueError, KeyError, TypeError) as e:
        _json(handler, {"error": f"invalid request: {e}"}, 400)
        return

    sess = _get_session(sid)
    if not sess:
        _json(handler, {"error": "session not found"}, 404)
        return

    btc = BitcoindClient(config)
    cp = CounterpartyClient(config)

    # Locate commit output in commit tx
    try:
        commit_vout, commit_value = _get_commit_vout(btc, commit_txid, sess["insc_commit_spk"])
    except ValueError as e:
        _json(handler, {"error": str(e)}, 400)
        return

    commit_spk = bytes.fromhex(sess["insc_commit_spk"])

    # Get wallet scriptPubKey for change output
    try:
        wallet_spk = _addr_to_spk(btc, sess["wallet_address"])
    except ValueError as e:
        _json(handler, {"error": str(e)}, 400)
        return

    # Build CP issuance OP_RETURN keyed to source_utxo (inputs_set pins RC4 key)
    inputs_set = f"{source_txid}:{source_vout}"
    try:
        composed = cp.compose_issuance(
            source=sess["wallet_address"],
            asset=sess["asset"],
            quantity=sess["quantity"],
            divisible=sess["divisible"],
            inputs_set=inputs_set,
        )
        decoded = btc._call("decoderawtransaction", [composed["rawtransaction"]])
        _dest_outs, op_return_spk = _extract_issuance_outputs(decoded)
    except (BitcoindError, CounterpartyError, Exception) as e:
        _json(handler, {"error": f"compose issuance failed: {e}"}, 500)
        return

    # Calculate change
    fee = math.ceil(REVEAL_VSIZE_ESTIMATE * sess["fee_rate"])
    change_value = source_value + commit_value - fee
    if change_value < DUST:
        _json(handler, {"error": f"source UTXO too small: need {fee + DUST} sats, have {source_value}"}, 400)
        return

    # Build reveal tx (unsigned — witnesses set after signing)
    vouts = []
    if op_return_spk is not None:
        vouts.append(tap.TxOut(0, op_return_spk))
    vouts.append(tap.TxOut(change_value, wallet_spk))

    reveal_tx = tap.Tx(
        vin=[
            tap.TxIn(source_txid, source_vout, sequence=0xFFFFFFFD),
            tap.TxIn(commit_txid, commit_vout, sequence=0xFFFFFFFD),
        ],
        vout=vouts,
    )

    # Sign vin[1] (commit tapscript) with ephemeral reveal key
    insc_seckey = sess["insc_seckey"]
    insc_leaf = sess["insc_leaf"]
    insc_merkle = sess["insc_merkle"]
    insc_control = sess["insc_control"]

    sighash = tap.taproot_script_path_sighash(
        reveal_tx, 1,
        prevout_values=[source_value, commit_value],
        prevout_scripts=[source_spk, commit_spk],
        tapleaf=insc_merkle,
    )
    sig = tap.schnorr_sign(sighash, insc_seckey, aux_rand=os.urandom(32))
    reveal_witness_vin1 = [sig, insc_leaf, insc_control]

    # Build PSBT: vin[1] finalized, vin[0] pending wallet signature
    psbt = build_reveal_psbt(
        unsigned_tx=reveal_tx,
        source_value=source_value,
        source_spk=source_spk,
        commit_value=commit_value,
        commit_spk=commit_spk,
        reveal_witness=reveal_witness_vin1,
    )

    _update_session(sid,
        commit_txid=commit_txid,
        commit_vout=commit_vout,
        source_txid=source_txid,
        source_vout=source_vout,
        source_value=source_value,
        source_spk_hex=source_spk.hex(),
        reveal_tx_hex=reveal_tx.serialize(force_witness=False).hex(),
        reveal_witness_vin1=[w.hex() for w in reveal_witness_vin1],
        wallet_spk_hex=wallet_spk.hex(),
        status="reveal_built",
    )

    _json(handler, {"reveal_psbt_hex": psbt.hex()})


def _broadcast(handler: BaseHTTPRequestHandler, config: Config) -> None:
    """POST /mint/broadcast
    Body: {session_id, signed_psbt_hex}
    Returns: {reveal_txid}
    """
    length = int(handler.headers.get("Content-Length", 0))
    try:
        req = json.loads(handler.rfile.read(length))
        sid = str(req["session_id"])
        signed_psbt_hex = str(req["signed_psbt_hex"])
    except (ValueError, KeyError) as e:
        _json(handler, {"error": f"invalid request: {e}"}, 400)
        return

    sess = _get_session(sid)
    if not sess:
        _json(handler, {"error": "session not found"}, 404)
        return
    if sess.get("status") not in ("reveal_built",):
        _json(handler, {"error": f"session in wrong state: {sess.get('status')}"}, 400)
        return

    # Extract vin[0] signature from the wallet-signed PSBT
    try:
        vin0_sig, vin1_witness = parse_signed_psbt(signed_psbt_hex)
    except ValueError as e:
        _json(handler, {"error": f"PSBT parse failed: {e}"}, 400)
        return

    # Rebuild the reveal tx and attach witnesses
    source_txid = sess["source_txid"]
    source_vout = sess["source_vout"]
    commit_txid = sess["commit_txid"]
    commit_vout = sess["commit_vout"]

    # Decode the stored unsigned tx hex to reconstruct outputs
    btc = BitcoindClient(config)
    try:
        dec = btc._call("decoderawtransaction", [sess["reveal_tx_hex"]])
    except BitcoindError as e:
        _json(handler, {"error": f"failed to decode reveal tx: {e}"}, 500)
        return

    vouts = [
        tap.TxOut(int(round(o["value"] * COIN)),
                  bytes.fromhex(o["scriptPubKey"]["hex"]))
        for o in dec["vout"]
    ]

    reveal_tx = tap.Tx(
        vin=[
            tap.TxIn(source_txid, source_vout, sequence=0xFFFFFFFD),
            tap.TxIn(commit_txid, commit_vout, sequence=0xFFFFFFFD),
        ],
        vout=vouts,
    )
    reveal_tx.vin[0].witness = [vin0_sig]
    reveal_tx.vin[1].witness = vin1_witness if vin1_witness else [
        bytes.fromhex(w) for w in sess["reveal_witness_vin1"]
    ]

    raw_hex = reveal_tx.serialize(force_witness=True).hex()

    # Broadcast
    try:
        reveal_txid = btc._call("sendrawtransaction", [raw_hex])
    except BitcoindError as e:
        # Try testmempoolaccept for a better error message
        try:
            checks = btc._call("testmempoolaccept", [[raw_hex]])
            reason = checks[0].get("reject-reason", str(e)) if checks else str(e)
        except Exception:
            reason = str(e)
        _json(handler, {"error": f"broadcast failed: {reason}"}, 400)
        return

    _update_session(sid, reveal_txid=reveal_txid, status="broadcast")
    _json(handler, {"reveal_txid": reveal_txid})


def _status(handler: BaseHTTPRequestHandler, config: Config, sid: str) -> None:
    """GET /mint/status/:session_id
    Returns: {status, reveal_txid, counter_number}
    """
    sess = _get_session(sid)
    if not sess:
        _json(handler, {"error": "session not found"}, 404)
        return

    resp: dict = {
        "status": sess.get("status", "unknown"),
        "reveal_txid": sess.get("reveal_txid"),
        "counter_number": sess.get("counter_number"),
    }

    # If broadcast, poll CP for the counter number
    if sess.get("reveal_txid") and not sess.get("counter_number"):
        try:
            cp = CounterpartyClient(config)
            issuances = cp.get_issuances_by_tx(sess["reveal_txid"])
            if issuances:
                asset = issuances[0].get("asset")
                resp["status"] = "confirmed"
                resp["asset"] = asset
                # Counter number comes from the store; CP only knows the asset
                _update_session(sid, status="confirmed", asset_confirmed=asset)
        except Exception:
            log.exception("failed to poll counterparty for issuance status")

    _json(handler, resp)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

def handle_mint(handler: BaseHTTPRequestHandler, path: str, method: str,
                config: Config) -> bool:
    if not path.startswith("/mint/"):
        return False

    if path == "/mint/prepare" and method == "POST":
        _prepare(handler, config)
        return True
    if path == "/mint/reveal" and method == "POST":
        _reveal(handler, config)
        return True
    if path == "/mint/broadcast" and method == "POST":
        _broadcast(handler, config)
        return True
    if path.startswith("/mint/status/") and method == "GET":
        sid = path[len("/mint/status/"):]
        _status(handler, config, sid)
        return True

    return False


def _json(handler: BaseHTTPRequestHandler, obj: dict, status: int = 200) -> None:
    body = json.dumps(obj).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)
