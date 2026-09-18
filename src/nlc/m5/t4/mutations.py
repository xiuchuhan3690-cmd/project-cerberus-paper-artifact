"""Single-variable mutations and isolated single-barrier disabled mutants."""

from __future__ import annotations
from copy import deepcopy
import json
from m1.canonical import canonical_bytes
from .canonical import ARTIFACT_TAG,EVIDENCE_TAG,artifact_material,decision,tagged_hash
from .fixtures import mutate,valid
from .model import BARRIER_ORDER
from .suite import VERIFIERS,combine,evaluate


FIXTURE_FOR_BARRIER={
    "NAMESPACE":"B1_OLD_NAMESPACE","VERIFIER_DOMAIN":"B2_OLD_VERIFIER",
    "CRYPTOGRAPHIC_ROOT":"B3_OLD_CRYPTO_ROOT","SEMANTIC_GRAMMAR":"B4_OLD_GRAMMAR",
    "PROTOCOL_ADAPTER":"B5_LEGACY_ADAPTER",
}


def disabled_evaluate(artifact,context,disabled):
    """Mutation-only broken control: bypass exactly one verifier."""
    decisions=[]
    for name in BARRIER_ORDER:
        if name==disabled: decisions.append(decision(name,artifact,context,"PASS","MUTANT_BARRIER_DISABLED"))
        else: decisions.append(VERIFIERS[name](artifact,context))
    return combine(artifact,context,decisions)


def counterexamples(fixtures,context):
    rows=[]
    for index,name in enumerate(BARRIER_ORDER,1):
        fixture_id=FIXTURE_FOR_BARRIER[name]; artifact=fixtures[fixture_id]
        result=disabled_evaluate(artifact,context,name)
        trace=[
            {"step":1,"event":"PRESENT_OLD_AUTHORITY_ARTIFACT","artifact_id":artifact["artifact_id"]},
            {"step":2,"event":"BYPASS_SINGLE_BARRIER","disabled_barrier":name,"remaining_enabled":[x for x in BARRIER_ORDER if x!=name]},
            {"step":3,"event":"OLD_AUTHORITY_EFFECTIVE","decision_id":result.decision_id},
        ]
        material={"counterexample_id":f"TC1-T4-{index}-{name}","disabled_barrier":name,"fixture_id":fixture_id,"normalized_reason":"OLD_AUTHORITY_CONTINUATION_VIA_DISABLED_BARRIER","remaining_enabled":[x for x in BARRIER_ORDER if x!=name],"shortest_trace_length":3,"starting_old_authority_artifact":artifact,"trace":trace,"violated_property":"TC-1 Old Authority Non-Continuation"}
        rows.append({**material,"counterexample_hash":__import__("hashlib").sha256(canonical_bytes(material)).hexdigest(),"authority_effective":result.authority_effective,"combined_decision":json.loads(result.decision_bytes)})
    return rows


def mutation_inputs(context):
    base=valid(context); rows=[]
    def add(name,artifact,reason): rows.append({"mutation_id":name,"kind":"ARTIFACT","artifact":artifact,"expected":"REJECT","expected_reason":reason})
    add("old_namespace_token",mutate(base,namespace_id="NLC:NS:OLD:D_0:E0"),"OLD_OR_WRONG_NAMESPACE")
    add("wrong_namespace_version",mutate(base,namespace_version="NLC-NAMESPACE/OLD/0.9"),"NAMESPACE_VERSION_MISMATCH")
    add("old_verifier_artifact",mutate(base,verifier_domain_id="NLC:VERIFIER-DOMAIN:OLD:D_0:E0"),"OLD_OR_WRONG_VERIFIER_DOMAIN")
    add("wrong_verifier_domain_id",mutate(base,verifier_domain_id="NLC:VERIFIER-DOMAIN:WRONG"),"OLD_OR_WRONG_VERIFIER_DOMAIN")
    bad_signature=deepcopy(base); bad_signature["synthetic_signature"]="0"*64; bad_signature["artifact_id"]=tagged_hash(ARTIFACT_TAG,artifact_material(bad_signature))
    add("old_root_signature",bad_signature,"SYNTHETIC_SIGNATURE_INVALID")
    add("old_verification_root_id",mutate(base,cryptographic_root_id="NLC:SYNTHETIC-CRYPTO-ROOT:OLD:E0"),"OLD_OR_WRONG_CRYPTOGRAPHIC_ROOT")
    add("old_parser_object",mutate(base,grammar_id="NLC-LEGACY-AUTHORITY-GRAMMAR/0.9"),"OLD_OR_UNSUPPORTED_GRAMMAR")
    add("parser_bridge_mutation",mutate(base,request_format="OPAQUE_LEGACY_PARSER_BRIDGE"),"PARSER_BRIDGE_OR_OPAQUE_FORMAT_PROHIBITED")
    add("legacy_adapter_request",mutate(base,protocol_adapter_id="NLC:LEGACY-AUTHORITY-ADAPTER"),"LEGACY_OR_UNKNOWN_ADAPTER")
    add("old_adapter_version",mutate(base,protocol_adapter_version="0.9"),"ADAPTER_VERSION_MISMATCH")
    add("stale_cutover_receipt",mutate(base,cutover_receipt_id="0"*64),"STALE_CUTOVER_RECEIPT")
    add("wrong_active_root_id",mutate(base,root_id="0"*64),"ACTIVE_ROOT_MISMATCH")
    add("wrong_epoch",mutate(base,target_epoch=context.target_epoch+1),"TARGET_EPOCH_MISMATCH")
    add("wrong_domain",mutate(base,target_domain="D_OLD"),"TARGET_DOMAIN_MISMATCH")
    add("wrong_cutover_receipt_hash",mutate(base,cutover_receipt_sha256="0"*64),"CUTOVER_RECEIPT_HASH_MISMATCH")
    add("old_authority_claim",mutate(base,authority_claim="OLD_AUTHORITY_CONTINUATION"),"AUTHORITY_CLAIM_INVALID")
    positive=json.loads(evaluate(base,context).decision_bytes)
    rows.extend([
        {"mutation_id":"missing_barrier_evidence","kind":"DECISION","decision":{**positive,"barrier_decisions":positive["barrier_decisions"][:-1]},"expected":"REJECT","expected_reason":"BARRIER_EVIDENCE_COUNT_INVALID"},
        {"mutation_id":"forged_barrier_evidence","kind":"DECISION","decision":deepcopy(positive),"expected":"REJECT","expected_reason":"EVIDENCE_COMMITMENT_MISMATCH"},
        {"mutation_id":"unknown_barrier_result","kind":"DECISION","decision":deepcopy(positive),"expected":"REJECT","expected_reason":"INDIVIDUAL_VERDICT_MISMATCH"},
    ])
    rows[-2]["decision"]["barrier_decisions"][0]["evidence_commitment"]="0"*64
    unknown=rows[-1]["decision"]["barrier_decisions"][0]; unknown["verdict"]="UNKNOWN"
    unsigned={k:v for k,v in unknown.items() if k!="evidence_commitment"}; unknown["evidence_commitment"]=tagged_hash(EVIDENCE_TAG,unsigned)
    return rows
