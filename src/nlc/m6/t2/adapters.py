"""Deterministic local adapter contracts; no real external effects."""
from __future__ import annotations
import hashlib
from nlc.m6.t1.canonical import encode
SLOT="a652b78970d170b8dacc6044854c150a3e7ca2a54d5ece015c95ade0396fe765";ROOT="d38cab52600953a65aadebf1eb61bbc925d4957e1d8dfcb175eb2e6705affb3b";DOMAIN="D_1";EPOCH=1;SCOPE="effect-scope:synthetic-ledger:v1";SUITE="NLC-EFFECT-ADAPTERS/1.0"
VERSIONS={x:f"NLC-{x}-ADAPTER/1.0" for x in ("IDEMPOTENT","ESCROWED","FENCED","UNOBSERVABLE")}
class Reject(ValueError):pass
def h(tag,v):return hashlib.sha256(tag+encode(v)).hexdigest()
def request(adapter="IDEMPOTENT",operation="op:restore:alpha",attempt="attempt:1",**kw):
    return {"adapter_class":adapter,"adapter_version":VERSIONS[adapter],"effect_scope_id":SCOPE,"operation_id":operation,"semantic_effect_id":h(b"NLC-SEMANTIC-EFFECT/1.0\0",{"scope":SCOPE,"operation":operation}),"recovery_slot_id":SLOT,"target_domain":DOMAIN,"target_epoch":EPOCH,"active_root_id":ROOT,"attempt_id":attempt,**kw}
def check(r):
    required={"adapter_class","adapter_version","effect_scope_id","operation_id","semantic_effect_id","recovery_slot_id","target_domain","target_epoch","active_root_id","attempt_id"}
    if set(r)-required-{"fence_generation","escrow_action","response_lost"}:raise Reject("UNKNOWN_FIELD")
    a=r.get("adapter_class");
    if a not in VERSIONS or r.get("adapter_version")!=VERSIONS[a]:raise Reject("ADAPTER_BINDING")
    if (r.get("effect_scope_id"),r.get("recovery_slot_id"),r.get("target_domain"),r.get("target_epoch"),r.get("active_root_id"))!=(SCOPE,SLOT,DOMAIN,EPOCH,ROOT):raise Reject("FROZEN_BINDING")
    if r.get("semantic_effect_id")!=h(b"NLC-SEMANTIC-EFFECT/1.0\0",{"scope":SCOPE,"operation":r.get("operation_id")}):raise Reject("SEMANTIC_EFFECT_ID")
def evidence(r,state):
    core={"evidence_version":"NLC-EFFECT-EVIDENCE/1.0","adapter_class":r["adapter_class"],"effect_id":r["semantic_effect_id"],"scope_id":SCOPE,"recovery_slot_id":SLOT,"terminal_state":state,"adapter_state_version":VERSIONS[r["adapter_class"]]}
    return {**core,"evidence_commitment":h(b"NLC-EFFECT-EVIDENCE/1.0\0",core)}
class Idempotent:
    def __init__(self):self.results={};self.effect_count=0
    def execute(self,r):
        check(r);key=r["semantic_effect_id"]
        if key not in self.results:self.effect_count+=1;self.results[key]=evidence(r,"CONFIRMED_SUCCESS")
        return {"verdict":"CONFIRMED_SUCCESS","evidence":self.results[key],"retrieval":self.effect_count==1 and key in self.results}
class Escrowed:
    def __init__(self):self.states={};self.receipts={};self.conflicts=0
    def execute(self,r):
        check(r);key=r["semantic_effect_id"];action=r.get("escrow_action","PREPARE");old=self.states.get(key,"NOT_PREPARED")
        if action=="PREPARE":self.states.setdefault(key,"ESCROWED");return {"verdict":"PENDING","evidence":None}
        if action=="UNAVAILABLE":return {"verdict":"HOLD","evidence":None}
        target={"COMMIT":"CONFIRMED_SUCCESS","ABORT":"CONFIRMED_ABORTED"}.get(action)
        if not target:raise Reject("ESCROW_ACTION")
        if old in ("CONFIRMED_SUCCESS","CONFIRMED_ABORTED") and old!=target:self.conflicts+=1;raise Reject("CONFLICTING_TERMINAL")
        self.states[key]=target;self.receipts.setdefault(key,evidence(r,target));return {"verdict":target,"evidence":self.receipts[key]}
class Fenced:
    def __init__(self,generation=2):self.current=generation;self.effects=set();self.stale_rejects=0
    def execute(self,r):
        check(r);g=r.get("fence_generation")
        if g!=self.current:self.stale_rejects+=1;return {"verdict":"CONFIRMED_NO_EFFECT","evidence":evidence(r,"CONFIRMED_NO_EFFECT")}
        self.effects.add(r["semantic_effect_id"]);return {"verdict":"CONFIRMED_SUCCESS","evidence":evidence(r,"CONFIRMED_SUCCESS")}
class Unobservable:
    def __init__(self):self.success_count=0;self.output_activations=0;self.overlap=0;self.fabricated_receipts=0
    def execute(self,r):check(r);return {"verdict":"RECOVERY_HOLD","evidence":None}
