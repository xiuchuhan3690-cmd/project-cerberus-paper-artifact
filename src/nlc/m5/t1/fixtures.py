"""Frozen finite M5-T1 fixture construction from immutable Git objects."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from m1.canonical import canonical_bytes
from .builder import ReconstitutionCertificate
from .verifier import RootAcceptContext


M3_HEAD = "c8dedc7f03c2e9c3607737b66f971a69ff768c23"
M4_HEAD = "7d48a30863bc9fb3097e70ae9c348ef21f6acfcf"
M3_PATH = "artifacts/NLC_M3_Sterility_Artifact_for_M5_v1.json"
M4_PATH = "manifests/AIM_Freeze_Record_v1.json"
BARRIERS = {
    "namespace": "NLC-NAMESPACE-BARRIER/1.0",
    "verifier_domain": "NLC-VERIFIER-DOMAIN-BARRIER/1.0",
    "cryptographic_root": "NLC-CRYPTOGRAPHIC-ROOT-BARRIER/1.0",
    "semantic_grammar": "NLC-SEMANTIC-GRAMMAR-BARRIER/1.0",
    "protocol_adapter": "NLC-PROTOCOL-ADAPTER-BARRIER/1.0",
}
CONSTRUCTORS = ("RootConstructor_Q1", "RootConstructor_Q2")
FUNCTION_TAG = b"NLC-M5-T1-FUNCTION-v1\x00"


def git_blob(root: Path, commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=root, check=True,
        stdout=subprocess.PIPE,
    ).stdout


def baseline(root: Path) -> tuple[ReconstitutionCertificate, RootAcceptContext]:
    m3 = git_blob(root, M3_HEAD, M3_PATH)
    m4 = git_blob(root, M4_HEAD, M4_PATH)
    m3_obj = json.loads(m3)
    m4_obj = json.loads(m4)
    fixture = next(row for row in m4_obj["candidate_results"] if row["fixture_id"] == "T3-F26-INDEPENDENT-BUILD")
    inputs = [
        {"operation": "read", "record": "synthetic:alpha"},
        {"operation": "transform", "record": "synthetic:beta", "value": 7},
        {"operation": "status", "record": "synthetic:gamma", "terminal": True},
    ]
    witness = {
        "candidate_identity": "Service_n",
        "cases": [{
            "case_id": f"FW-{index + 1}", "input": item,
            "observed_output": hashlib.sha256(FUNCTION_TAG + canonical_bytes(item)).hexdigest(),
        } for index, item in enumerate(inputs)],
        "target_domain": "D_1",
        "witness_version": "NLC-M5-T1-FUNCTIONAL-WITNESS/1.0",
        "workload_id": "NLC-FINITE-SYNTHETIC-WORKLOAD/1.0",
    }
    m3_hash, m4_hash = hashlib.sha256(m3).hexdigest(), hashlib.sha256(m4).hexdigest()
    cert = ReconstitutionCertificate(
        "Service_n", "D_1", 1, "nonce:m5t1-valid-0001",
        {
            "artifact_commit": M3_HEAD, "artifact_path": M3_PATH,
            "artifact_sha256": m3_hash, "artifact_version": m3_obj["artifact_version"],
            "eligibility": m3_obj["status"], "proof_commitment": m3_hash,
        },
        {
            "artifact_commit": M4_HEAD, "artifact_path": M4_PATH,
            "artifact_sha256": m4_hash, "artifact_version": m4_obj["artifact_version"],
            "candidate_identity": "Service_n", "eligibility": "ELIGIBLE",
            "fixture_id": fixture["fixture_id"], "report_commitment": fixture["verification_digest"],
            "rule_set_version": m4_obj["rule_set_version"],
        },
        witness, BARRIERS, CONSTRUCTORS,
    )
    context = RootAcceptContext(
        "D_1", 1, BARRIERS, CONSTRUCTORS, frozenset(), M3_HEAD, M3_PATH, m3,
        M4_HEAD, M4_PATH, m4,
    )
    return cert, context
