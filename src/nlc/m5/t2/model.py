"""Closed immutable types for the finite M5-T2 constructor abstraction."""

from __future__ import annotations

from dataclasses import dataclass


CONSTRUCTION_VERSION = "NLC-ROOT-CONSTRUCTOR/1.0"
VOTE_VERSION = "NLC-ROOT-CONSTRUCTOR-VOTE/1.0"
RECEIPT_VERSION = "NLC-ROOT-CONSTRUCTION-RECEIPT/1.0"
PARENTAGE_VERSION = "NLC-ROOT-PARENTAGE-PROOF/1.0"
CONSTRUCTOR_SET = ("RootConstructor_Q1", "RootConstructor_Q2")
SYNTHETIC_CREDENTIALS = {
    "RootConstructor_Q1": "synthetic-share:q1-v1",
    "RootConstructor_Q2": "synthetic-share:q2-v1",
}


@dataclass(frozen=True)
class ConstructorVote:
    vote_version: str
    constructor_id: str
    proposal_id: str
    certificate_id: str
    target_domain: str
    target_epoch: int
    nonce: str
    constructor_set_commitment: str
    root_accept_predicate_version: str
    synthetic_proof: str


@dataclass(frozen=True)
class RootConstructionResult:
    receipt_bytes: bytes
    root_id: str
    proposal_id: str
    state: str
