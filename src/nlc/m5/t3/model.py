"""Closed data types and identifiers for NLC-M5-T3."""

from __future__ import annotations

from dataclasses import dataclass


SLOT_VERSION = "NLC-CUTOVER-SLOT/1.0"
PROPOSAL_VERSION = "NLC-CUTOVER-PROPOSAL/1.0"
STORE_VERSION = "NLC-CUTOVER-STORE/1.0"
RECEIPT_VERSION = "NLC-CUTOVER-RECEIPT/1.0"
ENGINE_VERSION = "NLC-CUTOVER-ENGINE/1.0"
FENCE_IDENTITY = "NLC-M5-T3-SYNTHETIC-SCOPE-FENCE/1.0"


@dataclass(frozen=True)
class CutoverSlot:
    slot_version: str
    target_domain: str
    target_epoch: int
    generation: int
    protected_scope: str
    fence_identity: str
    frozen_parent_state_commitment: str
    slot_id: str


@dataclass(frozen=True)
class RootProposal:
    proposal_version: str
    root_id: str
    certificate_id: str
    construction_receipt_id: str
    slot_id: str
    proposer_identity: str
    proposer_version: str
    proposal_id: str


@dataclass(frozen=True)
class ActivationResult:
    verdict: str
    reason_code: str
    state: str
    root_status: str
    root_id: str | None
    receipt_bytes: bytes | None


class CutoverError(ValueError):
    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


class InjectedCrash(RuntimeError):
    def __init__(self, point: str):
        super().__init__(point)
        self.point = point
