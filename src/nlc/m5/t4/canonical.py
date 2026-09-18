"""Pure canonical construction primitives for T4 artifacts and evidence."""

from __future__ import annotations
import hashlib
from m1.canonical import canonical_bytes
from .model import BARRIER_VERSIONS,VERIFIER_VERSIONS,BarrierDecision


ARTIFACT_TAG=b"NLC-M5-T4-EPOCH-ARTIFACT-v1\x00"
EVIDENCE_TAG=b"NLC-M5-T4-BARRIER-EVIDENCE-v1\x00"
COMBINED_TAG=b"NLC-M5-T4-COMBINED-DECISION-v1\x00"
SIGNATURE_TAG=b"NLC-M5-T4-SYNTHETIC-SIGNATURE-v1\x00"


def tagged_hash(tag:bytes,value:dict)->str:
    return hashlib.sha256(tag+canonical_bytes(value)).hexdigest()


def artifact_material(value:dict)->dict:
    return {key:value[key] for key in (
        "artifact_version","authority_claim","cryptographic_root_id","cutover_receipt_id",
        "cutover_receipt_sha256","cutover_slot_id","grammar_id","namespace_id","namespace_version",
        "protocol_adapter_id","protocol_adapter_version","request_format","root_id","synthetic_signature",
        "target_domain","target_epoch","verifier_domain_id","verifier_version",
    )}


def signature_material(value:dict)->dict:
    return {key:value[key] for key in ("authority_claim","cryptographic_root_id","root_id","target_domain","target_epoch")}


def seal_artifact(value:dict)->dict:
    unsigned=dict(value); unsigned.pop("artifact_id",None)
    unsigned["synthetic_signature"]=tagged_hash(SIGNATURE_TAG,signature_material(unsigned))
    unsigned["artifact_id"]=tagged_hash(ARTIFACT_TAG,artifact_material(unsigned))
    return unsigned


def decision(barrier_id:str, artifact:dict, context, verdict:str, reason_code:str)->BarrierDecision:
    material={
        "barrier_id":barrier_id,"barrier_version":BARRIER_VERSIONS[barrier_id],
        "decision_version":"NLC-EPOCH-BARRIER-DECISION/1.0","expected_domain":context.target_domain,
        "expected_epoch":context.target_epoch,"input_artifact_id":artifact.get("artifact_id","MISSING"),
        "observed_domain":artifact.get("target_domain","MISSING"),"observed_epoch":artifact.get("target_epoch",-1),
        "reason_code":reason_code,"verdict":verdict,"verifier_id":f"EpochBarrierVerifier_{barrier_id}",
        "verifier_version":VERIFIER_VERSIONS[barrier_id],
    }
    commitment=tagged_hash(EVIDENCE_TAG,material)
    return BarrierDecision(**material,evidence_commitment=commitment)
