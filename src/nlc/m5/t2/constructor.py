"""2-of-2 deterministic root constructor using frozen M5-T1 RootAccept.

The synthetic vote proof is a finite mutation-detection abstraction, not a
production signature, threshold-cryptography, KMS, or HSM claim.
"""

from __future__ import annotations

import hashlib
import json
from typing import Iterable

from m1.canonical import canonical_bytes
from nlc.m5.t1.verifier import RootAcceptContext, verify_root_accept
from .model import (
    CONSTRUCTION_VERSION, CONSTRUCTOR_SET, PARENTAGE_VERSION, RECEIPT_VERSION,
    SYNTHETIC_CREDENTIALS, VOTE_VERSION, ConstructorVote, RootConstructionResult,
)


ROOT_TAG = b"NLC-M5-T2-PARENTLESS-ROOT-v1\x00"
PROPOSAL_TAG = b"NLC-M5-T2-ROOT-PROPOSAL-v1\x00"
SET_TAG = b"NLC-M5-T2-CONSTRUCTOR-SET-v1\x00"
VOTE_TAG = b"NLC-M5-T2-SYNTHETIC-VOTE-v1\x00"
RECEIPT_TAG = b"NLC-M5-T2-CONSTRUCTION-RECEIPT-v1\x00"


class ConstructionError(ValueError):
    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def _sha(tag: bytes, raw: bytes) -> str:
    return hashlib.sha256(tag + raw).hexdigest()


