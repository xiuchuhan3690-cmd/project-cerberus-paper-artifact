"""NLC_Integrator_v1: routing and append evidence only, with no acceptance policy."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
VERSION="NLC_Integrator_v1";EVENT_VERSION="NLC-INTEGRATION-EVENT/1.0";LEDGER_VERSION="NLC-INTEGRATION-EVIDENCE-LEDGER/1.0"
DISPOSITIONS={"CONTINUE","STOP_REJECT","STOP_HOLD","STOP_KILL_SWITCH","COMPONENT_UNAVAILABLE","EVIDENCE_INVALID"}
ACCEPTABLE={"PASS","ACCEPT","ADMIT","ELIGIBLE","COMMITTED","VERIFIED_ADMIT"}
BINDINGS={
 "NTBA":("NTBA-M1/1.0","manifests/NTBA_M1_T3_Verification_Rules_v1.json","NTBA_INDEPENDENT_VERIFIER"),
 "AIM":("CERBERUS-AIM-FROZEN/1.0","vectors/NLC_M7_T1_AIM_Evidence_v1.json","AIM-INDEPENDENT-VERIFIER/1.0"),
 "STERILE":("NLC-M3-STERILITY-ARTIFACT-FOR-M5/1.0","vectors/NLC_M7_T1_Sterility_Evidence_v1.json","M3-INDEPENDENT-STERILITY"),
 "ROOT_ACCEPT":("NLC-ROOT-ACCEPT-VERIFIER/1.0","nlc/m5/t1/verifier.py","NLC-ROOT-ACCEPT-VERIFIER/1.0"),
 "CUTOVER":("NLC-CUTOVER-SLOT/1.0","nlc/m5/t3/verifier.py","NLC-M5-T3-INDEPENDENT"),
 "EPOCH_BARRIER":("NLC-EPOCH-BARRIER-SUITE/1.0","nlc/m5/t4/verifier.py","NLC-M5-T4-INDEPENDENT"),
 "RECOVERY_SLOT":("NLC-RECOVERY-SLOT/1.0","nlc/m6/t1/verifier.py","NLC-M6-T1-INDEPENDENT"),
 "EFFECT_ADAPTER":("NLC-EFFECT-ADAPTERS/1.0","nlc/m6/t2/verifier.py","NLC-M6-T2-INDEPENDENT"),
 "XREC":("NLC-XREC-PROTOCOL/1.0","nlc/m6/t3/verifier.py","NLC-M6-T3-INDEPENDENT"),
 "LINEAGE":("XREC_Lineage_Verifier_v1","nlc/m6/t4/verifier.py","XREC_Lineage_Verifier_v1"),
 "SRA_FIXTURE":("SRA_Fixture_v1","nlc/m7/t1/verifier.py","NLC-M7-T1-INDEPENDENT"),
}
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def h(tag,v):return hashlib.sha256(tag+canon(v)).hexdigest()
def registry(root:Path):
 def file_sha(p):return hashlib.sha256((root/p).read_bytes()).hexdigest()
 rows=[(c,*binding) for c,binding in BINDINGS.items()]
 return [{"component_id":c,"version":v,"artifact_path":p,"artifact_sha256":file_sha(p),"verifier_id":q,"role":"FROZEN_COMPONENT","status":"BOUND"} for c,v,p,q in rows]
class Ledger:
 def __init__(self,session):self.session=session;self.events=[];self.ids=set()
 def append(self,event_type,component,version,input_commitment,output_commitment,verifier,verdict,reason,disposition,epistemic="OBSERVED"):
  seq=len(self.events);parent="GENESIS" if not self.events else self.events[-1]["event_id"]
  core={"event_version":EVENT_VERSION,"session_id":self.session,"sequence":seq,"event_type":event_type,"component_id":component,"component_version":version,"input_commitment":input_commitment,"output_receipt_commitment":output_commitment,"verifier_id":verifier,"verifier_version":verifier,"verifier_verdict":verdict,"original_reason_code":reason,"normalized_routing_disposition":disposition,"preceding_event_commitment":parent,"epistemic_status":epistemic}
  event={**core,"event_id":h(b"NLC-INTEGRATION-EVENT/1.0\0",core)}
  if event["event_id"] in self.ids:raise ValueError("DUPLICATE_EVENT")
  self.events.append(event);self.ids.add(event["event_id"]);return event
def normalize(proposer,independent):
 if proposer in {"REJECT","EXCLUDED"} or independent=="REJECT":return "STOP_REJECT"
 if proposer in {"HOLD","QUARANTINED","RECOVERY_HOLD"} or independent=="HOLD":return "STOP_HOLD"
 if proposer in ACCEPTABLE and independent in ACCEPTABLE:return "CONTINUE"
 return "EVIDENCE_INVALID"
def run_session(session_id,steps,kill_at=-1):
 ledger=Ledger(session_id);zero="0"*64
 ledger.append("ORCHESTRATION_SESSION_START","INTEGRATOR",VERSION,h(b"session\0",{"id":session_id}),zero,"NONE","START","SESSION_START","CONTINUE")
 terminal="CONTINUE";invoked=[]
 for index,step in enumerate(steps):
  if kill_at==index:
   ledger.append("KILL_SWITCH_ENGAGED","INTEGRATOR",VERSION,zero,zero,"M0_KILL_SWITCH","ENGAGED","KILL_SWITCH","STOP_KILL_SWITCH");terminal="STOP_KILL_SWITCH";break
  c,v=step["component_id"],step["version"];inp=step["input_commitment"]
  if c not in BINDINGS:
   ledger.append("EVIDENCE_VALIDATION_FAILURE","INTEGRATOR",VERSION,inp,zero,"REGISTRY","REJECT","UNKNOWN_COMPONENT:"+c,"STOP_REJECT");terminal="STOP_REJECT";break
  if (v,step["verifier_id"])!=(BINDINGS[c][0],BINDINGS[c][2]):
   ledger.append("EVIDENCE_VALIDATION_FAILURE","INTEGRATOR",VERSION,inp,zero,"REGISTRY","REJECT","FROZEN_BINDING_MISMATCH:"+c,"EVIDENCE_INVALID");terminal="EVIDENCE_INVALID";break
  ledger.append("COMPONENT_INVOCATION",c,v,inp,zero,step["verifier_id"],"PENDING","INVOCATION", "CONTINUE");invoked.append(c)
  if step.get("unavailable"):
   ledger.append("COMPONENT_UNAVAILABLE",c,v,inp,zero,step["verifier_id"],"UNAVAILABLE","COMPONENT_UNAVAILABLE","COMPONENT_UNAVAILABLE");terminal="COMPONENT_UNAVAILABLE";break
  if step.get("invalid_receipt"):
   ledger.append("EVIDENCE_VALIDATION_FAILURE",c,v,inp,step["receipt_commitment"],step["verifier_id"],"REJECT","RECEIPT_COMMITMENT_MISMATCH","EVIDENCE_INVALID");terminal="EVIDENCE_INVALID";break
  disp=normalize(step["proposer_verdict"],step["independent_verdict"])
  ledger.append("VERIFIER_VERDICT",c,v,inp,step["receipt_commitment"],step["verifier_id"],step["independent_verdict"],step["reason"],disp)
  ledger.append("ROUTING_DECISION",c,v,inp,step["receipt_commitment"],step["verifier_id"],step["independent_verdict"],step["reason"],disp)
  if disp!="CONTINUE":
   kind="HOLD_PROPAGATION" if disp=="STOP_HOLD" else "REJECT_PROPAGATION" if disp=="STOP_REJECT" else "EVIDENCE_VALIDATION_FAILURE"
   ledger.append(kind,c,v,inp,step["receipt_commitment"],step["verifier_id"],step["independent_verdict"],step["reason"],disp);terminal=disp;break
 ledger.append("ORCHESTRATION_TERMINAL","INTEGRATOR",VERSION,zero,h(b"terminal\0",{"session":session_id,"disposition":terminal}),"NONE",terminal,"TERMINAL",terminal)
 return {"session_version":"NLC-INTEGRATION-SESSION/1.0","session_id":session_id,"events":ledger.events,"terminal_disposition":terminal,"invoked_components":invoked,"kill_switch_engaged":kill_at>=0 and terminal=="STOP_KILL_SWITCH"}
def step(component,version,verifier,verdict="PASS",independent="PASS",reason="VERIFIED",**kw):
 inp=h(b"input\0",{"component":component,"case":kw.get("case","baseline")});receipt=h(b"receipt\0",{"component":component,"verdict":verdict,"reason":reason})
 return {"component_id":component,"version":version,"verifier_id":verifier,"input_commitment":inp,"receipt_commitment":receipt,"proposer_verdict":verdict,"independent_verdict":independent,"reason":reason,**kw}
