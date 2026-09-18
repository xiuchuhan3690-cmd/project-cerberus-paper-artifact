"""Pure RecoverySlot/output construction plus single-slot retrieval store."""

from __future__ import annotations
from dataclasses import dataclass
from .canonical import CanonicalError,decode,digest,encode
from .model import *

class RecoveryReject(ValueError): pass
class RecoveryHold(ValueError): pass

def _exact(value:dict,fields:frozenset[str],reason="SLOT_FIELDS_INVALID"):
    if not isinstance(value,dict) or set(value)!=fields: raise RecoveryReject(reason)
def _hex(value): return isinstance(value,str) and len(value)==64 and all(c in "0123456789abcdef" for c in value)
def _scan_authority(value):
    forbidden=("old_token","old_capability","old_credential","refresh_grant","delegation","authority_parent","signing_authority","authority_secret","opaque_carrier","verifier_object","parser_object")
    if isinstance(value,dict):
        for key,item in value.items():
            if any(token in key.lower() for token in forbidden): raise RecoveryReject("OLD_AUTHORITY_CARRIER_PROHIBITED")
            _scan_authority(item)
    elif isinstance(value,list):
        for item in value:_scan_authority(item)
    elif isinstance(value,str) and any(token in value.lower() for token in ("old-token:","old-capability:","old-key:","old-delegation:","old-refresh:")):
        raise RecoveryReject("OLD_AUTHORITY_CARRIER_PROHIBITED")

def validate_material(material:dict):
    _exact(material,SLOT_FIELDS)
    expected={"recovery_protocol_version":RECOVERY_PROTOCOL_VERSION,"target_domain":TARGET_DOMAIN,"target_epoch":TARGET_EPOCH,"accepted_reconstitution_identity":CERTIFICATE_ID,"active_root_id":ACTIVE_ROOT_ID,"cutover_slot_id":CUTOVER_SLOT_ID,"cutover_receipt_id":CUTOVER_RECEIPT_ID,"cutover_receipt_sha256":CUTOVER_RECEIPT_SHA256,"output_construction_version":OUTPUT_CONSTRUCTION_VERSION}
    for key,value in expected.items():
        if material[key]!=value: raise RecoveryReject("BINDING_MISMATCH:"+key)
    proof=material["sterility_proof"]
    _exact(proof,frozenset({"artifact_version","artifact_sha256","artifact_commit","eligibility"}),"STERILITY_PROOF_FIELDS_INVALID")
    if proof!={"artifact_version":STERILITY_ARTIFACT_VERSION,"artifact_sha256":STERILITY_ARTIFACT_SHA256,"artifact_commit":STERILITY_ARTIFACT_COMMIT,"eligibility":"STERILITY_ARTIFACT_FOR_M5_FROZEN"}: raise RecoveryReject("STERILITY_PROOF_INVALID")
    facts=material["sterile_checkpoint_identity"]
    _scan_authority(facts)
    if not isinstance(facts,list) or not facts or any(not isinstance(x,dict) or set(x)!={"fact_id","provenance_ref","value"} for x in facts): raise RecoveryReject("CHECKPOINT_FACTS_INVALID")
    canonical_facts=sorted(facts,key=lambda x:(x["fact_id"],x["provenance_ref"],encode(x["value"])))
    if material["checkpoint_commitment"]!=digest(b"NLC-STERILE-CHECKPOINT/1.0\x00",canonical_facts): raise RecoveryReject("CHECKPOINT_COMMITMENT_MISMATCH")
    if not isinstance(material["effect_scope_identity"],str) or not material["effect_scope_identity"]: raise RecoveryReject("EFFECT_SCOPE_INVALID")
    settlement=material["settlement_context"]
    _exact(settlement,frozenset({"state","proof_identity","fence_context"}),"SETTLEMENT_FIELDS_INVALID")
    if settlement["state"]=="UNKNOWN": raise RecoveryHold("SETTLEMENT_UNKNOWN")
    if settlement["state"]!="FENCED" or not _hex(settlement["proof_identity"]) or not settlement["fence_context"].startswith("synthetic-fence:"): raise RecoveryHold("SETTLEMENT_UNVERIFIED")
    if not isinstance(material["recovery_request_identity"],str) or not material["recovery_request_identity"]: raise RecoveryReject("REQUEST_IDENTITY_INVALID")
    return {**material,"sterile_checkpoint_identity":canonical_facts}

