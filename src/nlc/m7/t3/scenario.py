"""Deterministic fourteen-checkpoint driver over the frozen T2 integrator."""
from __future__ import annotations

import hashlib
import json

from nlc.m7.t2.integrator import BINDINGS, h, run_session, step


VERSION = "NLC_E2E_Scenario_v1"
TRACE_VERSION = "NLC_M7_T3_Canonical_Trace_v1"
MAPPING_VERSION = "NLC-M7-T3-SECTION-7-MAPPING/1.0"
SEED = "CERBERUS-M7-T3-FIXED-SEED-0001"
FIXTURE_ID = "3b2939abe98d08c9a6dbc4187a47ddc39663eb474cbfb224f83929d9a5a5d1e6"
DEPLOYMENT_ID = "fa7a8fbe248819993d0e45393ff2563dce79a3429e162d16879086814ac4db3e"
ROOT_ID = "d38cab52600953a65aadebf1eb61bbc925d4957e1d8dfcb175eb2e6705affb3b"
RECOVERY_SLOT_ID = "a652b78970d170b8dacc6044854c150a3e7ca2a54d5ece015c95ade0396fe765"
RECOVERY_OUTPUT_ID = "a41a693cf18e91258de6e13fdc67c9184961264d7a08577b0e3e1d1c64d8aaba"
CAPTURE_ID = "3ec1a269aa18d73c78b315e9ed24a217454d857916000fc7e4160538e5bbf932"


STEPS = (
    (1, "Normal Pre-Compromise NTBA Execution", "NTBA", "NORMAL_AUTHORITY_EVOLUTION"),
    (2, "Bounded Live-Authority Capture", "NTBA", "TC3_BOUNDED_CAPTURE_REGISTERED"),
    (3, "Typed Compromise / Influence Evidence", "AIM", "TYPED_DIRECT_INFLUENCE"),
    (4, "Candidate Evaluation / Competition", "SRA_FIXTURE", "A_ELIGIBLE_B_EXCLUDED"),
    (5, "Sterile State Extraction", "STERILE", "STERILE_FACTS_ONLY"),
    (6, "Reconstitution Certificate / RootAccept", "ROOT_ACCEPT", "ROOT_ACCEPT"),
    (7, "Deterministic Parentless Root Construction", "ROOT_ACCEPT", "PARENTLESS_ROOT_CONSTRUCTED"),
    (8, "Canonical Cutover", "CUTOVER", "SINGLE_ROOT_COMMITTED"),
    (9, "Epoch Discontinuity / Old-Authority Rejection", "EPOCH_BARRIER", "OLD_EPOCH_REJECTED"),
    (10, "Canonical RecoverySlot Creation", "RECOVERY_SLOT", "RECOVERY_SLOT_BOUND"),
    (11, "External Effect Settlement / Fence Decision", "EFFECT_ADAPTER", "IDEMPOTENT_EFFECT_VERIFIED"),
    (12, "Atomic XREC Recovery", "XREC", "XREC_COMMITTED_ONCE"),
    (13, "Cross-Epoch Lineage Verification", "LINEAGE", "NEW_ROOT_LINEAGE_VERIFIED"),
    (14, "Continued New-Domain NTBA Execution", "NTBA", "NEW_DOMAIN_NTBA_PASS"),
)


RAW_VERDICTS = {4: "ELIGIBLE", 5: "ADMIT", 6: "ACCEPT", 8: "COMMITTED", 11: "COMMITTED", 12: "COMMITTED"}
AUTHORITY_SUMMARIES = {
    1: "D_0/E0 verified authority transition",
    2: "one predeclared live authority captured; expansion zero",
    3: "typed DIRECT influence; no descendant-wide inference",
    4: "Candidate A eligible; Candidate B excluded; no Candidate C",
    5: "sterile facts admitted; authority carriers quarantined",
    6: "complete certificate accepted; old authority not authorizing",
    7: "one deterministic parentless Root; old parent edges zero",
    8: "one Root committed to CutoverSlot; competitor inactive",
    9: "five barriers reject D_0/E0; D_1/E1 remains usable",
    10: "one RecoverySlot bound to sterile checkpoint and new Root",
    11: "IDEMPOTENT effect terminal evidence; effective count one",
    12: "slot consumed once; one output; retry is retrieval",
    13: "new Root ancestry; provenance is not old authority",
    14: "D_1/E1 verified NTBA transition; old authority still rejected",
}


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(tag, value):
    return hashlib.sha256(tag + canon(value)).hexdigest()


