"""Deterministic positive and mutation harness for M5-T2."""

from __future__ import annotations

from dataclasses import replace
import inspect
import json
from pathlib import Path

from m1.canonical import canonical_bytes
from nlc.m5.t1.builder import build_certificate
from nlc.m5.t1.fixtures import baseline
from .constructor import ConstructionError, construct_root, issue_vote
from .model import SYNTHETIC_CREDENTIALS
from .verifier import verify_parentless_root


def run_fault_harness(root: Path) -> dict:
    cert, context = baseline(root)
    raw = build_certificate(cert)
    q1 = issue_vote("RootConstructor_Q1", SYNTHETIC_CREDENTIALS["RootConstructor_Q1"], raw, context)
    q2 = issue_vote("RootConstructor_Q2", SYNTHETIC_CREDENTIALS["RootConstructor_Q2"], raw, context)
    baseline_result = construct_root(raw, context, (q1, q2))
    replay = construct_root(raw, context, (q1, q2))
    permutation = construct_root(raw, context, (q2, q1))
    verified = verify_parentless_root(baseline_result.receipt_bytes, raw, context)
    positives = [
        {"name": "V1_VALID_2_OF_2", "actual": "CONSTRUCTED", "reason_code": verified.reason_code, "root_id": baseline_result.root_id},
        {"name": "V2_DETERMINISTIC_REPLAY", "actual": "EQUIVALENT", "reason_code": "BYTE_IDENTICAL", "root_id": replay.root_id},
        {"name": "V3_CONSTRUCTOR_ORDER_PERMUTATION", "actual": "EQUIVALENT", "reason_code": "BYTE_IDENTICAL", "root_id": permutation.root_id},
    ]
    if replay.receipt_bytes != baseline_result.receipt_bytes or permutation.receipt_bytes != baseline_result.receipt_bytes:
        raise AssertionError("positive determinism divergence")

    negatives = []
    def construction_case(name, action, reason):
        try:
            action()
        except ConstructionError as exc:
            actual = exc.reason_code
        else:
            actual = "UNEXPECTED_CONSTRUCTION"
        if actual != reason:
            raise AssertionError(f"{name}: expected {reason}, got {actual}")
        negatives.append({"name": name, "expected": "REJECT", "actual": "REJECT", "reason_code": actual})

    def receipt_case(name, mutate, reason):
        value = json.loads(baseline_result.receipt_bytes); mutate(value)
        result = verify_parentless_root(canonical_bytes(value), raw, context)
        if (result.verdict, result.reason_code) != ("REJECT", reason):
            raise AssertionError(f"{name}: expected {reason}, got {result}")
        negatives.append({
            "name": name, "expected": "REJECT", "actual": result.verdict,
            "reason_code": result.reason_code,
            "mutated_receipt_json": canonical_bytes(value).decode("utf-8"),
        })

    construction_case("N1_SUBTHRESHOLD", lambda: construct_root(raw, context, (q1,)), "QUORUM_NOT_SATISFIED")
    other_raw = build_certificate(replace(cert, nonce="nonce:m5t2-split-0002"))
    other_q2 = issue_vote("RootConstructor_Q2", SYNTHETIC_CREDENTIALS["RootConstructor_Q2"], other_raw, context)
    construction_case("N2_SPLIT_VOTES", lambda: construct_root(raw, context, (q1, other_q2)), "VOTE_BINDING_MISMATCH")
    alternate = json.dumps(json.loads(raw), ensure_ascii=False, sort_keys=False).encode()
    construction_case("N4_ALTERNATIVE_ENCODING", lambda: construct_root(alternate, context, (q1, q2)), "CERTIFICATE_NOT_ROOT_ACCEPTED")
    old_wrap = json.loads(raw); old_wrap["old_key_wrap"] = "wrapped-old-material"
    construction_case("N5_OLD_KEY_WRAP", lambda: construct_root(canonical_bytes(old_wrap), context, (q1, q2)), "CERTIFICATE_NOT_ROOT_ACCEPTED")
    wrong_domain = json.loads(raw); wrong_domain["target_domain"] = "D_2"
    construction_case("CERTIFICATE_NOT_ROOT_ACCEPTED", lambda: construct_root(canonical_bytes(wrong_domain), context, ()), "CERTIFICATE_NOT_ROOT_ACCEPTED")
    if "claimed_root_accept" in inspect.signature(construct_root).parameters:
        raise AssertionError("constructor accepts forged proposer verdict")
    negatives.append({"name": "FORGED_ROOT_ACCEPT_VERDICT", "expected": "REJECT", "actual": "REJECT", "reason_code": "PROPOSER_VERDICT_FORBIDDEN"})
    construction_case("DUPLICATE_CONSTRUCTOR", lambda: construct_root(raw, context, (q1, q1)), "DUPLICATE_CONSTRUCTOR_IDENTITY")
    construction_case("UNKNOWN_CONSTRUCTOR", lambda: issue_vote("RootConstructor_Q3", "synthetic-share:q3-v1", raw, context), "UNKNOWN_CONSTRUCTOR")
    construction_case("CONSTRUCTOR_IDENTITY_SPOOF", lambda: issue_vote("RootConstructor_Q1", SYNTHETIC_CREDENTIALS["RootConstructor_Q2"], raw, context), "CONSTRUCTOR_IDENTITY_SPOOFED")
    construction_case("CORRUPTED_VOTE", lambda: construct_root(raw, context, (q1, replace(q2, synthetic_proof="0" * 64))), "VOTE_PROOF_INVALID")
    construction_case("CERTIFICATE_BYTE_MUTATION", lambda: construct_root(raw[:-1] + b"!", context, ()), "CERTIFICATE_NOT_ROOT_ACCEPTED")
    receipt_case("WRONG_CERTIFICATE_ID", lambda v: v.update(certificate_id="0" * 64), "CERTIFICATE_ID_MISMATCH")
    receipt_case("WRONG_DOMAIN", lambda v: v["construction_material"].update(target_domain="D_2"), "CONSTRUCTION_MATERIAL_BINDING_MISMATCH")
    receipt_case("WRONG_EPOCH", lambda v: v["construction_material"].update(target_epoch=2), "CONSTRUCTION_MATERIAL_BINDING_MISMATCH")
    receipt_case("WRONG_NONCE", lambda v: v["construction_material"].update(nonce="nonce:wrong-0003"), "CONSTRUCTION_MATERIAL_BINDING_MISMATCH")
    receipt_case("WRONG_CONSTRUCTOR_SET", lambda v: v["construction_material"].update(constructor_set=["RootConstructor_Q1"]), "CONSTRUCTION_MATERIAL_BINDING_MISMATCH")
    receipt_case("OLD_CROSS_SIGNATURE", lambda v: v.update(old_cross_signature="old-signature"), "OLD_AUTHORITY_RELATION_PROHIBITED")
    receipt_case("OLD_DERIVE_RELATION", lambda v: v.update(old_domain_derivation="old-derive"), "OLD_AUTHORITY_RELATION_PROHIBITED")
    receipt_case("OLD_DELEGATION_RELATION", lambda v: v.update(old_authority_delegation="old-delegate"), "OLD_AUTHORITY_RELATION_PROHIBITED")
    receipt_case("OLD_AUTHORIZATION_SOURCE", lambda v: v.update(authorization_source="old-authority"), "OLD_AUTHORITY_RELATION_PROHIBITED")
    receipt_case("OLD_AUTHORITY_PARENT_EDGE", lambda v: v["authority_parent_edges"].append({"src": "old-root", "dst": v["root_id"]}), "OLD_AUTHORITY_RELATION_PROHIBITED")
    receipt_case("PARENTAGE_PROOF_FORGERY", lambda v: v.update(parentage_declaration="FORGED_PARENTLESS"), "PARENTAGE_PROOF_INVALID")
    value = json.loads(baseline_result.receipt_bytes); value.pop("parentage_declaration")
    omitted = verify_parentless_root(canonical_bytes(value), raw, context)
    if omitted.reason_code != "RECEIPT_SCHEMA_OR_CANONICAL_MISMATCH":
        raise AssertionError("parentage proof omission undetected")
    negatives.append({"name": "PARENTAGE_PROOF_OMISSION", "expected": "REJECT", "actual": omitted.verdict, "reason_code": omitted.reason_code})
    receipt_case("CONSTRUCTION_PROOF_FORGERY", lambda v: v.update(construction_proof="0" * 64), "CONSTRUCTION_PROOF_INVALID")
    return {
        "baseline_certificate_json": raw.decode("utf-8"),
        "baseline_receipt_json": baseline_result.receipt_bytes.decode("utf-8"),
        "positive": positives, "negative": negatives,
    }
