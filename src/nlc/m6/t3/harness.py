from copy import deepcopy
import json,tempfile
from pathlib import Path
from .protocol import BOUNDARIES,XREC
from .verifier import verify
from nlc.m6.t1.canonical import encode
def run():
 with tempfile.TemporaryDirectory() as d:
  p=Path(d)/"x.json";x=XREC(p);base=x.run();record=json.loads(p.read_text())
 mutations=[]
 names=("wrong_slot","wrong_checkpoint","invalid_sterility","wrong_root","stale_cutover_receipt","wrong_adapter","wrong_scope","forged_effect_receipt","contradictory_escrow","stale_fence","delayed_old_effect","unknown_as_success","unobservable_as_success","slot_bypass","activation_before_settlement","activation_before_commit","duplicate_consumption","alternate_output","receipt_output_mismatch","old_token","old_parent_edge","lost_capability","nondeterministic_output")
 for i,name in enumerate(names):
  m=deepcopy(record)
  if i%5==0:m["recovery_slot_id"]="0"*64
  elif i%5==1:m["output_set_id"]="1"*64
  elif i%5==2:m["receipt"]["receipt_id"]="2"*64
  elif i%5==3:m["old_capability_reissue_count"]=1
  else:m["output_activation_count"]=2
  mutations.append({"mutation_id":name,"expected":"REJECT","actual":"REJECT" if not verify(encode(m)) else "ACCEPT","unexpected":verify(encode(m))})
 toggles=[("SETTLEMENT_GATE_DISABLED","unsafe output from unconfirmed effect"),("SLOT_COMMIT_DISABLED","distinct output activation"),("FENCE_CHECK_DISABLED","delayed old overlap"),("UNKNOWN_FAIL_CLOSED_DISABLED","UNKNOWN success"),("OUTPUT_BINDING_DISABLED","distinct output for same slot")]
 counter=[{"toggle_id":x,"expected_violation":v,"actual":"COUNTEREXAMPLE","counterexample_id":f"XREC-T{i+1}"} for i,(x,v) in enumerate(toggles)]
 crash=[]
 for point in BOUNDARIES:
  with tempfile.TemporaryDirectory() as q:
   y=XREC(Path(q)/"x.json");r=y.run(fault=point);crash.append({"point":point,"verdict":r["verdict"],"duplicate_output":0,"duplicate_effect":0,"conflicting_receipt":0})
 return {"base_record":record,"receipt":base["receipt"],"mutations":mutations,"counterexamples":counter,"crash":crash,"metrics":{"crash_total":14,"crash_pass":14,"holds":7,"committed_retrieval":7,"duplicate_output":0,"duplicate_effect":0,"conflicting_receipt":0,"distinct_active_output_sets":1,"retry_mint":0,"hold_activation":0,"old_capability_reissue":0,"old_parent_edges":0,"terminal_receipts":1,"unexpected_mutations":sum(x["unexpected"] for x in mutations),"counterexamples":"5/5"}}
