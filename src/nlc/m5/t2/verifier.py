"""Independent verifier for M5-T2 Root_Constructor_v1 receipts.

No M5-T2 constructor, store, model, or acceptance function is imported.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import unicodedata
from typing import Any

from nlc.m5.t1.verifier import RootAcceptContext, verify_root_accept


ROOT_TAG = b"NLC-M5-T2-PARENTLESS-ROOT-v1\x00"
PROPOSAL_TAG = b"NLC-M5-T2-ROOT-PROPOSAL-v1\x00"
SET_TAG = b"NLC-M5-T2-CONSTRUCTOR-SET-v1\x00"
VOTE_TAG = b"NLC-M5-T2-SYNTHETIC-VOTE-v1\x00"
RECEIPT_TAG = b"NLC-M5-T2-CONSTRUCTION-RECEIPT-v1\x00"
CONSTRUCTORS = ("RootConstructor_Q1", "RootConstructor_Q2")
CREDENTIALS = {
    "RootConstructor_Q1": "synthetic-share:q1-v1",
    "RootConstructor_Q2": "synthetic-share:q2-v1",
}
RECEIPT_FIELDS = {
    "activation_status", "authority_ancestry", "authority_parent_edges",
    "certificate_commitment", "certificate_id", "construction_material",
    "construction_proof", "constructor_set_commitment", "evidence_ancestry",
    "parentage_declaration", "parentage_version", "prohibited_old_authority_relations",
    "proposal_id", "quorum", "receipt_version", "root_id", "state",
}
MATERIAL_FIELDS = {
    "certificate_id", "constructor_set", "constructor_set_commitment",
    "construction_version", "nonce", "target_domain", "target_epoch",
}
VOTE_FIELDS = {
    "certificate_id", "constructor_id", "constructor_set_commitment", "nonce",
    "proposal_id", "root_accept_predicate_version", "synthetic_proof",
    "target_domain", "target_epoch", "vote_version",
}
PROHIBITED = (
    "old_authority", "old_root", "old_key", "cross_signature", "cross_sign",
    "wrapped_old", "old_domain", "derivation", "delegation", "authorization_source",
    "authority_parent", "parent_authority",
)


@dataclass(frozen=True)
class ParentageVerification:
    verdict: str
    reason_code: str
    root_id: str | None
    authority_parent_edge_count: int
    prohibited_old_authority_relation_count: int
    verifier_version: str = "NLC-M5-T2-INDEPENDENT-PARENTAGE-VERIFIER/1.0"


class _Reject(ValueError):
    def __init__(self, code: str):
        self.code = code


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _Reject("DUPLICATE_RECEIPT_FIELD")
        result[key] = value
    return result


def _parse(raw: bytes) -> dict:
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs)
    except _Reject:
        raise
    except (UnicodeError, json.JSONDecodeError):
        raise _Reject("RECEIPT_MALFORMED") from None
    if not isinstance(value, dict):
        raise _Reject("RECEIPT_MALFORMED")
    return value


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, float):
        raise _Reject("RECEIPT_MALFORMED")
    if isinstance(value, (bool, int)):
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {unicodedata.normalize("NFC", key): _normalize(item) for key, item in value.items()}
    raise _Reject("RECEIPT_MALFORMED")


def _canonical(value: Any) -> bytes:
    return json.dumps(_normalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(tag: bytes, raw: bytes) -> str:
    return hashlib.sha256(tag + raw).hexdigest()


def _contains_prohibited(value: Any) -> bool:
    if isinstance(value, dict):
        safe_relation_fields = {
            "authority_parent_edges", "authority_ancestry",
            "prohibited_old_authority_relations", "parentage_declaration",
        }
        return any(
            (key not in safe_relation_fields and any(token in key.lower().replace("-", "_") for token in PROHIBITED))
            or (key != "parentage_declaration" and _contains_prohibited(item))
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_prohibited(item) for item in value)
    if isinstance(value, str):
        if value in {
            "CERTIFICATE_BORN_NO_AUTHORITY_PARENT", "RECONSTITUTION_CERTIFICATE",
            "CONSTRUCTOR_VOTE",
        }:
            return False
        folded = value.lower().replace("-", "_")
        return any(token in folded for token in PROHIBITED)
    return False


def _reject(code: str, root_id=None, edges=0, relations=0) -> ParentageVerification:
    return ParentageVerification("REJECT", code, root_id, edges, relations)


def verify_parentless_root(
    receipt_bytes: bytes, certificate_bytes: bytes, context: RootAcceptContext,
) -> ParentageVerification:
    root_id = None
    try:
        receipt = _parse(receipt_bytes)
        if _contains_prohibited(receipt):
            raise _Reject("OLD_AUTHORITY_RELATION_PROHIBITED")
        if set(receipt) != RECEIPT_FIELDS or _canonical(receipt) != receipt_bytes:
            raise _Reject("RECEIPT_SCHEMA_OR_CANONICAL_MISMATCH")
        root_id = receipt["root_id"]
        accepted = verify_root_accept(certificate_bytes, context)
        if accepted.verdict != "ACCEPT" or accepted.certificate_id is None:
            raise _Reject("CERTIFICATE_NOT_ROOT_ACCEPTED")
        if receipt["certificate_id"] != accepted.certificate_id:
            raise _Reject("CERTIFICATE_ID_MISMATCH")
        if receipt["certificate_commitment"] != hashlib.sha256(certificate_bytes).hexdigest():
            raise _Reject("CERTIFICATE_COMMITMENT_MISMATCH")
        cert = json.loads(certificate_bytes)
        material = receipt["construction_material"]
        if not isinstance(material, dict) or set(material) != MATERIAL_FIELDS:
            raise _Reject("CONSTRUCTION_MATERIAL_MALFORMED")
        expected_set = list(CONSTRUCTORS)
        set_commitment = _sha(SET_TAG, _canonical(expected_set))
        expected_material = {
            "certificate_id": accepted.certificate_id,
            "constructor_set": expected_set,
            "constructor_set_commitment": set_commitment,
            "construction_version": "NLC-ROOT-CONSTRUCTOR/1.0",
            "nonce": cert["nonce"], "target_domain": cert["target_domain"],
            "target_epoch": cert["target_epoch"],
        }
        if material != expected_material or receipt["constructor_set_commitment"] != set_commitment:
            raise _Reject("CONSTRUCTION_MATERIAL_BINDING_MISMATCH")
        proposal_id = _sha(PROPOSAL_TAG, _canonical(expected_material))
        expected_root = _sha(ROOT_TAG, _canonical(expected_material))
        if receipt["proposal_id"] != proposal_id:
            raise _Reject("PROPOSAL_ID_MISMATCH")
        if root_id != expected_root:
            raise _Reject("ROOT_ID_MISMATCH")
        quorum = receipt["quorum"]
        if not isinstance(quorum, dict) or set(quorum) != {"required", "total", "vote_records"}:
            raise _Reject("QUORUM_MALFORMED")
        if (quorum["required"], quorum["total"]) != (2, 2) or not isinstance(quorum["vote_records"], list) or len(quorum["vote_records"]) != 2:
            raise _Reject("QUORUM_NOT_SATISFIED")
        seen = set()
        expected_vote_hashes = []
        for vote in quorum["vote_records"]:
            if not isinstance(vote, dict) or set(vote) != VOTE_FIELDS:
                raise _Reject("VOTE_MALFORMED")
            constructor_id = vote["constructor_id"]
            if constructor_id not in CONSTRUCTORS or constructor_id in seen:
                raise _Reject("QUORUM_CONSTRUCTOR_INVALID")
            seen.add(constructor_id)
            unsigned = {key: value for key, value in vote.items() if key != "synthetic_proof"}
            expected_unsigned = {
                "certificate_id": accepted.certificate_id, "constructor_id": constructor_id,
                "constructor_set_commitment": set_commitment, "nonce": cert["nonce"],
                "proposal_id": proposal_id,
                "root_accept_predicate_version": "NLC-ROOT-ACCEPT-VERIFIER/1.0",
                "target_domain": cert["target_domain"], "target_epoch": cert["target_epoch"],
                "vote_version": "NLC-ROOT-CONSTRUCTOR-VOTE/1.0",
            }
            if unsigned != expected_unsigned:
                raise _Reject("VOTE_BINDING_MISMATCH")
            proof = _sha(VOTE_TAG, CREDENTIALS[constructor_id].encode() + b"\x00" + _canonical(unsigned))
            if vote["synthetic_proof"] != proof:
                raise _Reject("VOTE_PROOF_INVALID")
            expected_vote_hashes.append(hashlib.sha256(_canonical(vote)).hexdigest())
        if seen != set(CONSTRUCTORS):
            raise _Reject("QUORUM_NOT_SATISFIED")
        edges = receipt["authority_parent_edges"]
        relations = receipt["prohibited_old_authority_relations"]
        if not isinstance(edges, list) or edges:
            return _reject("AUTHORITY_PARENT_EDGE_PRESENT", root_id, len(edges) if isinstance(edges, list) else 1, 0)
        if not isinstance(relations, list) or relations:
            return _reject("OLD_AUTHORITY_RELATION_PROHIBITED", root_id, 0, len(relations) if isinstance(relations, list) else 1)
        if receipt["authority_ancestry"] != []:
            raise _Reject("AUTHORITY_ANCESTRY_PRESENT")
        expected_evidence = [
            {"evidence_id": accepted.certificate_id, "evidence_type": "RECONSTITUTION_CERTIFICATE"},
            *[{"evidence_id": digest, "evidence_type": "CONSTRUCTOR_VOTE"} for digest in expected_vote_hashes],
        ]
        if receipt["evidence_ancestry"] != expected_evidence:
            raise _Reject("EVIDENCE_ANCESTRY_MISMATCH")
        if receipt["parentage_declaration"] != "CERTIFICATE_BORN_NO_AUTHORITY_PARENT" or receipt["parentage_version"] != "NLC-ROOT-PARENTAGE-PROOF/1.0":
            raise _Reject("PARENTAGE_PROOF_INVALID")
        if receipt["state"] != "CONSTRUCTED_NOT_ACTIVE" or receipt["activation_status"] != "NOT_ACTIVE / NOT_CUTOVER_COMMITTED":
            raise _Reject("FORBIDDEN_ACTIVATION_STATE")
        if receipt["receipt_version"] != "NLC-ROOT-CONSTRUCTION-RECEIPT/1.0":
            raise _Reject("CONSTRUCTION_VERSION_INVALID")
        unsigned_receipt = {key: value for key, value in receipt.items() if key != "construction_proof"}
        if receipt["construction_proof"] != _sha(RECEIPT_TAG, _canonical(unsigned_receipt)):
            raise _Reject("CONSTRUCTION_PROOF_INVALID")
        return ParentageVerification("ACCEPT", "PARENTLESS_ROOT_VERIFIED", root_id, 0, 0)
    except _Reject as exc:
        return _reject(exc.code, root_id)
