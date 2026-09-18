"""Independent verifier; intentionally imports no constructor or store code."""

from __future__ import annotations
from dataclasses import dataclass
import hashlib,json,unicodedata
from .model import *

@dataclass(frozen=True)
class Verification: verdict:str;reason:str;slot_id:str|None=None;output_set_id:str|None=None
class Bad(ValueError):pass
def _pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out:raise Bad("DUPLICATE_FIELD")
        out[k]=v
    return out
def _norm(v):
    if v is None or isinstance(v,float):raise Bad("MALFORMED")
    if isinstance(v,(bool,int)):return v
    if isinstance(v,str):return unicodedata.normalize("NFC",v)
    if isinstance(v,list):return [_norm(x) for x in v]
    if isinstance(v,dict):return {unicodedata.normalize("NFC",k):_norm(x) for k,x in v.items()}
    raise Bad("MALFORMED")
def enc(v):return json.dumps(_norm(v),ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def h(domain,value):return hashlib.sha256(domain+enc(value)).hexdigest()
def no_old_carrier(value):
    forbidden=("old_token","old_capability","old_credential","refresh_grant","delegation","authority_parent","signing_authority","authority_secret","opaque_carrier","verifier_object","parser_object")
    if isinstance(value,dict):
        for key,item in value.items():
            if any(token in key.lower() for token in forbidden):raise Bad("OLD_AUTHORITY_CARRIER")
            no_old_carrier(item)
    elif isinstance(value,list):
        for item in value:no_old_carrier(item)
    elif isinstance(value,str) and any(token in value.lower() for token in ("old-token:","old-capability:","old-key:","old-refresh:","old-delegation:")):raise Bad("OLD_AUTHORITY_CARRIER")
def verify(slot_bytes:bytes,result:bytes):
    try:
        material=json.loads(slot_bytes.decode(),object_pairs_hook=_pairs);receipt=json.loads(result.decode(),object_pairs_hook=_pairs)
        if enc(material)!=slot_bytes or enc(receipt)!=result:raise Bad("NON_CANONICAL")
        if set(material)!=SLOT_FIELDS:raise Bad("SLOT_FIELDS")
        expected=(RECOVERY_PROTOCOL_VERSION,TARGET_DOMAIN,TARGET_EPOCH,CERTIFICATE_ID,ACTIVE_ROOT_ID,CUTOVER_SLOT_ID,CUTOVER_RECEIPT_ID,CUTOVER_RECEIPT_SHA256,OUTPUT_CONSTRUCTION_VERSION)
        actual=tuple(material[k] for k in ("recovery_protocol_version","target_domain","target_epoch","accepted_reconstitution_identity","active_root_id","cutover_slot_id","cutover_receipt_id","cutover_receipt_sha256","output_construction_version"))
        if actual!=expected:raise Bad("FROZEN_BINDING")
        proof=material["sterility_proof"]
        if proof!={"artifact_version":STERILITY_ARTIFACT_VERSION,"artifact_sha256":STERILITY_ARTIFACT_SHA256,"artifact_commit":STERILITY_ARTIFACT_COMMIT,"eligibility":"STERILITY_ARTIFACT_FOR_M5_FROZEN"}:raise Bad("STERILITY")
        no_old_carrier(material["sterile_checkpoint_identity"])
        facts=sorted(material["sterile_checkpoint_identity"],key=lambda x:(x["fact_id"],x["provenance_ref"],enc(x["value"])))
        if material["checkpoint_commitment"]!=h(b"NLC-STERILE-CHECKPOINT/1.0\x00",facts):raise Bad("CHECKPOINT")
        settlement=material["settlement_context"]
        if settlement.get("state")!="FENCED" or len(settlement.get("proof_identity",""))!=64 or any(c not in "0123456789abcdef" for c in settlement["proof_identity"]) or not settlement.get("fence_context","").startswith("synthetic-fence:"):raise Bad("SETTLEMENT")
        slot_id=h(SLOT_DOMAIN,{**material,"sterile_checkpoint_identity":facts})
        output=receipt["output_set"]
        if output["recovery_slot_id"]!=slot_id or receipt["recovery_slot_id"]!=slot_id or receipt["state"]!="CONSUMED" or receipt["mint_count"]!=1:raise Bad("SLOT_RESULT_BINDING")
        keys=[]
        for member in output["members"]:
            ancestry=member["authority_ancestry"]
            if ancestry!={"domain":TARGET_DOMAIN,"epoch":TARGET_EPOCH,"parent_root_id":ACTIVE_ROOT_ID,"old_authority_parent_edges":[]}:raise Bad("ANCESTRY")
            exposed=(str(member["semantic_key"])+enc(member["payload"]).decode()).lower()
            if any(token in exposed for token in ("old-token:","old-capability:","old-key:","old-refresh:","old-delegation:")):raise Bad("LOST_CAPABILITY")
            body={k:member[k] for k in ("semantic_key","payload","authority_ancestry")}
            if member["output_id"]!=h(OUTPUT_DOMAIN,{"slot_id":slot_id,"body":body}):raise Bad("OUTPUT_ID")
            keys.append((member["semantic_key"],member["output_id"]))
        if keys!=sorted(keys) or len(keys)!=len(set(keys)):raise Bad("OUTPUT_ORDER_OR_DUPLICATE")
        expected_set=h(OUTPUT_SET_DOMAIN,{"slot_id":slot_id,"members":output["members"]})
        if output["output_set_id"]!=expected_set:raise Bad("OUTPUT_SET_ID")
        core={k:receipt[k] for k in ("result_version","state","recovery_slot_id","output_set","mint_count")}
        if receipt["result_id"]!=h(RECEIPT_DOMAIN,core):raise Bad("RESULT_ID")
        return Verification("ACCEPT","INDEPENDENT_RECOMPUTATION_PASS",slot_id,expected_set)
    except (Bad,KeyError,TypeError,UnicodeError,json.JSONDecodeError) as exc:return Verification("REJECT",str(exc))