def slot(material:dict):
    normalized=validate_material(material);return normalized,digest(SLOT_DOMAIN,normalized)

def construct_outputs(material:dict,requested_templates:list[dict]):
    normalized,slot_id=slot(material)
    if not isinstance(requested_templates,list) or not requested_templates: raise RecoveryReject("OUTPUT_TEMPLATE_INVALID")
    members=[];seen=set()
    for template in requested_templates:
        _exact(template,frozenset({"semantic_key","payload","authority_template","lost_capability_ids"}),"OUTPUT_TEMPLATE_FIELDS_INVALID")
        _scan_authority(template["semantic_key"])
        _scan_authority(template["payload"])
        if template["lost_capability_ids"]: raise RecoveryReject("LOST_CAPABILITY_REISSUE_PROHIBITED")
        authority=template["authority_template"]
        _exact(authority,frozenset({"domain","epoch","authority_parent_root_id","old_authority_parent_edges"}),"AUTHORITY_TEMPLATE_FIELDS_INVALID")
        if authority!={"domain":TARGET_DOMAIN,"epoch":TARGET_EPOCH,"authority_parent_root_id":ACTIVE_ROOT_ID,"old_authority_parent_edges":[]}: raise RecoveryReject("NEW_DOMAIN_ANCESTRY_REQUIRED")
        key=template["semantic_key"]
        if key in seen: raise RecoveryReject("DUPLICATE_OUTPUT_MEMBER")
        seen.add(key)
        body={"semantic_key":key,"payload":template["payload"],"authority_ancestry":{"domain":TARGET_DOMAIN,"epoch":TARGET_EPOCH,"parent_root_id":ACTIVE_ROOT_ID,"old_authority_parent_edges":[]}}
        members.append({**body,"output_id":digest(OUTPUT_DOMAIN,{"slot_id":slot_id,"body":body})})
    members.sort(key=lambda x:(x["semantic_key"],x["output_id"]))
    output_set_id=digest(OUTPUT_SET_DOMAIN,{"slot_id":slot_id,"members":members})
    output_set={"output_construction_version":OUTPUT_CONSTRUCTION_VERSION,"recovery_slot_id":slot_id,"output_set_id":output_set_id,"members":members}
    return normalized,slot_id,output_set,encode(output_set)

def result_bytes(slot_id:str,output_set:dict):
    core={"result_version":RECEIPT_VERSION,"state":"CONSUMED","recovery_slot_id":slot_id,"output_set":output_set,"mint_count":1}
    return encode({**core,"result_id":digest(RECEIPT_DOMAIN,core)})

@dataclass
class Stored:
    state:str; result:bytes|None; output_set_id:str|None; mint_count:int; retrieval_count:int
class RecoveryStore:
    def __init__(self): self._slots={}
    def recover(self,material,templates,client_id):
        try: normalized,slot_id,output_set,_=construct_outputs(material,templates)
        except RecoveryHold as exc:
            normalized={**material};slot_id=digest(SLOT_DOMAIN,normalized);self._slots.setdefault(slot_id,Stored("HOLD",None,None,0,0));return {"verdict":"HOLD","reason":str(exc),"slot_id":slot_id,"result_bytes":None,"retrieval":False}
        stored=self._slots.get(slot_id)
        candidate=result_bytes(slot_id,output_set)
        if stored:
            if stored.state=="HOLD": return {"verdict":"HOLD","reason":"SETTLEMENT_HOLD","slot_id":slot_id,"result_bytes":None,"retrieval":True}
            if stored.output_set_id!=output_set["output_set_id"] or stored.result!=candidate: raise RecoveryReject("DISTINCT_OUTPUT_FOR_CONSUMED_SLOT")
            stored.retrieval_count+=1;return {"verdict":"ACCEPT","reason":"RETRIEVED","slot_id":slot_id,"result_bytes":stored.result,"retrieval":True}
        self._slots[slot_id]=Stored("CONSUMED",candidate,output_set["output_set_id"],1,0)
        return {"verdict":"ACCEPT","reason":"MINTED_ONCE","slot_id":slot_id,"result_bytes":candidate,"retrieval":False}
    def metrics(self,slot_id): return self._slots[slot_id]