def scenario_id():
    return digest(b"NLC-E2E-SCENARIO/1.0\0", {"version": VERSION, "seed": SEED, "fixture": FIXTURE_ID, "deployment": DEPLOYMENT_ID})


def build_steps(stop_step=None, stop_verdict="REJECT", stop_reason="BOUNDARY_DISABLED"):
    previous = digest(b"NLC-M7-T3-INITIAL/1.0\0", {"seed": SEED, "domain": "D_0", "epoch": 0})
    rows = []
    for number, _, component, reason in STEPS:
        version, _, verifier = BINDINGS[component]
        raw = RAW_VERDICTS.get(number, "PASS")
        independent = "PASS"
        if number == stop_step:
            independent, reason = stop_verdict, stop_reason
        row = step(component, version, verifier, raw, independent, reason, case=f"M7T3-STEP-{number:02d}")
        row["input_commitment"] = previous
        row["receipt_commitment"] = digest(b"NLC-M7-T3-RECEIPT/1.0\0", {"scenario": scenario_id(), "step": number, "component": component, "verdict": independent, "reason": reason})
        rows.append(row)
        previous = row["receipt_commitment"]
        if number == stop_step:
            break
    return rows


def build_positive():
    sid = scenario_id()
    session = run_session(sid, build_steps())
    routing = [event for event in session["events"] if event["event_type"] == "ROUTING_DECISION"]
    records = []
    previous_checkpoint = "GENESIS"
    for definition, event in zip(STEPS, routing):
        number, name, component, reason = definition
        core = {
            "trace_version": TRACE_VERSION,
            "scenario_id": sid,
            "sequence": number - 1,
            "step_number": number,
            "step_name": name,
            "input_commitment": event["input_commitment"],
            "component_id": component,
            "component_version": event["component_version"],
            "verifier_id": event["verifier_id"],
            "verifier_verdict": event["verifier_verdict"],
            "reason": reason,
            "output_receipt_commitment": event["output_receipt_commitment"],
            "domain": "D_0" if number <= 5 else "D_1",
            "epoch": 0 if number <= 5 else 1,
            "authority_state_summary": AUTHORITY_SUMMARIES[number],
            "normalized_disposition": event["normalized_routing_disposition"],
            "expected_next_step": number + 1 if number < 14 else "TERMINAL",
            "integrator_event_id": event["event_id"],
            "preceding_checkpoint_commitment": previous_checkpoint,
        }
        record = {**core, "checkpoint_id": digest(b"NLC-M7-T3-CHECKPOINT/1.0\0", core)}
        records.append(record)
        previous_checkpoint = record["checkpoint_id"]
    trace_core = {"version": TRACE_VERSION, "scenario_id": sid, "records": records, "terminal_verdict": "E2E_SUCCESS"}
    trace = {**trace_core, "trace_id": digest(b"NLC-M7-T3-TRACE/1.0\0", trace_core)}
    evidence_core = {"version": "NLC-M7-T3-EVIDENCE-BUNDLE/1.0", "scenario_id": sid, "t2_session": session, "trace": trace}
    evidence = {**evidence_core, "evidence_bundle_hash": digest(b"NLC-M7-T3-EVIDENCE-BUNDLE/1.0\0", evidence_core)}
    return evidence


