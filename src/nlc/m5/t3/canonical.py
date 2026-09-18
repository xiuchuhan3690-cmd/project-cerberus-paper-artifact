"""Canonical identities for CutoverSlot, proposal, and receipt."""

from __future__ import annotations

import hashlib

from m1.canonical import canonical_bytes
from .model import CutoverSlot, RootProposal, SLOT_VERSION, PROPOSAL_VERSION


SLOT_TAG = b"NLC-M5-T3-CUTOVER-SLOT-v1\x00"
PROPOSAL_TAG = b"NLC-M5-T3-CUTOVER-PROPOSAL-v1\x00"
RECEIPT_TAG = b"NLC-M5-T3-CUTOVER-RECEIPT-v1\x00"
PARENT_TAG = b"NLC-M5-T3-FROZEN-PARENT-v1\x00"


def tagged_hash(tag: bytes, value: dict) -> str:
    return hashlib.sha256(tag + canonical_bytes(value)).hexdigest()


def slot_material(slot: CutoverSlot | dict) -> dict:
    value = slot.__dict__ if isinstance(slot, CutoverSlot) else slot
    return {key: value[key] for key in (
        "fence_identity", "frozen_parent_state_commitment", "generation",
        "protected_scope", "slot_version", "target_domain", "target_epoch",
    )}


def make_slot(target_domain: str, target_epoch: int, generation: int,
              protected_scope: str, fence_identity: str,
              frozen_parent_state_commitment: str) -> CutoverSlot:
    material = {
        "fence_identity": fence_identity,
        "frozen_parent_state_commitment": frozen_parent_state_commitment,
        "generation": generation, "protected_scope": protected_scope,
        "slot_version": SLOT_VERSION, "target_domain": target_domain,
        "target_epoch": target_epoch,
    }
    return CutoverSlot(**material, slot_id=tagged_hash(SLOT_TAG, material))


def proposal_material(proposal: RootProposal | dict) -> dict:
    value = proposal.__dict__ if isinstance(proposal, RootProposal) else proposal
    return {key: value[key] for key in (
        "certificate_id", "construction_receipt_id", "proposal_version",
        "proposer_identity", "proposer_version", "root_id", "slot_id",
    )}


def make_proposal(root_id: str, certificate_id: str, construction_receipt_id: str,
                  slot_id: str, proposer_identity: str,
                  proposer_version: str) -> RootProposal:
    material = {
        "certificate_id": certificate_id,
        "construction_receipt_id": construction_receipt_id,
        "proposal_version": PROPOSAL_VERSION,
        "proposer_identity": proposer_identity,
        "proposer_version": proposer_version,
        "root_id": root_id, "slot_id": slot_id,
    }
    return RootProposal(**material, proposal_id=tagged_hash(PROPOSAL_TAG, material))
