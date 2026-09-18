"""Independent RootAccept verifier for Reconstitution_Certificate_v1.

The verifier imports neither the builder nor any proposer acceptance rule.  It
parses duplicate-preserving JSON itself, applies a closed field table, recreates
canonical bytes, hashes both frozen parent artifacts, and replays the bounded
functional witness contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping


CERTIFICATE_VERSION = "NLC-RECONSTITUTION-CERTIFICATE/1.0"
PREDICATE_VERSION = "NLC-ROOT-ACCEPT-VERIFIER/1.0"
CERTIFICATE_HASH_TAG = b"NLC-RECONSTITUTION-CERTIFICATE-v1\x00"
FUNCTION_TAG = b"NLC-M5-T1-FUNCTION-v1\x00"
FROZEN_M3_HEAD = "c8dedc7f03c2e9c3607737b66f971a69ff768c23"
FROZEN_M4_HEAD = "7d48a30863bc9fb3097e70ae9c348ef21f6acfcf"
FROZEN_M3_PATH = "artifacts/NLC_M3_Sterility_Artifact_for_M5_v1.json"
FROZEN_M4_PATH = "manifests/AIM_Freeze_Record_v1.json"
FROZEN_BARRIERS = {
    "namespace": "NLC-NAMESPACE-BARRIER/1.0",
    "verifier_domain": "NLC-VERIFIER-DOMAIN-BARRIER/1.0",
    "cryptographic_root": "NLC-CRYPTOGRAPHIC-ROOT-BARRIER/1.0",
    "semantic_grammar": "NLC-SEMANTIC-GRAMMAR-BARRIER/1.0",
    "protocol_adapter": "NLC-PROTOCOL-ADAPTER-BARRIER/1.0",
}
FROZEN_CONSTRUCTORS = ("RootConstructor_Q1", "RootConstructor_Q2")
FROZEN_FUNCTION_INPUTS = (
    ("FW-1", {"operation": "read", "record": "synthetic:alpha"}),
    ("FW-2", {"operation": "transform", "record": "synthetic:beta", "value": 7}),
    ("FW-3", {"operation": "status", "record": "synthetic:gamma", "terminal": True}),
)

CERTIFICATE_FIELDS = {
    "aim_exclusion_evidence", "barrier_versions", "candidate_identity",
    "certificate_version", "functional_witness", "nonce",
    "sterility_evidence", "target_domain", "target_epoch",
    "threshold_constructor_set",
}
STERILITY_FIELDS = {
    "artifact_commit", "artifact_path", "artifact_sha256", "artifact_version",
    "eligibility", "proof_commitment",
}
AIM_FIELDS = {
    "artifact_commit", "artifact_path", "artifact_sha256", "artifact_version",
    "candidate_identity", "eligibility", "fixture_id", "report_commitment",
    "rule_set_version",
}
WITNESS_FIELDS = {
    "candidate_identity", "cases", "target_domain", "witness_version",
    "workload_id",
}
BARRIER_FIELDS = {
    "cryptographic_root", "namespace", "protocol_adapter", "semantic_grammar",
    "verifier_domain",
}
PROHIBITED_AUTHORITY_TOKENS = (
    "old_authority", "old_root", "old_key", "cross_signature", "cross-signature",
    "cross_sign", "wrapped_old", "delegation", "authorization_source",
    "authority_parent", "parent_authority", "old_domain_signature",
    "old_domain_derivation", "old_key_wrap", "old_authority_delegation",
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ATOM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}$")
NONCE = re.compile(r"^nonce:[A-Za-z0-9._-]{8,96}$")


@dataclass(frozen=True)
class RootAcceptContext:
    target_domain: str
    target_epoch: int
    barrier_versions: Mapping[str, str]
    threshold_constructor_set: tuple[str, ...]
    used_nonces: frozenset[str]
    m3_head: str
    m3_artifact_path: str
    m3_artifact_bytes: bytes
    m4_head: str
    m4_artifact_path: str
    m4_artifact_bytes: bytes


@dataclass(frozen=True)
class VerificationResult:
    verdict: str
    reason_code: str
    certificate_id: str | None
    predicate_version: str = PREDICATE_VERSION


class _Reject(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _Reject("DUPLICATE_FIELD")
        result[key] = value
    return result


def _bad_number(_value):
    raise _Reject("MALFORMED_CANONICAL_VALUE")


def _parse(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs,
            parse_float=_bad_number, parse_constant=_bad_number,
        )
    except _Reject:
        raise
    except (UnicodeError, json.JSONDecodeError):
        raise _Reject("MALFORMED_CERTIFICATE") from None
    if not isinstance(value, dict):
        raise _Reject("MALFORMED_CERTIFICATE")
    return value


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, float):
        raise _Reject("MALFORMED_CANONICAL_VALUE")
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if not -(2**63) <= value <= 2**63 - 1:
            raise _Reject("MALFORMED_CANONICAL_VALUE")
        return value
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise _Reject("MALFORMED_CANONICAL_VALUE")
            key = unicodedata.normalize("NFC", key)
            if key in normalized:
                raise _Reject("DUPLICATE_FIELD")
            normalized[key] = _normalize(item)
        return normalized
    raise _Reject("MALFORMED_CANONICAL_VALUE")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        _normalize(value), ensure_ascii=False, allow_nan=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _exact(value: Any, fields: set[str], missing_code: str, malformed_code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _Reject(malformed_code)
    missing = fields - set(value)
    if missing:
        raise _Reject(missing_code)
    if set(value) != fields:
        raise _Reject(malformed_code)
    return value


def _contains_prohibited(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            folded = key.lower().replace("-", "_")
            if any(token.replace("-", "_") in folded for token in PROHIBITED_AUTHORITY_TOKENS):
                return True
            if _contains_prohibited(item):
                return True
    elif isinstance(value, list):
        return any(_contains_prohibited(item) for item in value)
    elif isinstance(value, str):
        folded = value.lower().replace("-", "_")
        return any(token.replace("-", "_") in folded for token in PROHIBITED_AUTHORITY_TOKENS)
    return False


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _artifact_object(raw: bytes, code: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise _Reject(code) from None
    if not isinstance(value, dict):
        raise _Reject(code)
    return value


def _verify_sterility(cert: dict[str, Any], context: RootAcceptContext) -> None:
    value = _exact(cert.get("sterility_evidence"), STERILITY_FIELDS, "STERILITY_EVIDENCE_MISSING", "STERILITY_EVIDENCE_MALFORMED")
    if context.m3_head != FROZEN_M3_HEAD or context.m3_artifact_path != FROZEN_M3_PATH:
        raise _Reject("STERILITY_EVIDENCE_REFERENCE_MISMATCH")
    if value["artifact_commit"] != context.m3_head or value["artifact_path"] != context.m3_artifact_path:
        raise _Reject("STERILITY_EVIDENCE_REFERENCE_MISMATCH")
    actual = _sha(context.m3_artifact_bytes)
    if value["artifact_sha256"] != actual or value["proof_commitment"] != actual:
        raise _Reject("STERILITY_COMMITMENT_MISMATCH")
    artifact = _artifact_object(context.m3_artifact_bytes, "STERILITY_ARTIFACT_MALFORMED")
    if value["artifact_version"] != artifact.get("artifact_version"):
        raise _Reject("STERILITY_VERSION_INELIGIBLE")
    if value["eligibility"] != "STERILITY_ARTIFACT_FOR_M5_FROZEN" or artifact.get("status") != value["eligibility"]:
        raise _Reject("STERILITY_NOT_ELIGIBLE")
    if artifact.get("false_admit", {}).get("count") != 0 or artifact.get("producer_verifier_divergence") != 0:
        raise _Reject("STERILITY_NOT_ELIGIBLE")


def _verify_aim(cert: dict[str, Any], context: RootAcceptContext) -> None:
    value = _exact(cert.get("aim_exclusion_evidence"), AIM_FIELDS, "AIM_EVIDENCE_MISSING", "AIM_EVIDENCE_MALFORMED")
    if context.m4_head != FROZEN_M4_HEAD or context.m4_artifact_path != FROZEN_M4_PATH:
        raise _Reject("AIM_EVIDENCE_REFERENCE_MISMATCH")
    if value["artifact_commit"] != context.m4_head or value["artifact_path"] != context.m4_artifact_path:
        raise _Reject("AIM_EVIDENCE_REFERENCE_MISMATCH")
    if value["artifact_sha256"] != _sha(context.m4_artifact_bytes):
        raise _Reject("AIM_COMMITMENT_MISMATCH")
    artifact = _artifact_object(context.m4_artifact_bytes, "AIM_ARTIFACT_MALFORMED")
    if artifact.get("artifact_version") != value["artifact_version"] or artifact.get("rule_set_version") != value["rule_set_version"]:
        raise _Reject("AIM_VERSION_INELIGIBLE")
    if artifact.get("independent_verification") != "PASS":
        raise _Reject("AIM_NOT_ELIGIBLE")
    rows = [row for row in artifact.get("candidate_results", []) if row.get("fixture_id") == value["fixture_id"]]
    if len(rows) != 1 or rows[0].get("verification_digest") != value["report_commitment"]:
        raise _Reject("AIM_REPORT_COMMITMENT_MISMATCH")
    candidates = [row for row in rows[0].get("candidates", []) if row.get("candidate_id") == value["candidate_identity"]]
    if len(candidates) != 1 or candidates[0].get("eligibility") != value["eligibility"] or value["eligibility"] != "ELIGIBLE":
        raise _Reject("AIM_CANDIDATE_INELIGIBLE")
    if value["candidate_identity"] != cert["candidate_identity"]:
        raise _Reject("CANDIDATE_IDENTITY_MISMATCH")


def _case_output(case_input: Any) -> str:
    return _sha(FUNCTION_TAG + _canonical(case_input))


def _verify_witness(cert: dict[str, Any]) -> None:
    value = _exact(cert.get("functional_witness"), WITNESS_FIELDS, "FUNCTIONAL_WITNESS_MISSING", "FUNCTIONAL_WITNESS_MALFORMED")
    if value["witness_version"] != "NLC-M5-T1-FUNCTIONAL-WITNESS/1.0" or value["workload_id"] != "NLC-FINITE-SYNTHETIC-WORKLOAD/1.0":
        raise _Reject("FUNCTIONAL_WITNESS_UNSUPPORTED")
    if value["candidate_identity"] != cert["candidate_identity"] or value["target_domain"] != cert["target_domain"]:
        raise _Reject("FUNCTIONAL_WITNESS_BINDING_MISMATCH")
    cases = value["cases"]
    if not isinstance(cases, list) or len(cases) != len(FROZEN_FUNCTION_INPUTS):
        raise _Reject("FUNCTIONAL_WITNESS_MALFORMED")
    seen = set()
    for case, (expected_id, expected_input) in zip(cases, FROZEN_FUNCTION_INPUTS):
        if not isinstance(case, dict) or set(case) != {"case_id", "input", "observed_output"}:
            raise _Reject("FUNCTIONAL_WITNESS_MALFORMED")
        if not isinstance(case["case_id"], str) or case["case_id"] in seen:
            raise _Reject("FUNCTIONAL_WITNESS_MALFORMED")
        seen.add(case["case_id"])
        if case["case_id"] != expected_id or case["input"] != expected_input:
            raise _Reject("FUNCTIONAL_WITNESS_UNSUPPORTED")
        if case["observed_output"] != _case_output(case["input"]):
            raise _Reject("FUNCTIONAL_WITNESS_FORGED")


def _verify_bindings(cert: dict[str, Any], context: RootAcceptContext) -> None:
    for name in ("candidate_identity", "target_domain", "nonce"):
        if not isinstance(cert[name], str) or not ATOM.fullmatch(cert[name]):
            raise _Reject("MALFORMED_CANONICAL_VALUE")
    if cert["target_domain"] != context.target_domain:
        raise _Reject("TARGET_DOMAIN_MISMATCH")
    if isinstance(cert["target_epoch"], bool) or not isinstance(cert["target_epoch"], int) or cert["target_epoch"] < 0:
        raise _Reject("TARGET_EPOCH_MALFORMED")
    if cert["target_epoch"] != context.target_epoch:
        raise _Reject("TARGET_EPOCH_MISMATCH")
    if not NONCE.fullmatch(cert["nonce"]):
        raise _Reject("NONCE_INVALID")
    if cert["nonce"] in context.used_nonces:
        raise _Reject("NONCE_REPLAYED")
    barriers = _exact(cert["barrier_versions"], BARRIER_FIELDS, "BARRIER_VERSION_MISSING", "BARRIER_VERSION_MALFORMED")
    if dict(context.barrier_versions) != FROZEN_BARRIERS or barriers != FROZEN_BARRIERS:
        raise _Reject("BARRIER_VERSION_MISMATCH")
    constructors = cert["threshold_constructor_set"]
    if not isinstance(constructors, list) or any(not isinstance(item, str) for item in constructors):
        raise _Reject("CONSTRUCTOR_SET_MALFORMED")
    if constructors != sorted(constructors) or len(constructors) != len(set(constructors)):
        raise _Reject("CONSTRUCTOR_SET_MALFORMED")
    if tuple(sorted(context.threshold_constructor_set)) != FROZEN_CONSTRUCTORS or tuple(constructors) != FROZEN_CONSTRUCTORS:
        raise _Reject("CONSTRUCTOR_SET_MISMATCH")


def verify_root_accept(raw: bytes, context: RootAcceptContext) -> VerificationResult:
    """Evaluate the frozen T1 pre-construction predicate; never mint/activate a root."""
    cert_id = None
    try:
        cert = _parse(raw)
        if _contains_prohibited(cert):
            raise _Reject("OLD_AUTHORITY_RELATION_PROHIBITED")
        missing = CERTIFICATE_FIELDS - set(cert)
        if missing:
            if "sterility_evidence" in missing:
                raise _Reject("STERILITY_EVIDENCE_MISSING")
            if "aim_exclusion_evidence" in missing:
                raise _Reject("AIM_EVIDENCE_MISSING")
            if "functional_witness" in missing:
                raise _Reject("FUNCTIONAL_WITNESS_MISSING")
            raise _Reject("REQUIRED_FIELD_MISSING")
        if set(cert) != CERTIFICATE_FIELDS:
            raise _Reject("UNKNOWN_FIELD")
        if cert.get("certificate_version") != CERTIFICATE_VERSION:
            raise _Reject("UNSUPPORTED_CERTIFICATE_VERSION")
        canonical = _canonical(cert)
        if canonical != raw:
            raise _Reject("NONCANONICAL_CERTIFICATE_BYTES")
        cert_id = _sha(CERTIFICATE_HASH_TAG + canonical)
        _verify_bindings(cert, context)
        _verify_sterility(cert, context)
        _verify_aim(cert, context)
        _verify_witness(cert)
        return VerificationResult("ACCEPT", "ROOT_ACCEPT", cert_id)
    except _Reject as exc:
        return VerificationResult("REJECT", exc.code, cert_id)
