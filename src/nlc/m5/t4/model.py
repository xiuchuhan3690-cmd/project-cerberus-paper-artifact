"""Closed types and frozen identifiers for Epoch_Barrier_Suite_v1."""

from __future__ import annotations
from dataclasses import dataclass


SUITE_VERSION = "NLC-EPOCH-BARRIER-SUITE/1.0"
ARTIFACT_VERSION = "NLC-EPOCH-AUTHORITY-ARTIFACT/1.0"
EVIDENCE_VERSION = "NLC-EPOCH-BARRIER-EVIDENCE/1.0"
DECISION_VERSION = "NLC-EPOCH-BARRIER-DECISION/1.0"
COMBINED_VERSION = "NLC-EPOCH-BARRIER-COMBINED/1.0"
BARRIER_ORDER = ("NAMESPACE", "VERIFIER_DOMAIN", "CRYPTOGRAPHIC_ROOT", "SEMANTIC_GRAMMAR", "PROTOCOL_ADAPTER")
BARRIER_VERSIONS = {
    "NAMESPACE": "NLC-NAMESPACE-BARRIER/1.0",
    "VERIFIER_DOMAIN": "NLC-VERIFIER-DOMAIN-BARRIER/1.0",
    "CRYPTOGRAPHIC_ROOT": "NLC-CRYPTOGRAPHIC-ROOT-BARRIER/1.0",
    "SEMANTIC_GRAMMAR": "NLC-SEMANTIC-GRAMMAR-BARRIER/1.0",
    "PROTOCOL_ADAPTER": "NLC-PROTOCOL-ADAPTER-BARRIER/1.0",
}
VERIFIER_VERSIONS = {name: f"NLC-{name.replace('_', '-')}-VERIFIER/1.0" for name in BARRIER_ORDER}


@dataclass(frozen=True)
class EpochContext:
    active_root_id: str
    cutover_slot_id: str
    cutover_receipt_id: str
    cutover_receipt_sha256: str
    target_domain: str
    target_epoch: int
    namespace_id: str
    namespace_version: str
    verifier_domain_id: str
    verifier_version: str
    cryptographic_root_id: str
    semantic_grammar_id: str
    protocol_adapter_id: str
    protocol_adapter_version: str
    suite_version: str = SUITE_VERSION


@dataclass(frozen=True)
class BarrierDecision:
    barrier_id: str
    barrier_version: str
    decision_version: str
    evidence_commitment: str
    expected_domain: str
    expected_epoch: int
    input_artifact_id: str
    observed_domain: str
    observed_epoch: int
    reason_code: str
    verdict: str
    verifier_id: str
    verifier_version: str


@dataclass(frozen=True)
class CombinedDecision:
    decision_bytes: bytes
    decision_id: str
    verdict: str
    reason_code: str
    authority_effective: bool