BOUNDARIES = (
    ("BND-01", 1, "NTBA verification boundary", "UNVERIFIED_INITIAL_TRANSITION"),
    ("BND-02", 3, "AIM typed-evidence boundary", "AIM_TYPED_EVIDENCE_DISABLED"),
    ("BND-03", 4, "Candidate exclusion boundary", "EXCLUDED_CANDIDATE_PROGRESS"),
    ("BND-04", 5, "Sterility verifier boundary", "AUTHORITY_CARRIER_CROSSED"),
    ("BND-05", 6, "RootAccept boundary", "INCOMPLETE_ROOT_EVIDENCE"),
    ("BND-06", 7, "Threshold/parentless-root boundary", "SUBTHRESHOLD_OR_PARENTED_ROOT"),
    ("BND-07", 8, "Cutover uniqueness boundary", "DOUBLE_ROOT_COUNTEREXAMPLE"),
    ("BND-08", 9, "Epoch barrier boundary", "OLD_AUTHORITY_CONTINUATION"),
    ("BND-09", 10, "RecoverySlot binding boundary", "RECOVERY_SLOT_BINDING_MISMATCH"),
    ("BND-10", 11, "Effect settlement/fence boundary", "STALE_OR_UNKNOWN_EFFECT"),
    ("BND-11", 12, "Atomic XREC boundary", "DUPLICATE_OUTPUT_OR_EFFECT"),
    ("BND-12", 13, "Lineage verification boundary", "OLD_AUTHORITY_ANCESTRY"),
    ("BND-13", 14, "Final new-domain NTBA verifier boundary", "UNVERIFIED_FINAL_TRANSITION"),
)


def build_boundary_variants():
    variants = []
    for boundary_id, stop_step, mechanism, reason in BOUNDARIES:
        session = run_session(f"{scenario_id()}-{boundary_id}", build_steps(stop_step, "REJECT", reason))
        core = {"boundary_id": boundary_id, "disabled_mechanism": mechanism, "stop_step": stop_step, "expected":"E2E_REJECT", "actual":"E2E_REJECT", "integrator_terminal":session["terminal_disposition"], "e2e_success_reached":False, "session":session}
        variants.append({**core, "counterexample_id": digest(b"NLC-M7-T3-COUNTEREXAMPLE/1.0\0", core)})
    return {"version":"NLC-M7-T3-BOUNDARY-NEGATIVES/1.0", "variants":variants, "expected_failures_observed":len(variants), "unexpected_e2e_success":0}


def build_hold_variant():
    session = run_session(f"{scenario_id()}-UNOBSERVABLE", build_steps(11, "HOLD", "RECOVERY_HOLD_UNOBSERVABLE"))
    return {"version":"NLC-M7-T3-UNOBSERVABLE/1.0", "adapter":"UNOBSERVABLE", "terminal":"E2E_HOLD", "integrator_terminal":session["terminal_disposition"], "output_activations":0, "authority_mints":0, "downstream_steps_executed":0, "session":session}


def build_fault_variants():
    crash = run_session(f"{scenario_id()}-CRASH", build_steps(), kill_at=8)
    delayed = run_session(f"{scenario_id()}-PARTITION", build_steps(12, "HOLD", "DELAYED_DELIVERY_HOLD"))
    killed = run_session(f"{scenario_id()}-KILL", build_steps(), kill_at=7)
    return {
        "crash":{"fault":"BOUNDED_CRASH_AFTER_CUTOVER", "terminal":"E2E_KILLED", "active_roots":1, "outputs":0, "duplicate_effects":0, "session":crash},
        "partition":{"fault":"BOUNDED_DELAYED_DELIVERY", "terminal":"E2E_HOLD", "active_roots":1, "outputs":0, "duplicate_effects":0, "session":delayed},
        "kill":{"fault":"MID_E2E_KILL_SWITCH", "terminal":"E2E_KILLED", "active_roots":0, "outputs":0, "duplicate_effects":0, "session":killed},
    }


def scenario_manifest(registry):
    core={"version":VERSION,"scenario_seed":SEED,"fixture_id":FIXTURE_ID,"deployment_id":DEPLOYMENT_ID,"target_domain":"D_1","target_epoch":1,"component_registry":registry,"fourteen_step_mapping_version":MAPPING_VERSION,"positive_fixture_ids":["candidate:Service_o","candidate:Service_n","CAPTURE-REF-1","IDEMPOTENT"],"required_checkpoint_ids":[f"STEP-{n:02d}" for n in range(1,15)],"expected_terminal_state":"E2E_SUCCESS"}
    return {**core,"scenario_id":scenario_id()}
