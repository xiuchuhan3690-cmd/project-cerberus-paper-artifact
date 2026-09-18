"""M1 entity vocabulary and fail-closed record validation."""

from __future__ import annotations

import copy
import re
import uuid
from datetime import datetime
from typing import Any

from .canonical import CanonicalizationError, canonical_bytes, sha256_hex

SCHEMA_VERSION = "0.1"
MARKER = "CERBERUS_SYNTHETIC_TEST"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")
ID_PREFIXES = {
    "run": "cerb_run_",
    "session": "cerb_ses_",
    "generation": "cerb_gen_",
    "artifact": "cerb_art_",
    "issuance": "cerb_iss_",
    "event": "cerb_evt_",
    "derivation": "cerb_drv_",
}
ID_FIELDS = {
    "EXPERIMENT_RUN": ("run", "run_id"),
    "SESSION": ("session", "session_id"),
    "GENERATION": ("generation", "generation_id"),
    "ARTIFACT": ("artifact", "artifact_id"),
    "ISSUANCE": ("issuance", "issuance_id"),
    "EVENT": ("event", "event_id"),
    "DERIVATION": ("derivation", "derivation_id"),
}


class ProvenanceValidationError(ValueError):
    pass


def new_id(kind: str) -> str:
    try:
        prefix = ID_PREFIXES[kind]
    except KeyError as exc:
        raise ProvenanceValidationError(f"unknown id kind: {kind}") from exc
    return prefix + uuid.uuid4().hex


def validate_id(kind: str, value: Any) -> None:
    prefix = ID_PREFIXES.get(kind)
    if prefix is None:
        raise ProvenanceValidationError(f"unknown id kind: {kind}")
    if not isinstance(value, str) or not re.fullmatch(re.escape(prefix) + r"[0-9a-f]{32}", value):
        raise ProvenanceValidationError(f"invalid {kind} id")


def id_kind(value: Any) -> str:
    if not isinstance(value, str):
        raise ProvenanceValidationError("record id must be a string")
    matches = [kind for kind, prefix in ID_PREFIXES.items() if value.startswith(prefix)]
    if len(matches) != 1:
        raise ProvenanceValidationError("record id namespace is unknown or ambiguous")
    validate_id(matches[0], value)
    return matches[0]


def validate_timestamp(value: Any) -> None:
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise ProvenanceValidationError("timestamp must be UTC RFC3339 with six fractional digits")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as exc:
        raise ProvenanceValidationError("timestamp is not a real calendar instant") from exc


def record_id(record: dict[str, Any]) -> str:
    entity_type = record.get("entity_type")
    if entity_type not in ID_FIELDS:
        raise ProvenanceValidationError("unknown entity_type")
    kind, field = ID_FIELDS[entity_type]
    value = record.get(field)
    validate_id(kind, value)
    return value


def _require_exact(record: dict[str, Any], required: set[str]) -> None:
    missing = required - record.keys()
    extra = record.keys() - required
    if missing or extra:
        raise ProvenanceValidationError(f"record shape mismatch; missing={sorted(missing)}, extra={sorted(extra)}")


def issuance_payload_digest(record: dict[str, Any]) -> str:
    payload = copy.deepcopy(record)
    payload.pop("canonical_record_digest", None)
    return sha256_hex(canonical_bytes(payload))