def _certificate_fields(certificate_bytes: bytes) -> dict:
    try:
        value = json.loads(certificate_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise ConstructionError("CERTIFICATE_MALFORMED") from None
    if not isinstance(value, dict):
        raise ConstructionError("CERTIFICATE_MALFORMED")
    return value


def constructor_set_commitment(constructor_set: Iterable[str]) -> str:
    values = sorted(constructor_set)
    if values != list(CONSTRUCTOR_SET) or len(values) != len(set(values)):
        raise ConstructionError("CONSTRUCTOR_SET_INVALID")
    return _sha(SET_TAG, canonical_bytes(values))


def construction_material(
    certificate_id: str, target_domain: str, target_epoch: int, nonce: str,
    constructor_set: Iterable[str],
) -> dict:
    values = sorted(constructor_set)
    set_commitment = constructor_set_commitment(values)
    return {
        "certificate_id": certificate_id,
        "constructor_set": values,
        "constructor_set_commitment": set_commitment,
        "construction_version": CONSTRUCTION_VERSION,
        "nonce": nonce,
        "target_domain": target_domain,
        "target_epoch": target_epoch,
    }


def _proposal(material: dict) -> str:
    return _sha(PROPOSAL_TAG, canonical_bytes(material))


def _root_id(material: dict) -> str:
    return _sha(ROOT_TAG, canonical_bytes(material))


def vote_dict(vote: ConstructorVote, *, include_proof: bool = True) -> dict:
    value = {
        "certificate_id": vote.certificate_id,
        "constructor_id": vote.constructor_id,
        "constructor_set_commitment": vote.constructor_set_commitment,
        "nonce": vote.nonce,
        "proposal_id": vote.proposal_id,
        "root_accept_predicate_version": vote.root_accept_predicate_version,
        "target_domain": vote.target_domain,
        "target_epoch": vote.target_epoch,
        "vote_version": vote.vote_version,
    }
    if include_proof:
        value["synthetic_proof"] = vote.synthetic_proof
    return value


def vote_bytes(vote: ConstructorVote) -> bytes:
    return canonical_bytes(vote_dict(vote))


def _vote_proof(unsigned: dict, credential: str) -> str:
    return _sha(VOTE_TAG, credential.encode("utf-8") + b"\x00" + canonical_bytes(unsigned))


def validate_vote_record(vote: ConstructorVote) -> None:
    if vote.constructor_id not in CONSTRUCTOR_SET:
        raise ConstructionError("UNKNOWN_CONSTRUCTOR")
    if vote.vote_version != VOTE_VERSION:
        raise ConstructionError("VOTE_VERSION_INVALID")
    expected = _vote_proof(
        vote_dict(vote, include_proof=False), SYNTHETIC_CREDENTIALS[vote.constructor_id],
    )
    if vote.synthetic_proof != expected:
        raise ConstructionError("VOTE_PROOF_INVALID")


def issue_vote(
    constructor_id: str,
    synthetic_credential: str,
    certificate_bytes: bytes,
    context: RootAcceptContext,
) -> ConstructorVote:
    if constructor_id not in CONSTRUCTOR_SET:
        raise ConstructionError("UNKNOWN_CONSTRUCTOR")
    if SYNTHETIC_CREDENTIALS[constructor_id] != synthetic_credential:
        raise ConstructionError("CONSTRUCTOR_IDENTITY_SPOOFED")
    accepted = verify_root_accept(certificate_bytes, context)
    if accepted.verdict != "ACCEPT" or accepted.certificate_id is None:
        raise ConstructionError("CERTIFICATE_NOT_ROOT_ACCEPTED")
    cert = _certificate_fields(certificate_bytes)
    material = construction_material(
        accepted.certificate_id, cert["target_domain"], cert["target_epoch"],
        cert["nonce"], cert["threshold_constructor_set"],
    )
    provisional = ConstructorVote(
        VOTE_VERSION, constructor_id, _proposal(material), accepted.certificate_id,
        cert["target_domain"], cert["target_epoch"], cert["nonce"],
        material["constructor_set_commitment"], accepted.predicate_version, "",
    )
    proof = _vote_proof(vote_dict(provisional, include_proof=False), synthetic_credential)
    return ConstructorVote(**{**provisional.__dict__, "synthetic_proof": proof})


def _validate_vote(vote: ConstructorVote, material: dict, proposal_id: str) -> None:
    validate_vote_record(vote)
    expected = ConstructorVote(
        VOTE_VERSION, vote.constructor_id, proposal_id, material["certificate_id"],
        material["target_domain"], material["target_epoch"], material["nonce"],
        material["constructor_set_commitment"], "NLC-ROOT-ACCEPT-VERIFIER/1.0", "",
    )
    if vote_dict(vote, include_proof=False) != vote_dict(expected, include_proof=False):
        raise ConstructionError("VOTE_BINDING_MISMATCH")


def construct_root(
    certificate_bytes: bytes,
    context: RootAcceptContext,
    votes: Iterable[ConstructorVote],
) -> RootConstructionResult:
    accepted = verify_root_accept(certificate_bytes, context)
    if accepted.verdict != "ACCEPT" or accepted.certificate_id is None:
        raise ConstructionError("CERTIFICATE_NOT_ROOT_ACCEPTED")
    cert = _certificate_fields(certificate_bytes)
    material = construction_material(
        accepted.certificate_id, cert["target_domain"], cert["target_epoch"],
        cert["nonce"], cert["threshold_constructor_set"],
    )
    proposal_id = _proposal(material)
    vote_list = list(votes)
    if len({vote.constructor_id for vote in vote_list}) != len(vote_list):
        raise ConstructionError("DUPLICATE_CONSTRUCTOR_IDENTITY")
    for vote in vote_list:
        _validate_vote(vote, material, proposal_id)
    by_constructor = {vote.constructor_id: vote for vote in vote_list}
    if set(by_constructor) != set(CONSTRUCTOR_SET):
        raise ConstructionError("QUORUM_NOT_SATISFIED")
    ordered_votes = [by_constructor[name] for name in CONSTRUCTOR_SET]
    root_id = _root_id(material)
    evidence_ancestry = [
        {"evidence_id": accepted.certificate_id, "evidence_type": "RECONSTITUTION_CERTIFICATE"},
        *[
            {"evidence_id": hashlib.sha256(vote_bytes(vote)).hexdigest(), "evidence_type": "CONSTRUCTOR_VOTE"}
            for vote in ordered_votes
        ],
    ]
    receipt_without_proof = {
        "activation_status": "NOT_ACTIVE / NOT_CUTOVER_COMMITTED",
        "authority_ancestry": [],
        "authority_parent_edges": [],
        "certificate_commitment": hashlib.sha256(certificate_bytes).hexdigest(),
        "certificate_id": accepted.certificate_id,
        "construction_material": material,
        "constructor_set_commitment": material["constructor_set_commitment"],
        "evidence_ancestry": evidence_ancestry,
        "parentage_declaration": "CERTIFICATE_BORN_NO_AUTHORITY_PARENT",
        "parentage_version": PARENTAGE_VERSION,
        "prohibited_old_authority_relations": [],
        "proposal_id": proposal_id,
        "quorum": {"required": 2, "total": 2, "vote_records": [vote_dict(vote) for vote in ordered_votes]},
        "receipt_version": RECEIPT_VERSION,
        "root_id": root_id,
        "state": "CONSTRUCTED_NOT_ACTIVE",
    }
    proof = _sha(RECEIPT_TAG, canonical_bytes(receipt_without_proof))
    receipt = {**receipt_without_proof, "construction_proof": proof}
    return RootConstructionResult(canonical_bytes(receipt), root_id, proposal_id, "CONSTRUCTED_NOT_ACTIVE")
