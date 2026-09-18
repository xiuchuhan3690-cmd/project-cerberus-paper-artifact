"""Durable local XREC: slot consumption and output activation share one record."""
from __future__ import annotations
import hashlib,os,threading
from pathlib import Path
from nlc.m6.t1.canonical import decode,encode
from nlc.m6.t1.constructor import construct_outputs
from nlc.m6.t1.fixtures import baseline
from nlc.m6.t2.adapters import Escrowed,Fenced,Idempotent,Unobservable,request

VERSION="NLC-XREC-PROTOCOL/1.0";RECEIPT_VERSION="NLC-XREC-RECEIPT/1.0"
SLOT="a652b78970d170b8dacc6044854c150a3e7ca2a54d5ece015c95ade0396fe765"
OUTPUT="a41a693cf18e91258de6e13fdc67c9184961264d7a08577b0e3e1d1c64d8aaba"
ROOT="d38cab52600953a65aadebf1eb61bbc925d4957e1d8dfcb175eb2e6705affb3b"
CUTOVER_RECEIPT="1bce312db818a2f1c9ddf63297ebe54f4738fa8ee1e038d441c25731ae85500c"
STATES=("NEW","CHECKPOINT_VERIFIED","EFFECT_VERIFIED","PREPARED","COMMITTED","HOLD","ABORTED")
BOUNDARIES=("before_checkpoint","after_checkpoint","before_effect","after_effect","before_prepare","after_prepare","before_slot_consumption","after_slot_consumption","before_output_activation","after_output_activation","before_receipt","after_receipt","before_ack","after_ack")
class XReject(ValueError):pass
def digest(tag,v):return hashlib.sha256(tag+encode(v)).hexdigest()
def make_receipt(adapter,evidence,checkpoint):
 core={"receipt_version":RECEIPT_VERSION,"protocol_version":VERSION,"recovery_slot_id":SLOT,"checkpoint_commitment":checkpoint,"effect_scope_id":"effect-scope:synthetic-ledger:v1","adapter_class":adapter,"adapter_version":f"NLC-{adapter}-ADAPTER/1.0","settlement_evidence_commitment":evidence["evidence_commitment"],"active_root_id":ROOT,"cutover_receipt_id":CUTOVER_RECEIPT,"output_set_id":OUTPUT,"target_domain":"D_1","target_epoch":1,"terminal_state":"COMMITTED"}
 return {**core,"receipt_id":digest(b"NLC-XREC-RECEIPT/1.0\0",core)}
class Store:
 def __init__(self,path):self.path=Path(path);self.lock=threading.RLock()
 def read(self):return decode(self.path.read_bytes()) if self.path.exists() else None
 def write(self,value):
  temp=self.path.with_suffix(".tmp");temp.write_bytes(encode(value));os.replace(temp,self.path)
 def commit(self,record):
  with self.lock:
   old=self.read()
   if old and old.get("state")=="COMMITTED":
    if old!=record:raise XReject("DISTINCT_COMMIT_FOR_SLOT")
    return old,True
   self.write(record);return record,False
class XREC:
 def __init__(self,path):self.store=Store(path)
 def run(self,adapter="IDEMPOTENT",fault=None,escrow_action="COMMIT",fence_generation=2):
  old=self.store.read()
  if old and old.get("state")=="COMMITTED":return {"verdict":"COMMITTED","receipt":old["receipt"],"retrieval":True}
  material,templates=baseline();normalized,slot_id,outputs,_=construct_outputs(material,templates)
  if slot_id!=SLOT or outputs["output_set_id"]!=OUTPUT:raise XReject("FROZEN_T1_BINDING")
  if fault in BOUNDARIES[:3]:return self._hold("CRASH_BEFORE_EFFECT")
  r=request(adapter)
  if adapter=="IDEMPOTENT":effect=Idempotent().execute(r)
  elif adapter=="ESCROWED":effect=Escrowed().execute(dict(r,escrow_action=escrow_action))
  elif adapter=="FENCED":effect=Fenced().execute(dict(r,fence_generation=fence_generation))
  else:effect=Unobservable().execute(r)
  if effect["verdict"]!="CONFIRMED_SUCCESS" or not effect.get("evidence"):return self._hold("EFFECT_NOT_CONFIRMED")
  if fault in BOUNDARIES[3:7]:
   if fault=="after_prepare":self.store.write({"protocol_version":VERSION,"state":"PREPARED","recovery_slot_id":SLOT})
   return self._hold("CRASH_BEFORE_ATOMIC_COMMIT",persist=False)
  receipt=make_receipt(adapter,effect["evidence"],normalized["checkpoint_commitment"])
  record={"protocol_version":VERSION,"state":"COMMITTED","recovery_slot_id":SLOT,"slot_state":"CONSUMED","output_state":"ACTIVE","output_set_id":OUTPUT,"output_activation_count":1,"effective_effect_count":1,"old_capability_reissue_count":0,"old_authority_parent_edges":0,"receipt":receipt}
  committed,retrieval=self.store.commit(record)
  return {"verdict":"COMMITTED","receipt":committed["receipt"],"retrieval":retrieval or fault in BOUNDARIES[7:]}
 def _hold(self,reason,persist=False):return {"verdict":"HOLD","reason":reason,"output_activation_count":0,"slot_consumed":False}
