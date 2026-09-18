"""Canonical certificate builder.

This module deliberately contains no RootAccept decision function.  It only
normalizes unordered construction material and emits canonical M1 JSON bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping, Sequence

from m1.canonical import canonical_bytes


CERTIFICATE_VERSION = "NLC-RECONSTITUTION-CERTIFICATE/1.0"
CERTIFICATE_HASH_TAG = b"NLC-RECONSTITUTION-CERTIFICATE-v1\x00"


@dataclass(frozen=True)
class ReconstitutionCertificate:
    candidate_identity: str
    target_domain: str
    target_epoch: int
    nonce: str
    sterility_evidence: Mapping[str, Any]
    aim_exclusion_evidence: Mapping[str, Any]
    functional_witness: Mapping[str, Any]
    barrier_versions: Mapping[str, str]
    threshold_constructor_set: Sequence[str]
    certificate_version: str = CERTIFICATE_VERSION


def certificate_material(value: ReconstitutionCertificate) -> dict[str, Any]:
    """Return the closed canonical material; no field is defaulted or inferred."""
    return {
        "aim_exclusion_evidence": dict(value.aim_exclusion_evidence),
        "barrier_versions": dict(value.barrier_versions),
        "candidate_identity": value.candidate_identity,
        "certificate_version": value.certificate_version,
        "functional_witness": dict(value.functional_witness),
        "nonce": value.nonce,
        "sterility_evidence": dict(value.sterility_evidence),
        "target_domain": value.target_domain,
        "target_epoch": value.target_epoch,
        "threshold_constructor_set": sorted(value.threshold_constructor_set),
    }


def build_certificate(value: ReconstitutionCertificate) -> bytes:
    return canonical_bytes(certificate_material(value))


def certificate_id(raw: bytes) -> str:
    return hashlib.sha256(CERTIFICATE_HASH_TAG + raw).hexdigest()