def validate_record(record: Any) -> None:
    if not isinstance(record, dict):
        raise ProvenanceValidationError("record must be an object")
    try:
        canonical_bytes(record)
    except CanonicalizationError as exc:
        raise ProvenanceValidationError(str(exc)) from exc
    if record.get("schema_version") != SCHEMA_VERSION:
        raise ProvenanceValidationError("schema_version must be 0.1")
    if record.get("synthetic_test_marker") != MARKER:
        raise ProvenanceValidationError("synthetic marker is missing")
    entity_type = record.get("entity_type")
    record_type = record.get("record_type")
    identity = record_id(record)

    common = {"schema_version", "record_type", "entity_type", "synthetic_test_marker"}
    shapes = {
        "EXPERIMENT_RUN": common | {"run_id", "created_at", "owner_label", "authorization_scope_id", "policy_version", "experiment_manifest_digest"},
        "SESSION": common | {"session_id", "run_id", "created_at"},
        "GENERATION": common | {"generation_id", "session_id", "run_id", "created_at", "generator_label", "parameters_digest"},
        "ARTIFACT": common | {"artifact_id", "generation_id", "run_id", "created_at", "media_type", "placeholder_digest"},
        "ISSUANCE": common | {"issuance_id", "session_id", "generation_id", "artifact_id", "run_id", "issued_at", "policy_version", "canonical_record_digest"},
    }
    if entity_type in shapes:
        if record_type not in {"ENTITY", "ISSUANCE"}:
            raise ProvenanceValidationError("core entity has invalid record_type")
        if entity_type == "ISSUANCE" and record_type != "ISSUANCE":
            raise ProvenanceValidationError("issuance must use ISSUANCE record_type")
        if entity_type != "ISSUANCE" and record_type != "ENTITY":
            raise ProvenanceValidationError("non-issuance entity must use ENTITY record_type")
        _require_exact(record, shapes[entity_type])
    elif entity_type == "EVENT":
        if record_type == "OBSERVED_EVENT":
            _require_exact(record, common | {"event_id", "run_id", "event_type", "sensor_id", "occurred_at", "raw"})
        elif record_type == "UNOBSERVABLE":
            _require_exact(record, common | {"event_id", "run_id", "claim_type", "reason", "boundary"})
        else:
            raise ProvenanceValidationError("EVENT can only be OBSERVED_EVENT or UNOBSERVABLE")
    elif entity_type == "DERIVATION":
        if record_type == "DERIVED_FACT":
            _require_exact(record, common | {"derivation_id", "run_id", "supporting_record_ids", "derived_at", "method"})
        elif record_type == "INFERRED_RELATIONSHIP":
            _require_exact(record, common | {"derivation_id", "run_id", "supporting_record_ids", "proposed_at", "rationale", "confidence_micros"})
        else:
            raise ProvenanceValidationError("DERIVATION has invalid semantic record_type")
    else:
        raise ProvenanceValidationError("unknown entity_type")

    for field, kind in (("run_id", "run"), ("session_id", "session"), ("generation_id", "generation"), ("artifact_id", "artifact"), ("issuance_id", "issuance"), ("event_id", "event"), ("derivation_id", "derivation")):
        if field in record:
            validate_id(kind, record[field])
    for field in ("created_at", "issued_at", "occurred_at", "derived_at", "proposed_at"):
        if field in record:
            validate_timestamp(record[field])
    for field in ("experiment_manifest_digest", "parameters_digest", "placeholder_digest", "canonical_record_digest"):
        if field in record and (not isinstance(record[field], str) or not HEX64.fullmatch(record[field])):
            raise ProvenanceValidationError(f"{field} must be lowercase SHA-256 hex")
    for field in (
        "owner_label", "authorization_scope_id", "policy_version", "event_type", "sensor_id",
        "claim_type", "reason", "boundary", "method", "rationale",
    ):
        if field in record and (not isinstance(record[field], str) or not record[field]):
            raise ProvenanceValidationError(f"{field} must be a non-empty string")
    if "raw" in record and not isinstance(record["raw"], dict):
        raise ProvenanceValidationError("raw must be an object")
    if entity_type == "EXPERIMENT_RUN":
        if not re.fullmatch(r"synthetic-research-owner:[a-z0-9_-]+", record["owner_label"]):
            raise ProvenanceValidationError("owner_label must be synthetic")
        if not re.fullmatch(r"CERBERUS-M1-AUTH-[A-Z0-9_-]+", record["authorization_scope_id"]):
            raise ProvenanceValidationError("authorization scope is outside M1")
    if entity_type == "GENERATION" and record["generator_label"] != "SYNTHETIC_PLACEHOLDER_METADATA_ONLY":
        raise ProvenanceValidationError("M1 generation label is outside placeholder-only scope")
    if entity_type == "ARTIFACT" and record["media_type"] != "application/x-cerberus-placeholder":
        raise ProvenanceValidationError("M1 artifact must be placeholder metadata")
    if entity_type == "ISSUANCE" and record["canonical_record_digest"] != issuance_payload_digest(record):
        raise ProvenanceValidationError("issuance canonical_record_digest mismatch")
    if entity_type == "DERIVATION":
        supporting = record["supporting_record_ids"]
        if not isinstance(supporting, list) or not supporting or len(supporting) != len(set(supporting)):
            raise ProvenanceValidationError("supporting_record_ids must be a non-empty unique list")
        for value in supporting:
            id_kind(value)
        if "sensor_id" in record or "event_id" in record:
            raise ProvenanceValidationError("derived/inferred record cannot impersonate an observed event")
        if record_type == "INFERRED_RELATIONSHIP":
            confidence = record["confidence_micros"]
            if not isinstance(confidence, int) or isinstance(confidence, bool) or not 0 <= confidence <= 1_000_000:
                raise ProvenanceValidationError("confidence_micros must be an integer from 0 to 1000000")
    if not isinstance(identity, str):
        raise ProvenanceValidationError("identity is malformed")
