"""Independent T3 artifact checker; no T3 implementation/model/store imports."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import unicodedata
from typing import Any

from nlc.m5.t2.verifier import verify_parentless_root


SLOT_TAG = b"NLC-M5-T3-CUTOVER-SLOT-v1\x00"
PROPOSAL_TAG = b"NLC-M5-T3-CUTOVER-PROPOSAL-v1\x00"
RECEIPT_TAG = b"NLC-M5-T3-CUTOVER-RECEIPT-v1\x00"


@dataclass(frozen=True)
class CutoverVerification:
    verdict: str
    reason_code: str
    slot_id: str | None
    root_id: str | None
    committed_root_count: int
    distinct_committed_root_count: int
    verifier_version: str = "NLC-M5-T3-INDEPENDENT-CUTOVER-VERIFIER/1.0"


def _canonical(value: Any) -> bytes:
    def norm(item):
        if item is None or isinstance(item, (bool, int)): return item
        if isinstance(item, float): raise ValueError("FLOAT_PROHIBITED")
        if isinstance(item, str): return unicodedata.normalize("NFC", item)
        if isinstance(item, list): return [norm(x) for x in item]
        if isinstance(item, dict): return {unicodedata.normalize("NFC", k): norm(v) for k, v in item.items()}
        raise ValueError("TYPE_PROHIBITED")
    return json.dumps(norm(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(tag, value): return hashlib.sha256(tag + _canonical(value)).hexdigest()


def verify_cutover(store_bytes: bytes, receipt_bytes: bytes, construction_receipt: bytes,
                   certificate: bytes, context) -> CutoverVerification:
    slot_id = root_id = None
    try:
        store = json.loads(store_bytes.decode("utf-8")); receipt = json.loads(receipt_bytes.decode("utf-8"))
        if _canonical(store) + b"\n" != store_bytes or _canonical(receipt) != receipt_bytes:
            raise ValueError("NON_CANONICAL_ENCODING")
        if store.get("store_version") != "NLC-CUTOVER-STORE/1.0": raise ValueError("STORE_VERSION_INVALID")
        slot = store["slot"]; slot_id = slot["slot_id"]
        slot_material = {k: slot[k] for k in ("fence_identity", "frozen_parent_state_commitment", "generation", "protected_scope", "slot_version", "target_domain", "target_epoch")}
        if slot["slot_version"] != "NLC-CUTOVER-SLOT/1.0" or _hash(SLOT_TAG, slot_material) != slot_id: raise ValueError("SLOT_ID_MISMATCH")
        proposal = store["proposal"]
        pm = {k: proposal[k] for k in ("certificate_id", "construction_receipt_id", "proposal_version", "proposer_identity", "proposer_version", "root_id", "slot_id")}
        if proposal["proposal_version"] != "NLC-CUTOVER-PROPOSAL/1.0" or _hash(PROPOSAL_TAG, pm) != proposal["proposal_id"]: raise ValueError("PROPOSAL_BINDING_MISMATCH")
        if proposal["slot_id"] != slot_id: raise ValueError("PROPOSAL_SLOT_MISMATCH")
        eligible = verify_parentless_root(construction_receipt, certificate, context)
        root_id = proposal["root_id"]
        if eligible.verdict != "ACCEPT" or eligible.root_id != root_id: raise ValueError("ROOT_NOT_ELIGIBLE")
        t2 = json.loads(construction_receipt)
        if proposal["certificate_id"] != t2["certificate_id"]: raise ValueError("CERTIFICATE_ID_MISMATCH")
        if proposal["construction_receipt_id"] != hashlib.sha256(construction_receipt).hexdigest(): raise ValueError("CONSTRUCTION_RECEIPT_ID_MISMATCH")
        if t2["construction_material"]["target_domain"] != slot["target_domain"]: raise ValueError("WRONG_DOMAIN")
        if t2["construction_material"]["target_epoch"] != slot["target_epoch"]: raise ValueError("STALE_EPOCH")
        if store["state"] != "COMMITTED" or store["terminal_outcome"] != "COMMITTED_ACTIVE": raise ValueError("TERMINAL_STATE_INCONSISTENT")
        if store["candidate_root_id"] != root_id: raise ValueError("POST_COMMIT_ROOT_SUBSTITUTION")
        if store["receipt"] != receipt or store["receipt_id"] != receipt.get("receipt_id"): raise ValueError("STATE_RECEIPT_MISMATCH")
        material = {k: receipt[k] for k in ("accepted_certificate_id", "activation_result", "authority_ancestry", "authority_parent_edges", "commit_state", "decision_evidence", "engine_version", "proposal_id", "receipt_version", "root_construction_receipt_id", "root_id", "slot_id")}
        if receipt.get("receipt_version") != "NLC-CUTOVER-RECEIPT/1.0" or _hash(RECEIPT_TAG, material) != receipt.get("receipt_id"): raise ValueError("RECEIPT_ID_MISMATCH")
        if (receipt["slot_id"], receipt["root_id"], receipt["proposal_id"], receipt["accepted_certificate_id"], receipt["root_construction_receipt_id"]) != (slot_id, root_id, proposal["proposal_id"], proposal["certificate_id"], proposal["construction_receipt_id"]): raise ValueError("RECEIPT_BINDING_MISMATCH")
        if receipt["commit_state"] != "COMMITTED" or receipt["activation_result"] != "ACTIVE": raise ValueError("RECEIPT_STATE_MISMATCH")
        if receipt["authority_ancestry"] != [] or receipt["authority_parent_edges"] != []: raise ValueError("OLD_AUTHORITY_RELATION_PROHIBITED")
        commits = [row for row in store.get("history", []) if row.get("event") == "COMMIT"]
        roots = {row.get("root_id") for row in commits}
        if len(commits) != 1 or roots != {root_id}: raise ValueError("MULTIPLE_OR_CONFLICTING_COMMIT")
        evidence = receipt["decision_evidence"]
        if evidence.get("root_eligibility_verdict") != "ACCEPT" or evidence.get("parentless_reason_code") != "PARENTLESS_ROOT_VERIFIED" or evidence.get("authority_parent_edge_count") != 0: raise ValueError("COMMIT_EVIDENCE_MISSING")
        return CutoverVerification("ACCEPT", "SINGLE_PARENTLESS_ROOT_COMMIT_VERIFIED", slot_id, root_id, len(commits), len(roots))
    except (ValueError, KeyError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        code = str(exc) if isinstance(exc, ValueError) and str(exc) else "ARTIFACT_MALFORMED"
        return CutoverVerification("REJECT", code, slot_id, root_id, 0, 0)
