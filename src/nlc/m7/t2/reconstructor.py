"""Independent evidence-only reconstruction; imports no integrator."""
import hashlib,json
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def reconstruct(events):
 try:
  rows=sorted(events,key=lambda x:x["sequence"]);ids=set();invoked=[];verified=[];routes=[];kill=False;terminal=None
  for i,e in enumerate(rows):
   if e["sequence"]!=i:raise ValueError("MISSING_SEQUENCE")
   core={k:e[k] for k in e if k!="event_id"};want=hashlib.sha256(b"NLC-INTEGRATION-EVENT/1.0\0"+canon(core)).hexdigest()
   if e["event_id"]!=want or e["event_id"] in ids:raise ValueError("EVENT_ID_OR_REPLAY")
   if e["preceding_event_commitment"]!=("GENESIS" if i==0 else rows[i-1]["event_id"]):raise ValueError("PREDECESSOR")
   ids.add(e["event_id"])
   if e["event_type"]=="COMPONENT_INVOCATION":invoked.append(e["component_id"])
   if e["event_type"]=="VERIFIER_VERDICT":verified.append(e["component_id"])
   if e["event_type"]=="ROUTING_DECISION":routes.append(e["normalized_routing_disposition"])
   if e["event_type"]=="KILL_SWITCH_ENGAGED":kill=True
   if e["event_type"]=="ORCHESTRATION_TERMINAL":terminal=e["normalized_routing_disposition"]
  bypass=[c for c in invoked if c not in verified and terminal not in {"COMPONENT_UNAVAILABLE","EVIDENCE_INVALID","STOP_KILL_SWITCH"}]
  overrides=sum(e["verifier_verdict"] in {"HOLD","REJECT"} and e["normalized_routing_disposition"]=="CONTINUE" for e in rows)
  return {"verdict":"ACCEPT" if terminal and not bypass and not overrides else "REJECT","terminal":terminal,"invoked":invoked,"verified":verified,"routes":routes,"kill_switch":kill,"override_count":overrides,"bypass_components":bypass,"event_count":len(rows)}
 except Exception as e:return {"verdict":"REJECT","reason":str(e)}
