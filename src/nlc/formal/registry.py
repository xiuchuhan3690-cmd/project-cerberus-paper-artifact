"""Frozen NLC-FR1 inventories and cardinality registry."""

from __future__ import annotations

from .model import (
    AdmissibleType,
    AdmissionDecision,
    AuthorityPotential,
    AuthorityRelevance,
    AuthorityTerminalPredicate,
    ExternalAdapterClass,
    ForbiddenType,
    FormalBounds,
    InfluenceNode,
    OpaqueType,
    TransformSpec,
    TypeClass,
    TypeSpec,
)


AUTHORITY_DOMAINS = ("D_o", "D_1", "D_2")
CANDIDATE_NEW_DOMAINS = ("D_1", "D_2")
PROTECTED_SCOPES = ("s*", "s_2")
CERTIFICATES = ("Cert_R1", "Cert_R2")
GENERATIONS = ("g", "g+1")
CHECKPOINTS = ("cp*",)
RECOVERY_ATTEMPTS = ("RecoveryAttempt_1", "RecoveryAttempt_2")
CONSTRUCTOR_REPLICAS = ("Q1", "Q2")
RECOVERY_CLIENTS = ("RecoveryClient_1", "RecoveryClient_2")


ADMISSIBLE_TYPE_SPECS = (
    TypeSpec(AdmissibleType.BOUNDED_INT, "signed integer closed interval declared per field", "no textual normalization"),
    TypeSpec(AdmissibleType.BOOL, "{false,true}", "JSON boolean"),
    TypeSpec(AdmissibleType.ENUM, "finite declared symbol set", "exact case-sensitive symbol"),
    TypeSpec(AdmissibleType.NORMALIZED_STRING, "declared maximum length and alphabet", "Unicode NFC; explicit alphabet rule reference"),
    TypeSpec(AdmissibleType.BOUNDED_TIMESTAMP, "integer closed interval [0,40] in reference state", "integer logical time"),
    TypeSpec(AdmissibleType.BUSINESS_ID, "finite declared kind and bounded value", "new-domain-only namespace"),
    TypeSpec(AdmissibleType.IMMUTABLE_AGGREGATE, "fixed component schema", "canonical component tuple"),
    TypeSpec(AdmissibleType.TERMINAL_BUSINESS_FACT, "finite kind; terminal state only", "canonical fixed fields"),
    TypeSpec(AdmissibleType.CHECKPOINT_FACT, "finite inert checkpoint kind", "canonical fixed fields"),
    TypeSpec(AdmissibleType.INERT_PROVENANCE_REF, "finite evidence ID and SHA-256 digest", "EVIDENCE_ONLY tagged reference"),
)


TRANSFORM_SPECS = (
    TransformSpec("id", TypeClass.ANY_MODELED, TypeClass.ANY_MODELED, True, False, AuthorityRelevance.POTENTIAL, True),
    TransformSpec("field_i", TypeClass.ANY_MODELED, TypeClass.ANY_MODELED, True, True, AuthorityRelevance.POTENTIAL, True),
    TransformSpec("unwrap_j", TypeClass.ANY_MODELED, TypeClass.ANY_MODELED, True, True, AuthorityRelevance.POTENTIAL, True),
    TransformSpec("decode_B16", TypeClass.OPAQUE_QUARANTINED, TypeClass.ANY_MODELED, True, True, AuthorityRelevance.POTENTIAL, True),
    TransformSpec("decode_B32", TypeClass.OPAQUE_QUARANTINED, TypeClass.ANY_MODELED, True, True, AuthorityRelevance.POTENTIAL, True),
    TransformSpec("decode_B64", TypeClass.OPAQUE_QUARANTINED, TypeClass.ANY_MODELED, True, True, AuthorityRelevance.POTENTIAL, True),
    TransformSpec("typed_deser_t", TypeClass.OPAQUE_QUARANTINED, TypeClass.AUTHORITY_BEARING, True, True, AuthorityRelevance.TERMINAL, True),
    TransformSpec("resolve_ref", TypeClass.ANY_MODELED, TypeClass.ANY_MODELED, True, True, AuthorityRelevance.POTENTIAL, True),
    TransformSpec("decrypt_key_q", TypeClass.OPAQUE_QUARANTINED, TypeClass.ANY_MODELED, True, True, AuthorityRelevance.POTENTIAL, True),
    TransformSpec("refresh", TypeClass.AUTHORITY_BEARING, TypeClass.AUTHORITY_BEARING, True, True, AuthorityRelevance.TERMINAL, True),
    TransformSpec("delegate", TypeClass.AUTHORITY_BEARING, TypeClass.AUTHORITY_BEARING, True, True, AuthorityRelevance.TERMINAL, True),
    TransformSpec("retry_continue", TypeClass.AUTHORITY_BEARING, TypeClass.AUTHORITY_BEARING, True, True, AuthorityRelevance.TERMINAL, True),
    TransformSpec("recovery_authorize", TypeClass.AUTHORITY_BEARING, TypeClass.AUTHORITY_BEARING, True, True, AuthorityRelevance.TERMINAL, True),
    TransformSpec("parent_materialize", TypeClass.AUTHORITY_BEARING, TypeClass.AUTHORITY_BEARING, True, True, AuthorityRelevance.TERMINAL, True),
)


