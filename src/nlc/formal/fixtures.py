"""Deterministic synthetic states used by the NLC-M0-T1 golden corpus."""

from __future__ import annotations

import hashlib

from .model import *
from .registry import ADMISSIBLE_TYPE_SPECS, CRITICAL_INFLUENCE_NODES, TRANSFORM_SPECS


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def sterility_state(*, opaque: bool = False) -> SterilityState:
    transfers = ()
    if opaque:
        transfers = (
            TransferObject(
                "transfer_opaque_1",
                TypeClass.OPAQUE_QUARANTINED,
                2,
                STERILE_SCHEMA_ID,
                AdmissionDecision.QUARANTINE,
                OpaqueType.ARBITRARY_ENCRYPTED_CARRIER,
            ),
        )
    return SterilityState(
        STERILE_SCHEMA_ID,
        ADMISSIBLE_TYPE_SPECS,
        tuple(ForbiddenType),
        tuple(OpaqueType),
        TRANSFORM_SPECS,
        tuple(AuthorityTerminalPredicate),
        tuple(AuthorityPotential),
        tuple(AdmissionDecision),
        transfers,
    )


def influence_state(*, unknown: bool = False) -> InfluenceState:
    if unknown:
        edge = InfluenceEdge(
            "IE_UNKNOWN_1", "CloudControl_n", "RootConstructor_Q1", InfluenceEdgeType.CONTROLS,
            TimeInterval(0, 40), EpistemicLabel.UNOBSERVABLE, InfluenceClass.UNKNOWN,
            (), ObservationStatus.MISSING, DischargeDisposition.QUARANTINE, "DISCHARGE_CRITICAL_UNKNOWN",
        )
    else:
        edge = InfluenceEdge(
            "IE_OBSERVED_1", "EvidenceSigner", "LedgerRoot", InfluenceEdgeType.ATTESTS,
            TimeInterval(0, 40), EpistemicLabel.OBSERVED, InfluenceClass.DIRECT,
            ("evidence_1",), ObservationStatus.COMPLETE_FOR_INTERVAL, DischargeDisposition.EXCLUDE,
            "DISCHARGE_DISTINCT_SOURCE",
        )
    return InfluenceState(CRITICAL_INFLUENCE_NODES, (edge,))


def _certificates() -> tuple[CertificateProposal, ...]:
    return (
        CertificateProposal("Cert_R1", AuthorityDomain.NEW_1, digest("Cert_R1")),
        CertificateProposal("Cert_R2", AuthorityDomain.NEW_2, digest("Cert_R2")),
    )


def cutover_state(phase: CutoverPhase = CutoverPhase.IDLE) -> CutoverState:
    root = RootRecord(RootRecordState.NONE)
    slot_state = CutoverSlotState.OPEN
    votes: tuple[ConstructorVote, ...] = ()
    ownership = (ScopeOwnership("s*", ScopeOwner.OLD), ScopeOwnership("s_2", ScopeOwner.OLD))
    if phase is CutoverPhase.ROOT_PREPARED:
        root = RootRecord(RootRecordState.PREPARED, "Root_R1_g+1", digest("Cert_R1"), AuthorityDomain.NEW_1, Generation.NEXT)
        votes = (
            ConstructorVote("Q1", "CutoverSlot_s*_g+1", digest("Cert_R1-proposal")),
            ConstructorVote("Q2", "CutoverSlot_s*_g+1", digest("Cert_R1-proposal")),
        )
        ownership = (ScopeOwnership("s*", ScopeOwner.NONE), ScopeOwnership("s_2", ScopeOwner.OLD))
    elif phase is CutoverPhase.COMMITTED:
        root = RootRecord(RootRecordState.COMMITTED, "Root_R1_g+1", digest("Cert_R1"), AuthorityDomain.NEW_1, Generation.NEXT)
        slot_state = CutoverSlotState.COMMITTED
        votes = (
            ConstructorVote("Q1", "CutoverSlot_s*_g+1", digest("Cert_R1-proposal")),
            ConstructorVote("Q2", "CutoverSlot_s*_g+1", digest("Cert_R1-proposal")),
        )
        ownership = (ScopeOwnership("s*", ScopeOwner.NEW_1), ScopeOwnership("s_2", ScopeOwner.OLD))
    elif phase is CutoverPhase.PARTITIONED:
        votes = (
            ConstructorVote("Q1", "CutoverSlot_s*_g+1", digest("Cert_R1-proposal")),
            ConstructorVote("Q2", "CutoverSlot_s*_g+1", digest("Cert_R2-proposal")),
        )
    return CutoverState(
        AuthorityDomain.OLD,
        (AuthorityDomain.NEW_1, AuthorityDomain.NEW_2),
        _certificates(),
        ("s*", "s_2"),
        "CutoverSlot_s*_g+1",
        slot_state,
        (ConstructorReplica("Q1"), ConstructorReplica("Q2")),
        votes,
        2,
        2,
        phase,
        root,
        (
            EpochRegistryEntry(AuthorityDomain.OLD, Generation.CURRENT, True),
            EpochRegistryEntry(AuthorityDomain.NEW_1, Generation.NEXT, phase is CutoverPhase.COMMITTED),
            EpochRegistryEntry(AuthorityDomain.NEW_2, Generation.NEXT, False),
        ),
        ownership,
    )


