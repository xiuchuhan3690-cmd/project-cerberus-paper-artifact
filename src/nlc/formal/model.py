"""Immutable finite state types for NLC-M0-T1.

This module encodes domains only.  It deliberately contains no transition,
authority construction, admission, cutover, recovery, or external-effect
behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
from typing import Any


FORMAL_SCHEMA_VERSION = "NLC-FORMAL-STATE/1.0"
STERILE_SCHEMA_ID = "NLC-STERILE-REF/0.1"
MANIFEST_VERSION = "NLC-FORMAL-DOMAINS/1.0"


class FormalValidationError(ValueError):
    """A value is outside the frozen finite formal universe."""


class StableEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class AuthorityDomain(StableEnum):
    OLD = "D_o"
    NEW_1 = "D_1"
    NEW_2 = "D_2"


class ScopeOwner(StableEnum):
    OLD = "D_o"
    NONE = "NONE"
    NEW_1 = "D_1"
    NEW_2 = "D_2"


class Generation(StableEnum):
    CURRENT = "g"
    NEXT = "g+1"


class AdmissionDecision(StableEnum):
    ADMIT = "ADMIT"
    QUARANTINE = "QUARANTINE"
    REJECT = "REJECT"


class AuthorityPotential(StableEnum):
    ABSENT = "ABSENT"
    PRESENT = "PRESENT"
    UNKNOWN = "UNKNOWN"


class TypeClass(StableEnum):
    STERILE = "STERILE"
    AUTHORITY_BEARING = "AUTHORITY_BEARING"
    OPAQUE_QUARANTINED = "OPAQUE_QUARANTINED"
    ANY_MODELED = "ANY_MODELED"


class AuthorityRelevance(StableEnum):
    NONE = "NONE"
    POTENTIAL = "POTENTIAL"
    TERMINAL = "TERMINAL"


class AdmissibleType(StableEnum):
    BOUNDED_INT = "BoundedInt"
    BOOL = "Bool"
    ENUM = "Enum"
    NORMALIZED_STRING = "NormalizedString"
    BOUNDED_TIMESTAMP = "BoundedTimestamp"
    BUSINESS_ID = "BusinessId"
    IMMUTABLE_AGGREGATE = "ImmutableAggregate"
    TERMINAL_BUSINESS_FACT = "TerminalBusinessFact"
    CHECKPOINT_FACT = "CheckpointFact"
    INERT_PROVENANCE_REF = "InertProvenanceRef"


class ForbiddenType(StableEnum):
    EXECUTABLE_CODE = "EXECUTABLE_CODE"
    SCRIPT = "SCRIPT"
    CLOSURE = "CLOSURE"
    CALLBACK = "CALLBACK"
    DYNAMIC_DESERIALIZER = "DYNAMIC_DESERIALIZER"
    OLD_DOMAIN_CREDENTIAL = "OLD_DOMAIN_CREDENTIAL"
    ACCESS_TOKEN = "ACCESS_TOKEN"
    REFRESH_TOKEN = "REFRESH_TOKEN"
    SESSION_TOKEN = "SESSION_TOKEN"
    CAPABILITY = "CAPABILITY"
    DELEGATION_PROOF = "DELEGATION_PROOF"
    PENDING_GRANT = "PENDING_GRANT"
    RETRY_HANDLE = "RETRY_HANDLE"
    CONTINUATION_HANDLE = "CONTINUATION_HANDLE"
    JOB_TOKEN = "JOB_TOKEN"
    VERIFIER_OBJECT = "VERIFIER_OBJECT"
    SIGNING_OBJECT = "SIGNING_OBJECT"
    EXECUTABLE_JOB_STATE = "EXECUTABLE_JOB_STATE"
    OPAQUE_JOB_STATE = "OPAQUE_JOB_STATE"
    EXTENSION_MAP = "EXTENSION_MAP"
    UNKNOWN_NESTED_OBJECT = "UNKNOWN_NESTED_OBJECT"
    AUTHORITY_KIND_IDENTIFIER = "AUTHORITY_KIND_IDENTIFIER"


class OpaqueType(StableEnum):
    ARBITRARY_BYTES = "ARBITRARY_BYTES"
    ARBITRARY_ENCRYPTED_CARRIER = "ARBITRARY_ENCRYPTED_CARRIER"
    UNSUPPORTED_ENCODING = "UNSUPPORTED_ENCODING"
    UNSUPPORTED_COMPRESSION = "UNSUPPORTED_COMPRESSION"
    UNRESOLVED_REFERENCE = "UNRESOLVED_REFERENCE"
    OUT_OF_MODEL_REFERENCE = "OUT_OF_MODEL_REFERENCE"
    UNSUPPORTED_SCHEMA_VERSION = "UNSUPPORTED_SCHEMA_VERSION"
    EXCESSIVE_NESTING = "EXCESSIVE_NESTING"


class AuthorityTerminalPredicate(StableEnum):
    VALIDATE_OLD_CAPABILITY = "ValidateOldCapability"
    CAN_REFRESH_OLD = "CanRefreshOld"
    CAN_DELEGATE_OLD = "CanDelegateOld"
    CAN_CONTINUE_OLD = "CanContinueOld"
    CAN_AUTHORIZE_RECOVERY_OLD = "CanAuthorizeRecoveryOld"
    CAN_CONSTRUCT_AUTHORITY_PARENT = "CanConstructAuthorityParentOldOrNew"


class EpistemicLabel(StableEnum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    UNOBSERVABLE = "UNOBSERVABLE"


class InfluenceClass(StableEnum):
    DIRECT = "DIRECT"
    CERTAIN = "CERTAIN"
    POSSIBLE = "POSSIBLE"
    UNKNOWN = "UNKNOWN"


class ObservationStatus(StableEnum):
    COMPLETE_FOR_INTERVAL = "COMPLETE_FOR_INTERVAL"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"


class DischargeDisposition(StableEnum):
    EXCLUDE = "EXCLUDE"
    QUARANTINE = "QUARANTINE"
    EXPLICIT_RESIDUAL_ASSUMPTION = "EXPLICIT_RESIDUAL_ASSUMPTION"


class InfluenceEdgeType(StableEnum):
    AUTHORIZES = "AUTHORIZES"
    BUILDS = "BUILDS"
    SIGNS = "SIGNS"
    CONFIGURES = "CONFIGURES"
    ADMINISTERS = "ADMINISTERS"
    EXECUTES = "EXECUTES"
    STORES = "STORES"
    DERIVES = "DERIVES"
    VERIFIES = "VERIFIES"
    CONTROLS = "CONTROLS"
    ATTESTS = "ATTESTS"
    WITNESSES = "WITNESSES"


class CutoverPhase(StableEnum):
    IDLE = "IDLE"
    CERT_VERIFIED = "CERT_VERIFIED"
    FENCE_PREPARING = "FENCE_PREPARING"
    FENCE_CONFIRMED = "FENCE_CONFIRMED"
    SLOTS_PREPARED = "SLOTS_PREPARED"
    ROOT_PREPARED = "ROOT_PREPARED"
    COMMITTED = "COMMITTED"
    DELIVERED = "DELIVERED"
    ABORTED = "ABORTED"
    HOLD = "HOLD"
    RECOVERY_HOLD = "RECOVERY_HOLD"
    EFFECT_HALT = "EFFECT_HALT"
    PARTITIONED = "PARTITIONED"


class RootRecordState(StableEnum):
    NONE = "NONE"
    PREPARED = "PREPARED"
    COMMITTED = "COMMITTED"


class CutoverSlotState(StableEnum):
    OPEN = "OPEN"
    COMMITTED = "COMMITTED"


class RecoverySlotState(StableEnum):
    UNUSED = "UNUSED"
    PREPARED = "PREPARED"
    COMMITTED = "COMMITTED"
    RECOVERY_HOLD = "RECOVERY_HOLD"


class ExternalAdapterClass(StableEnum):
    IDEMPOTENT = "IDEMPOTENT"
    ESCROWED = "ESCROWED"
    FENCED = "FENCED"
    UNOBSERVABLE = "UNOBSERVABLE"


class SettlementFenceState(StableEnum):
    UNSETTLED = "UNSETTLED"
    PREPARED = "PREPARED"
    FINAL = "FINAL"
    UNKNOWN = "UNKNOWN"
    EFFECT_HALT = "EFFECT_HALT"


def _require_tuple(name: str, value: Any) -> None:
    if not isinstance(value, tuple):
        raise FormalValidationError(f"{name} must be an immutable tuple")


def _canonical_item_key(item: Any) -> str:
    if isinstance(item, Enum):
        return item.value
    if isinstance(item, str):
        return item
    for attribute in (
        "node_id", "edge_id", "transform_id", "object_id", "certificate_id",
        "replica_id", "scope_id", "attempt_id", "recovery_slot_id", "adapter_id",
    ):
        if hasattr(item, attribute):
            return str(getattr(item, attribute))
    if hasattr(item, "type_id"):
        return str(item.type_id)
    if hasattr(item, "domain"):
        return str(item.domain)
    return repr(item)


def _normalize_tuple_fields(instance: Any, names: tuple[str, ...]) -> None:
    for name in names:
        value = getattr(instance, name)
        _require_tuple(name, value)
        object.__setattr__(instance, name, tuple(sorted(value, key=_canonical_item_key)))


def _unique(name: str, values: tuple[Any, ...], key=lambda item: item) -> None:
    keys = [key(item) for item in values]
    if len(keys) != len(set(keys)):
        raise FormalValidationError(f"duplicate ID/value in {name}")


def _hex_digest(name: str, value: str) -> None:
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise FormalValidationError(f"{name} must be a lowercase SHA-256 hex digest")


def _require_enum(name: str, value: Any, enum_type: type[Enum]) -> None:
    if not isinstance(value, enum_type):
        raise FormalValidationError(f"{name} must be a typed {enum_type.__name__}")


@dataclass(frozen=True, slots=True)
class FormalBounds:
    authority_domain_count: int = 3
    candidate_new_domain_count: int = 2
    protected_scope_count: int = 2
    proposal_count: int = 2
    checkpoint_count: int = 1
    recovery_attempt_count: int = 2
    constructor_replica_count: int = 2
    constructor_quorum_threshold: int = 2
    constructor_quorum_denominator: int = 2
    recovery_slot_service_count: int = 1
    recovery_client_count: int = 2
    transfer_nesting_maximum: int = 2
    transform_depth_maximum: int = 4
    trace_bound: int = 40
    critical_influence_node_count: int = 31
    transform_type_count: int = 14
    adapter_class_count: int = 4

    def __post_init__(self) -> None:
        expected = (3, 2, 2, 2, 1, 2, 2, 2, 2, 1, 2, 2, 4, 40, 31, 14, 4)
        actual = tuple(getattr(self, field.name) for field in fields(self))
        if actual != expected:
            raise FormalValidationError("frozen NLC-FR1 cardinalities changed")


@dataclass(frozen=True, slots=True)
class TypeSpec:
    type_id: AdmissibleType
    finite_bound: str
    normalization_rule: str


@dataclass(frozen=True, slots=True)
class TransformSpec:
    transform_id: str
    input_type_class: TypeClass
    output_type_class: TypeClass
    deterministic: bool
    partial: bool
    authority_relevance: AuthorityRelevance
    enabled_in_reference_model: bool


@dataclass(frozen=True, slots=True)
class TransferObject:
    object_id: str
    type_class: TypeClass
    nesting_depth: int
    schema_version: str
    decision: AdmissionDecision
    opaque_reason: OpaqueType | None = None

    def __post_init__(self) -> None:
        _require_enum("type_class", self.type_class, TypeClass)
        _require_enum("decision", self.decision, AdmissionDecision)
        if self.opaque_reason is not None:
            _require_enum("opaque_reason", self.opaque_reason, OpaqueType)
        if not 0 <= self.nesting_depth <= 2:
            raise FormalValidationError("transfer nesting exceeds frozen maximum 2")
        if self.schema_version != STERILE_SCHEMA_ID:
            if self.opaque_reason is not OpaqueType.UNSUPPORTED_SCHEMA_VERSION:
                raise FormalValidationError("unsupported schema version must remain explicit")
            if self.decision is AdmissionDecision.ADMIT:
                raise FormalValidationError("unsupported schema version cannot be admitted")
        if self.type_class is TypeClass.OPAQUE_QUARANTINED:
            if self.opaque_reason is None or self.decision is not AdmissionDecision.QUARANTINE:
                raise FormalValidationError("opaque objects require an explicit quarantine reason")
        elif self.opaque_reason is not None:
            raise FormalValidationError("non-opaque object cannot carry an opaque reason")


@dataclass(frozen=True, slots=True)
class SterilityState:
    schema_id: str
    admissible_types: tuple[TypeSpec, ...]
    forbidden_types: tuple[ForbiddenType, ...]
    opaque_types: tuple[OpaqueType, ...]
    transforms: tuple[TransformSpec, ...]
    authority_terminal_predicates: tuple[AuthorityTerminalPredicate, ...]
    authority_potential_states: tuple[AuthorityPotential, ...]
    decisions: tuple[AdmissionDecision, ...]
    transfer_objects: tuple[TransferObject, ...]
    transform_depth_maximum: int = 4

    def __post_init__(self) -> None:
        _normalize_tuple_fields(self, ("admissible_types", "forbidden_types", "opaque_types", "transforms", "authority_terminal_predicates", "authority_potential_states", "decisions", "transfer_objects"))
        if self.schema_id != STERILE_SCHEMA_ID or self.transform_depth_maximum != 4:
            raise FormalValidationError("sterility schema/version or transform depth changed")
        if set(item.type_id for item in self.admissible_types) != set(AdmissibleType):
            raise FormalValidationError("admissible type inventory is incomplete")
        if set(self.forbidden_types) != set(ForbiddenType) or set(self.opaque_types) != set(OpaqueType):
            raise FormalValidationError("forbidden/opaque type inventory changed")
        if set(self.authority_terminal_predicates) != set(AuthorityTerminalPredicate):
            raise FormalValidationError("authority terminal predicates changed")
        if set(self.authority_potential_states) != set(AuthorityPotential) or set(self.decisions) != set(AdmissionDecision):
            raise FormalValidationError("authority potential/decision vocabulary changed")
        _unique("transforms", self.transforms, lambda item: item.transform_id)
        _unique("transfer_objects", self.transfer_objects, lambda item: item.object_id)
        if len(self.transforms) != 14:
            raise FormalValidationError("F_auth must contain exactly 14 transforms")


@dataclass(frozen=True, slots=True)
class TimeInterval:
    time_start: int
    time_end: int

    def __post_init__(self) -> None:
        if isinstance(self.time_start, bool) or isinstance(self.time_end, bool) or not self.time_start <= self.time_end:
            raise FormalValidationError("time interval must be ordered bounded integers")
        if not (0 <= self.time_start <= 40 and 0 <= self.time_end <= 40):
            raise FormalValidationError("time interval exceeds trace bound")


@dataclass(frozen=True, slots=True)
class InfluenceNode:
    node_id: str
    category: str
    residual_assumption_allowed: bool


@dataclass(frozen=True, slots=True)
class InfluenceEdge:
    edge_id: str
    src: str
    dst: str
    edge_type: InfluenceEdgeType
    interval: TimeInterval
    epistemic: EpistemicLabel
    influence: InfluenceClass
    evidence_ids: tuple[str, ...]
    observation: ObservationStatus
    disposition: DischargeDisposition
    discharge_rule_id: str

    def __post_init__(self) -> None:
        _require_enum("edge_type", self.edge_type, InfluenceEdgeType)
        _require_enum("epistemic", self.epistemic, EpistemicLabel)
        _require_enum("influence", self.influence, InfluenceClass)
        _require_enum("observation", self.observation, ObservationStatus)
        _require_enum("disposition", self.disposition, DischargeDisposition)
        _normalize_tuple_fields(self, ("evidence_ids",))
        _unique("evidence_ids", self.evidence_ids)


@dataclass(frozen=True, slots=True)
class InfluenceState:
    nodes: tuple[InfluenceNode, ...]
    edges: tuple[InfluenceEdge, ...]

    def __post_init__(self) -> None:
        _normalize_tuple_fields(self, ("nodes", "edges"))
        _unique("nodes", self.nodes, lambda item: item.node_id)
        _unique("edges", self.edges, lambda item: item.edge_id)
        if len(self.nodes) != 31:
            raise FormalValidationError("critical influence inventory must contain 31 nodes")
        by_id = {node.node_id: node for node in self.nodes}
        for edge in self.edges:
            if edge.src not in by_id or edge.dst not in by_id:
                raise FormalValidationError("influence edge references an unknown node")
            if edge.disposition is DischargeDisposition.EXPLICIT_RESIDUAL_ASSUMPTION:
                if not by_id[edge.src].residual_assumption_allowed or not by_id[edge.dst].residual_assumption_allowed:
                    raise FormalValidationError("residual assumption is forbidden on a critical role")


@dataclass(frozen=True, slots=True)
class CertificateProposal:
    certificate_id: str
    target_domain: AuthorityDomain
    certificate_hash: str

    def __post_init__(self) -> None:
        _require_enum("target_domain", self.target_domain, AuthorityDomain)
        if self.target_domain is AuthorityDomain.OLD:
            raise FormalValidationError("certificate target must be a proposed new domain")
        _hex_digest("certificate_hash", self.certificate_hash)


@dataclass(frozen=True, slots=True)
class ConstructorReplica:
    replica_id: str


@dataclass(frozen=True, slots=True)
class ConstructorVote:
    replica_id: str
    cutover_slot_id: str
    proposal_hash: str

    def __post_init__(self) -> None:
        _hex_digest("proposal_hash", self.proposal_hash)


@dataclass(frozen=True, slots=True)
class RootRecord:
    state: RootRecordState
    root_id: str | None = None
    certificate_hash: str | None = None
    domain: AuthorityDomain | None = None
    generation: Generation | None = None

    def __post_init__(self) -> None:
        _require_enum("state", self.state, RootRecordState)
        optional = (self.root_id, self.certificate_hash, self.domain, self.generation)
        if self.state is RootRecordState.NONE:
            if any(item is not None for item in optional):
                raise FormalValidationError("NONE root record cannot contain root material")
            return
        if any(item is None for item in optional):
            raise FormalValidationError(f"root {self.state.value} requires root ID, certificate hash, domain, generation")
        _require_enum("domain", self.domain, AuthorityDomain)
        _require_enum("generation", self.generation, Generation)
        if self.domain is AuthorityDomain.OLD or self.generation is not Generation.NEXT:
            raise FormalValidationError("prepared/committed root must target a new domain at g+1")
        _hex_digest("certificate_hash", self.certificate_hash or "")


@dataclass(frozen=True, slots=True)
class EpochRegistryEntry:
    domain: AuthorityDomain
    generation: Generation
    active: bool

    def __post_init__(self) -> None:
        _require_enum("domain", self.domain, AuthorityDomain)
        _require_enum("generation", self.generation, Generation)
        if not isinstance(self.active, bool):
            raise FormalValidationError("epoch registry active flag must be boolean")


@dataclass(frozen=True, slots=True)
class ScopeOwnership:
    scope_id: str
    owner: ScopeOwner

    def __post_init__(self) -> None:
        _require_enum("owner", self.owner, ScopeOwner)


@dataclass(frozen=True, slots=True)
class CutoverState:
    old_domain: AuthorityDomain
    proposed_new_domains: tuple[AuthorityDomain, ...]
    certificates: tuple[CertificateProposal, ...]
    protected_scopes: tuple[str, ...]
    cutover_slot_id: str
    cutover_slot_state: CutoverSlotState
    replicas: tuple[ConstructorReplica, ...]
    votes: tuple[ConstructorVote, ...]
    quorum_threshold: int
    quorum_denominator: int
    phase: CutoverPhase
    root_record: RootRecord
    epoch_registry: tuple[EpochRegistryEntry, ...]
    scope_ownership: tuple[ScopeOwnership, ...]

    def __post_init__(self) -> None:
        _require_enum("old_domain", self.old_domain, AuthorityDomain)
        _require_enum("cutover_slot_state", self.cutover_slot_state, CutoverSlotState)
        _require_enum("phase", self.phase, CutoverPhase)
        _normalize_tuple_fields(self, ("proposed_new_domains", "certificates", "protected_scopes", "replicas", "votes", "epoch_registry", "scope_ownership"))
        if self.old_domain is not AuthorityDomain.OLD:
            raise FormalValidationError("old authority domain must be D_o")
        if self.proposed_new_domains != (AuthorityDomain.NEW_1, AuthorityDomain.NEW_2):
            raise FormalValidationError("candidate new domains must be exactly D_1,D_2")
        if tuple(item.certificate_id for item in self.certificates) != ("Cert_R1", "Cert_R2"):
            raise FormalValidationError("certificates must be exactly Cert_R1,Cert_R2")
        if self.protected_scopes != ("s*", "s_2"):
            raise FormalValidationError("protected scopes must be exactly s*,s_2")
        if tuple(item.replica_id for item in self.replicas) != ("Q1", "Q2"):
            raise FormalValidationError("constructor replicas must be exactly Q1,Q2")
        if (self.quorum_threshold, self.quorum_denominator) != (2, 2):
            raise FormalValidationError("constructor safety quorum must remain 2/2")
        _unique("votes", self.votes, lambda item: item.replica_id)
        _unique("epoch_registry", self.epoch_registry, lambda item: (item.domain, item.generation))
        if {item.scope_id for item in self.scope_ownership} != {"s*", "s_2"}:
            raise FormalValidationError("scope ownership must explicitly cover both protected scopes")
        if self.phase is CutoverPhase.COMMITTED:
            if self.root_record.state is not RootRecordState.COMMITTED or self.cutover_slot_state is not CutoverSlotState.COMMITTED:
                raise FormalValidationError("COMMITTED phase requires committed root and cutover slot")
        if self.phase is CutoverPhase.ROOT_PREPARED and self.root_record.state is not RootRecordState.PREPARED:
            raise FormalValidationError("ROOT_PREPARED phase requires prepared root material")


@dataclass(frozen=True, slots=True)
class RecoveryAttempt:
    attempt_id: str
    certificate_id: str


@dataclass(frozen=True, slots=True)
class ExternalAdapter:
    adapter_id: str
    adapter_class: ExternalAdapterClass
    idempotency_key: str | None = None
    escrow_transaction_id: str | None = None
    fence_generation: Generation | None = None

    def __post_init__(self) -> None:
        _require_enum("adapter_class", self.adapter_class, ExternalAdapterClass)
        if self.adapter_class is ExternalAdapterClass.IDEMPOTENT:
            if self.idempotency_key is None or self.escrow_transaction_id is not None or self.fence_generation is not None:
                raise FormalValidationError("IDEMPOTENT adapter requires only idempotency_key")
        elif self.adapter_class is ExternalAdapterClass.ESCROWED:
            if self.escrow_transaction_id is None or self.idempotency_key is not None or self.fence_generation is not None:
                raise FormalValidationError("ESCROWED adapter requires only escrow_transaction_id")
        elif self.adapter_class is ExternalAdapterClass.FENCED:
            if self.fence_generation is None or self.idempotency_key is not None or self.escrow_transaction_id is not None:
                raise FormalValidationError("FENCED adapter requires only fence_generation")
        elif any(item is not None for item in (self.idempotency_key, self.escrow_transaction_id, self.fence_generation)):
            raise FormalValidationError("UNOBSERVABLE adapter has no finality parameter")


@dataclass(frozen=True, slots=True)
class RecoverySlot:
    recovery_slot_id: str
    checkpoint_id: str
    scope_id: str
    state: RecoverySlotState
    intent_hash: str | None = None
    output_set_id: str | None = None
    receipt_id: str | None = None
    hold_reason: str | None = None

    def __post_init__(self) -> None:
        _require_enum("state", self.state, RecoverySlotState)
        if self.checkpoint_id != "cp*" or self.scope_id not in ("s*", "s_2"):
            raise FormalValidationError("invalid checkpoint or protected scope")
        if self.state is RecoverySlotState.UNUSED:
            if any(item is not None for item in (self.intent_hash, self.output_set_id, self.receipt_id, self.hold_reason)):
                raise FormalValidationError("UNUSED recovery slot cannot contain outcome material")
        elif self.state is RecoverySlotState.PREPARED:
            if self.intent_hash is None or any(item is not None for item in (self.output_set_id, self.receipt_id, self.hold_reason)):
                raise FormalValidationError("PREPARED recovery slot requires only intent_hash")
            _hex_digest("intent_hash", self.intent_hash)
        elif self.state is RecoverySlotState.COMMITTED:
            if self.output_set_id is None or self.receipt_id is None or self.hold_reason is not None:
                raise FormalValidationError("recovery COMMITTED requires output_set_id and receipt_id")
        elif self.hold_reason is None or any(item is not None for item in (self.output_set_id, self.receipt_id)):
            raise FormalValidationError("RECOVERY_HOLD requires an explicit reason and no committed output")


@dataclass(frozen=True, slots=True)
class RecoveryState:
    checkpoints: tuple[str, ...]
    protected_scopes: tuple[str, ...]
    recovery_slot_service_id: str
    recovery_clients: tuple[str, ...]
    attempts: tuple[RecoveryAttempt, ...]
    slots: tuple[RecoverySlot, ...]
    adapters: tuple[ExternalAdapter, ...]
    settlement_fence_state: SettlementFenceState

    def __post_init__(self) -> None:
        _require_enum("settlement_fence_state", self.settlement_fence_state, SettlementFenceState)
        _normalize_tuple_fields(self, ("checkpoints", "protected_scopes", "recovery_clients", "attempts", "slots", "adapters"))
        if self.checkpoints != ("cp*",) or self.protected_scopes != ("s*", "s_2"):
            raise FormalValidationError("checkpoint/scope universe changed")
        if self.recovery_slot_service_id != "RecoverySlotService_1":
            raise FormalValidationError("reference model has exactly one recovery-slot service")
        if self.recovery_clients != ("RecoveryClient_1", "RecoveryClient_2"):
            raise FormalValidationError("recovery clients must be the two frozen failover clients")
        if tuple(item.attempt_id for item in self.attempts) != ("RecoveryAttempt_1", "RecoveryAttempt_2"):
            raise FormalValidationError("recovery attempts must be exactly two")
        if {item.adapter_class for item in self.adapters} != set(ExternalAdapterClass):
            raise FormalValidationError("all four adapter classes must be represented")
        _unique("slots", self.slots, lambda item: item.recovery_slot_id)
        _unique("adapters", self.adapters, lambda item: item.adapter_id)


@dataclass(frozen=True, slots=True)
class AuthorityDomainEntry:
    domain: AuthorityDomain
    generation: Generation
    proposed: bool

    def __post_init__(self) -> None:
        _require_enum("domain", self.domain, AuthorityDomain)
        _require_enum("generation", self.generation, Generation)
        if not isinstance(self.proposed, bool):
            raise FormalValidationError("domain proposed flag must be boolean")


@dataclass(frozen=True, slots=True)
class FormalConfiguration:
    schema_version: str
    manifest_version: str
    sterile_schema_id: str
    bounds: FormalBounds

    def __post_init__(self) -> None:
        if (self.schema_version, self.manifest_version, self.sterile_schema_id) != (FORMAL_SCHEMA_VERSION, MANIFEST_VERSION, STERILE_SCHEMA_ID):
            raise FormalValidationError("formal configuration version mismatch")


@dataclass(frozen=True, slots=True)
class NLCFormalState:
    configuration: FormalConfiguration
    sterility: SterilityState
    influence: InfluenceState
    cutover: CutoverState
    recovery: RecoveryState
    authority_domain_registry: tuple[AuthorityDomainEntry, ...]
    logical_clock: int
    future_trace_bound: int

    def __post_init__(self) -> None:
        _normalize_tuple_fields(self, ("authority_domain_registry",))
        if {item.domain for item in self.authority_domain_registry} != set(AuthorityDomain):
            raise FormalValidationError("authority domain registry must contain D_o,D_1,D_2")
        if isinstance(self.logical_clock, bool) or not 0 <= self.logical_clock <= 40:
            raise FormalValidationError("logical clock is outside bounded execution domain")
        if self.future_trace_bound != 40 or self.configuration.bounds.trace_bound != 40:
            raise FormalValidationError("future trace bound must remain L=40")