_NODE_CATEGORIES = {
    "Identity/Authority": ("IdentityRoot_o", "RootConstructor_Q1", "RootConstructor_Q2", "CapabilityConstructor_o", "VerifierKeys_o", "VerifierKeys_n"),
    "Runtime": ("Service_o", "Service_n", "WorkloadRuntime_n", "Orchestrator_n"),
    "State": ("AuthoritativeDB_o", "StateCommit_n", "CheckpointStore", "RecoverySlotLedger"),
    "Build": ("Compiler_n", "BuildSystem_n", "ArtifactOrigin_n", "DependencySource_n"),
    "Administrative": ("Admin_o", "Admin_n", "Automation_n", "RecoveryOperator"),
    "Infrastructure": ("KMS_o", "KMS_n", "CloudControl_n", "ClusterControl_n", "SecretStore_n"),
    "Provenance": ("EvidenceSigner", "LedgerRoot", "WitnessA", "WitnessB"),
}


CRITICAL_INFLUENCE_NODES = tuple(
    InfluenceNode(node_id, category, node_id in {"WitnessA", "WitnessB"})
    for category, node_ids in _NODE_CATEGORIES.items()
    for node_id in node_ids
)


def domain_manifest() -> dict[str, object]:
    """Machine-readable frozen domain manifest (not a formal state identity)."""
    bounds = FormalBounds()
    return {
        "manifest_version": "NLC-FORMAL-DOMAINS/1.0",
        "formal_state_schema": "NLC-FORMAL-STATE/1.0",
        "sterile_schema_id": "NLC-STERILE-REF/0.1",
        "authority_domains": list(AUTHORITY_DOMAINS),
        "candidate_new_domains": list(CANDIDATE_NEW_DOMAINS),
        "protected_scopes": list(PROTECTED_SCOPES),
        "certificates": list(CERTIFICATES),
        "generations": list(GENERATIONS),
        "checkpoints": list(CHECKPOINTS),
        "recovery_attempts": list(RECOVERY_ATTEMPTS),
        "constructor_replicas": list(CONSTRUCTOR_REPLICAS),
        "recovery_clients": list(RECOVERY_CLIENTS),
        "cardinality": {field: getattr(bounds, field) for field in bounds.__dataclass_fields__},
        "admissible_types": [item.value for item in AdmissibleType],
        "forbidden_types": [item.value for item in ForbiddenType],
        "opaque_types": [item.value for item in OpaqueType],
        "decisions": [item.value for item in AdmissionDecision],
        "authority_potential_states": [item.value for item in AuthorityPotential],
        "authority_terminal_predicates": [item.value for item in AuthorityTerminalPredicate],
        "transforms": [
            {
                "transform_id": item.transform_id,
                "input_type_class": item.input_type_class.value,
                "output_type_class": item.output_type_class.value,
                "deterministic": item.deterministic,
                "partial": item.partial,
                "authority_relevance": item.authority_relevance.value,
                "enabled_in_reference_model": item.enabled_in_reference_model,
            }
            for item in TRANSFORM_SPECS
        ],
        "critical_influence_nodes": [
            {"node_id": node.node_id, "category": node.category, "residual_assumption_allowed": node.residual_assumption_allowed}
            for node in CRITICAL_INFLUENCE_NODES
        ],
        "adapter_classes": [item.value for item in ExternalAdapterClass],
        "unknown_default_policy": "REJECT_MISSING_OR_UNKNOWN; NEVER_DEFAULT_TO_CLEAN_SAFE_SUCCESS_ACTIVE_OR_ADMIT",
    }