def recovery_state(slot_state: RecoverySlotState = RecoverySlotState.UNUSED) -> RecoveryState:
    if slot_state is RecoverySlotState.UNUSED:
        slot = RecoverySlot("RecoverySlot_s*_cp*", "cp*", "s*", slot_state)
        fence = SettlementFenceState.UNSETTLED
    elif slot_state is RecoverySlotState.RECOVERY_HOLD:
        slot = RecoverySlot("RecoverySlot_s*_cp*", "cp*", "s*", slot_state, hold_reason="UNOBSERVABLE_FINALITY")
        fence = SettlementFenceState.UNKNOWN
    elif slot_state is RecoverySlotState.PREPARED:
        slot = RecoverySlot("RecoverySlot_s*_cp*", "cp*", "s*", slot_state, intent_hash=digest("recovery-intent"))
        fence = SettlementFenceState.PREPARED
    else:
        slot = RecoverySlot("RecoverySlot_s*_cp*", "cp*", "s*", slot_state, output_set_id="OutputSet_s*_cp*_1", receipt_id="RecoveryReceipt_1")
        fence = SettlementFenceState.FINAL
    adapters = (
        ExternalAdapter("Adapter_IDEMPOTENT", ExternalAdapterClass.IDEMPOTENT, idempotency_key="idem_1"),
        ExternalAdapter("Adapter_ESCROWED", ExternalAdapterClass.ESCROWED, escrow_transaction_id="escrow_1"),
        ExternalAdapter("Adapter_FENCED", ExternalAdapterClass.FENCED, fence_generation=Generation.NEXT),
        ExternalAdapter("Adapter_UNOBSERVABLE", ExternalAdapterClass.UNOBSERVABLE),
    )
    return RecoveryState(
        ("cp*",), ("s*", "s_2"), "RecoverySlotService_1",
        ("RecoveryClient_1", "RecoveryClient_2"),
        (RecoveryAttempt("RecoveryAttempt_1", "Cert_R1"), RecoveryAttempt("RecoveryAttempt_2", "Cert_R2")),
        (slot,), adapters, fence,
    )


def full_formal_state(
    *,
    cutover_phase: CutoverPhase = CutoverPhase.IDLE,
    recovery_slot_state: RecoverySlotState = RecoverySlotState.UNUSED,
    unknown_influence: bool = True,
    opaque_transfer: bool = False,
) -> NLCFormalState:
    return NLCFormalState(
        FormalConfiguration(FORMAL_SCHEMA_VERSION, MANIFEST_VERSION, STERILE_SCHEMA_ID, FormalBounds()),
        sterility_state(opaque=opaque_transfer),
        influence_state(unknown=unknown_influence),
        cutover_state(cutover_phase),
        recovery_state(recovery_slot_state),
        (
            AuthorityDomainEntry(AuthorityDomain.OLD, Generation.CURRENT, False),
            AuthorityDomainEntry(AuthorityDomain.NEW_1, Generation.NEXT, True),
            AuthorityDomainEntry(AuthorityDomain.NEW_2, Generation.NEXT, True),
        ),
        0,
        40,
    )

