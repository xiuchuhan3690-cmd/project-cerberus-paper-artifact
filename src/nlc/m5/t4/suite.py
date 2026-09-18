"""All-five-required production-shaped bounded barrier composition."""

from __future__ import annotations
import json
from m1.canonical import canonical_bytes
from .canonical import ARTIFACT_TAG,COMBINED_TAG,artifact_material,tagged_hash
from .model import BARRIER_ORDER,COMBINED_VERSION,CombinedDecision,SUITE_VERSION
from . import namespace,verifier_domain,cryptographic_root,semantic_grammar,protocol_adapter


VERIFIERS={
    "NAMESPACE":namespace.verify,"VERIFIER_DOMAIN":verifier_domain.verify,
    "CRYPTOGRAPHIC_ROOT":cryptographic_root.verify,"SEMANTIC_GRAMMAR":semantic_grammar.verify,
    "PROTOCOL_ADAPTER":protocol_adapter.verify,
}


def _binding_reason(artifact,context):
    try: expected_artifact_id=tagged_hash(ARTIFACT_TAG,artifact_material(artifact))
    except (KeyError,TypeError): return "ARTIFACT_MALFORMED"
    if artifact.get("artifact_id")!=expected_artifact_id: return "ARTIFACT_ID_MISMATCH"
    if artifact.get("artifact_version")!="NLC-EPOCH-AUTHORITY-ARTIFACT/1.0":return "ARTIFACT_VERSION_INVALID"
    if artifact.get("authority_claim")!="NATIVE_NEW_EPOCH_AUTHORITY":return "AUTHORITY_CLAIM_INVALID"
    checks=(("root_id",context.active_root_id,"ACTIVE_ROOT_MISMATCH"),("cutover_slot_id",context.cutover_slot_id,"CUTOVER_SLOT_MISMATCH"),("cutover_receipt_id",context.cutover_receipt_id,"STALE_CUTOVER_RECEIPT"),("cutover_receipt_sha256",context.cutover_receipt_sha256,"CUTOVER_RECEIPT_HASH_MISMATCH"),("target_domain",context.target_domain,"TARGET_DOMAIN_MISMATCH"),("target_epoch",context.target_epoch,"TARGET_EPOCH_MISMATCH"))
    for key,expected,reason in checks:
        if artifact.get(key)!=expected:return reason
    return None


def combine(artifact,context,decisions):
    binding=_binding_reason(artifact,context)
    all_pass=not binding and len(decisions)==5 and [d.barrier_id for d in decisions]==list(BARRIER_ORDER) and all(d.verdict=="PASS" for d in decisions)
    reason="ALL_FIVE_BARRIERS_PASS" if all_pass else binding or next((d.reason_code for d in decisions if d.verdict!="PASS"),"BARRIER_EVIDENCE_INCOMPLETE")
    material={"active_binding":context.__dict__,"authority_ancestry":[],"authority_effective":all_pass,"barrier_decisions":[d.__dict__ for d in decisions],"combined_version":COMBINED_VERSION,"input_artifact_id":artifact.get("artifact_id","MISSING"),"old_authority_relations":[],"reason_code":reason,"suite_version":SUITE_VERSION,"verdict":"PASS" if all_pass else "REJECT"}
    decision_id=tagged_hash(COMBINED_TAG,material); value={**material,"decision_id":decision_id}
    return CombinedDecision(canonical_bytes(value),decision_id,value["verdict"],reason,all_pass)


def evaluate(artifact,context):
    return combine(artifact,context,[VERIFIERS[name](artifact,context) for name in BARRIER_ORDER])
