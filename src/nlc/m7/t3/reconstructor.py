"""Independent evidence-only reconstruction for NLC M7-T3."""
import hashlib
import json

from nlc.m7.t2.reconstructor import reconstruct as reconstruct_t2

EXPECTED_COMPONENTS=("NTBA","NTBA","AIM","SRA_FIXTURE","STERILE","ROOT_ACCEPT","ROOT_ACCEPT","CUTOVER","EPOCH_BARRIER","RECOVERY_SLOT","EFFECT_ADAPTER","XREC","LINEAGE","NTBA")

def canon(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def digest(tag,value):
    return hashlib.sha256(tag+canon(value)).hexdigest()


def reconstruct(bundle):
    try:
        trace=bundle["trace"];records=trace["records"]
        if len(records)!=14:raise ValueError("MISSING_STEP")
        previous="GENESIS";previous_receipt=None
        for index,record in enumerate(records):
            if record["sequence"]!=index or record["step_number"]!=index+1:raise ValueError("STEP_ORDER")
            if record["component_id"]!=EXPECTED_COMPONENTS[index]:raise ValueError("COMPONENT_SEQUENCE_OR_BYPASS")
            if (record["domain"],record["epoch"]) != (("D_0",0) if index<5 else ("D_1",1)):raise ValueError("DOMAIN_EPOCH_SEQUENCE")
            core={key:value for key,value in record.items() if key!="checkpoint_id"}
            if record["checkpoint_id"]!=digest(b"NLC-M7-T3-CHECKPOINT/1.0\0",core):raise ValueError("CHECKPOINT_ID")
            if record["preceding_checkpoint_commitment"]!=previous:raise ValueError("CHECKPOINT_CHAIN")
            if previous_receipt is not None and record["input_commitment"]!=previous_receipt:raise ValueError("CROSS_STEP_BINDING")
            if record["verifier_verdict"] not in {"PASS","ACCEPT"} or record["normalized_disposition"]!="CONTINUE":raise ValueError("VERDICT")
            previous=record["checkpoint_id"];previous_receipt=record["output_receipt_commitment"]
        trace_core={key:value for key,value in trace.items() if key!="trace_id"}
        if trace["trace_id"]!=digest(b"NLC-M7-T3-TRACE/1.0\0",trace_core):raise ValueError("TRACE_ID")
        t2=reconstruct_t2(bundle["t2_session"]["events"])
        if t2["verdict"]!="ACCEPT" or t2["terminal"]!="CONTINUE" or len(t2["verified"])!=14:raise ValueError("T2_EVIDENCE")
        routing=[event for event in bundle["t2_session"]["events"] if event["event_type"]=="ROUTING_DECISION"]
        if any(record["integrator_event_id"]!=event["event_id"] or record["output_receipt_commitment"]!=event["output_receipt_commitment"] for record,event in zip(records,routing)):raise ValueError("INTEGRATOR_BINDING")
        evidence_core={key:value for key,value in bundle.items() if key!="evidence_bundle_hash"}
        if bundle["evidence_bundle_hash"]!=digest(b"NLC-M7-T3-EVIDENCE-BUNDLE/1.0\0",evidence_core):raise ValueError("BUNDLE_HASH")
        return {"verdict":"ACCEPT","terminal":"E2E_SUCCESS","completed_steps":14,"independently_evidenced_steps":14,"reconstructed_steps":14,"missing_steps":0,"binding_failures":0,"runtime_state_dependency":False,"trace_id":trace["trace_id"],"evidence_bundle_hash":bundle["evidence_bundle_hash"]}
    except Exception as error:
        return {"verdict":"REJECT","reason":str(error)}
