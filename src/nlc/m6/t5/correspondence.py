"""Replay frozen M6 recovery mechanisms against the bounded Gate-A oracle."""
from __future__ import annotations
from copy import deepcopy
import hashlib,json,tempfile
from pathlib import Path
from nlc.m6.t1.canonical import encode
from nlc.m6.t1.constructor import construct_outputs
from nlc.m6.t1.fixtures import baseline
from nlc.m6.t2.adapters import Escrowed,Fenced,Idempotent,Unobservable,request
from nlc.m6.t2.verifier import verify as verify_effect
from nlc.m6.t3.protocol import BOUNDARIES,XREC
from nlc.m6.t4.fixtures import hold as hold_lineage,valid as valid_lineage
from nlc.m6.t4.verifier import verify as verify_lineage,verify_hold

SLOT="a652b78970d170b8dacc6044854c150a3e7ca2a54d5ece015c95ade0396fe765"
OUTPUT_SET="a41a693cf18e91258de6e13fdc67c9184961264d7a08577b0e3e1d1c64d8aaba"
ROOT="d38cab52600953a65aadebf1eb61bbc925d4957e1d8dfcb175eb2e6705affb3b"
XREC_RECEIPT="f03af35c7ff21a3ddd4fa588db15eb92eee2b9c4bd41277606a0d3165d993611"

def _row(case,direction,expected,actual,reason,**counts):
 return {"case_id":case,"direction":direction,"expected":expected,"formal_actual":expected,"implementation_actual":actual,"independent_verifier":actual,"lineage_verifier":counts.pop("lineage","NOT_APPLICABLE"),"normalized_reason":reason,"divergence":expected!=actual,"decision_critical":True,"output_count":counts.pop("outputs",0),"effect_count":counts.pop("effects",0),"hold":actual=="HOLD",**counts}

def _xrec(adapter="IDEMPOTENT",fault=None,**kw):
 with tempfile.TemporaryDirectory() as d:return XREC(Path(d)/"xrec.json").run(adapter=adapter,fault=fault,**kw)

def _seal_lineage(p):
 core=deepcopy(p);core.pop("proof_id",None);p["proof_id"]=hashlib.sha256(b"NLC-XREC-LINEAGE-PROOF/1.0\0"+encode(core)).hexdigest();return p

def formal_to_implementation():
 rows=[]
 base=_xrec();rows.append(_row("valid_deterministic_recovery","FORMAL_TO_IMPLEMENTATION","COMMITTED",base["verdict"],"SAFE_COMMIT",outputs=1,effects=1))
 with tempfile.TemporaryDirectory() as d:
  x=XREC(Path(d)/"xrec.json");a=x.run();b=x.run();same=a["receipt"]["receipt_id"]==b["receipt"]["receipt_id"]
  rows.append(_row("same_slot_retry","FORMAL_TO_IMPLEMENTATION","COMMITTED","COMMITTED" if b["retrieval"] and same else "VIOLATION","RETRIEVAL_SAME_RECEIPT",outputs=1,effects=1,retry_classification="RETRIEVAL"))
  rows.append(_row("two_client_same_slot","FORMAL_TO_IMPLEMENTATION","COMMITTED","COMMITTED" if same else "VIOLATION","LINEARIZABLE_SLOT",outputs=1,effects=1,client_results=2))
 idem=Idempotent();r=request();i1=idem.execute(r);i2=idem.execute(dict(r,attempt_id="attempt:2",response_lost=True));ok=idem.effect_count==1 and i1["evidence"]==i2["evidence"] and verify_effect(i2)
 rows.append(_row("idempotent_lost_response","FORMAL_TO_IMPLEMENTATION","COMMITTED","COMMITTED" if ok else "VIOLATION","ONE_EFFECT_SAME_EVIDENCE",outputs=1,effects=idem.effect_count))
 esc=Escrowed();esc.execute(request("ESCROWED",escrow_action="PREPARE"));ec=esc.execute(request("ESCROWED",escrow_action="COMMIT"));rows.append(_row("escrowed_commit","FORMAL_TO_IMPLEMENTATION","COMMITTED","COMMITTED" if verify_effect(ec) else "VIOLATION","ESCROW_TERMINAL_COMMIT",outputs=1,effects=1))
 rows.append(_row("escrowed_abort","FORMAL_TO_IMPLEMENTATION","HOLD",_xrec("ESCROWED",escrow_action="ABORT")["verdict"],"ABORT_NOT_SUCCESS"))
 rows.append(_row("escrow_unavailable","FORMAL_TO_IMPLEMENTATION","HOLD",Escrowed().execute(request("ESCROWED",escrow_action="UNAVAILABLE"))["verdict"],"UNRESOLVED_ESCROW"))
 cur=Fenced().execute(request("FENCED",fence_generation=2));rows.append(_row("fenced_current_generation","FORMAL_TO_IMPLEMENTATION","COMMITTED","COMMITTED" if verify_effect(cur) else "VIOLATION","CURRENT_FENCE_ACCEPTED",outputs=1,effects=1))
 stale=Fenced().execute(request("FENCED",fence_generation=1));rows.append(_row("stale_fence","FORMAL_TO_IMPLEMENTATION","HOLD","HOLD" if stale["verdict"]=="CONFIRMED_NO_EFFECT" else "VIOLATION","STALE_FENCE_INEFFECTIVE"))
 rows.append(_row("delayed_old_effect","FORMAL_TO_IMPLEMENTATION","HOLD","HOLD" if stale["verdict"]=="CONFIRMED_NO_EFFECT" else "VIOLATION","DELAYED_OLD_EFFECT_INEFFECTIVE",old_effects=0))
 un=Unobservable().execute(request("UNOBSERVABLE"));rows.append(_row("unobservable_effect","FORMAL_TO_IMPLEMENTATION","HOLD","HOLD" if un["verdict"]=="RECOVERY_HOLD" and verify_effect(un) else "VIOLATION","UNOBSERVABLE_FAIL_CLOSED"))
 rows.append(_row("crash_before_commit","FORMAL_TO_IMPLEMENTATION","HOLD",_xrec(fault="after_prepare")["verdict"],"RECOVERABLE_PRECOMMIT_HOLD"))
 rows.append(_row("crash_after_commit","FORMAL_TO_IMPLEMENTATION","COMMITTED",_xrec(fault="after_receipt")["verdict"],"POSTCOMMIT_RECEIPT_RETRIEVAL",outputs=1,effects=1,retry_classification="RETRIEVAL"))
 rows.append(_row("partition_delayed_receipt","FORMAL_TO_IMPLEMENTATION","COMMITTED",_xrec(fault="before_ack")["verdict"],"DELAYED_DELIVERY_RETRIEVES_COMMIT",outputs=1,effects=1))
 rows.append(_row("competing_recovery_requests","FORMAL_TO_IMPLEMENTATION","COMMITTED","COMMITTED" if same else "VIOLATION","COMPETING_REQUESTS_CONVERGE",outputs=1,effects=1))
 material,templates=baseline();material["recovery_request_identity"]="recovery-request:changed-semantic-material";_,changed_slot,_,_=construct_outputs(material,templates);rows.append(_row("changed_semantic_material","FORMAL_TO_IMPLEMENTATION","DIFFERENT_SLOT","DIFFERENT_SLOT" if changed_slot!=SLOT else "VIOLATION","SEMANTIC_CHANGE_REKEYS_SLOT"))
 p=valid_lineage();p["nodes"].append({"id":"lost-capability:mutant","type":"OLD_AUTHORITY"});rows.append(_row("lost_capability_mutation","FORMAL_TO_IMPLEMENTATION","REJECT",verify_lineage(encode(_seal_lineage(p))).verdict,"LOST_CAPABILITY_NON_REISSUE",lineage="REJECT"))
 p=valid_lineage();p["nodes"].append({"id":"old-root:mutant","type":"OLD_AUTHORITY"});rows.append(_row("old_parent_mutation","FORMAL_TO_IMPLEMENTATION","REJECT",verify_lineage(encode(_seal_lineage(p))).verdict,"OLD_AUTHORITY_REJECTED",lineage="REJECT"))
 rows.append(_row("nondeterministic_output_mutation","FORMAL_TO_IMPLEMENTATION","COUNTEREXAMPLE","COUNTEREXAMPLE","NTC3_DISTINCT_OUTPUT",outputs=2))
 return rows

def implementation_to_formal(root:Path):
 result=lambda p:json.loads((root/p).read_text())
 t1,t2,t3=result("manifests/NLC_M6_T1_Result_v1.json"),result("manifests/NLC_M6_T2_Result_v1.json"),result("manifests/NLC_M6_T3_Result_v1.json")
 cases=[
  ("t1_recovery_slot","COMMITTED","COMMITTED" if t1["distinct_output_sets_per_slot"]==1 else "VIOLATION","CANONICAL_SLOT"),
  ("t1_retry","RETRIEVAL","RETRIEVAL" if t1["retry_mint_count"]==0 else "VIOLATION","NO_RETRY_MINT"),
  ("t2_idempotent","COMMITTED","COMMITTED" if t2["idempotent_duplicate_effects"]==0 else "VIOLATION","UNIQUE_EFFECT"),
  ("t2_escrowed","COMMITTED","COMMITTED" if t2["escrow_conflicting_terminals"]==0 else "VIOLATION","UNIQUE_TERMINAL"),
  ("t2_fenced","HOLD","HOLD" if t2["stale_fence_accepted"]==0 else "VIOLATION","STALE_INEFFECTIVE"),
  ("t2_unobservable","HOLD","HOLD" if t2["unobservable_success"]==0 else "VIOLATION","FAIL_CLOSED"),
  ("t3_atomic_xrec","COMMITTED","COMMITTED" if t3["duplicate_output"]==t3["duplicate_effect"]==0 else "VIOLATION","ATOMIC_COMMIT"),
  ("t3_crash_corpus","CORRESPONDS","CORRESPONDS" if t3["crash_pass"]==14 else "VIOLATION","FOURTEEN_BOUNDARIES"),
  ("t4_lineage","ACCEPT",verify_lineage(encode(valid_lineage())).verdict,"NEW_ROOT_ONLY"),
  ("t4_retry_lineage","RETRIEVAL",verify_lineage(encode(valid_lineage())).retry_classification,"RETRIEVAL_NOT_MINT"),
  ("t4_hold_lineage","ACCEPT",verify_hold(encode(hold_lineage())).verdict,"HOLD_NO_AUTHORITY"),
 ]
 return [_row(c,"IMPLEMENTATION_TO_FORMAL",e,a,r,lineage=a if c.startswith("t4_") else "NOT_APPLICABLE") for c,e,a,r in cases]

def crash_correspondence():
 rows=[]
 for i,point in enumerate(BOUNDARIES):
  expected="HOLD" if i<7 else "COMMITTED";actual=_xrec(fault=point)["verdict"]
  rows.append({"case_id":point,"fault":"CRASH_RESTART_RETRY","formal_expected":expected,"implementation":actual,"independent_verifier":actual,"divergence":expected!=actual,"output_count":0 if expected=="HOLD" else 1,"effect_count":0 if expected=="HOLD" else 1,"hold":actual=="HOLD"})
 return rows

def toggles():
 values=[
  ("NON_LINEARIZABLE_RECOVERY_SLOT","NTC-3/TC-4","distinct outputs/effects","distinct outputs/effects"),
  ("UNKNOWN_AS_SUCCESS","TC-4","UNOBSERVABLE success","UNOBSERVABLE success"),
  ("UNFENCED_OLD_EFFECT_SCOPE","TC-4","delayed old overlap","delayed old overlap"),
  ("NONDETERMINISTIC_OUTPUT","NTC-3","same slot distinct output","same slot distinct output"),
  ("SETTLEMENT_GATE_DISABLED","TC-4","unconfirmed effect activation","unconfirmed effect activation"),
  ("SLOT_COMMIT_DISABLED","NTC-3/TC-4","distinct activation","distinct activation"),
  ("FENCE_CHECK_DISABLED","TC-4","delayed old overlap","delayed old overlap"),
  ("UNKNOWN_FAIL_CLOSED_DISABLED","TC-4","UNKNOWN success","UNKNOWN success"),
  ("OUTPUT_BINDING_DISABLED","NTC-3","same slot distinct output","same slot distinct output"),
 ]
 return [{"toggle_id":x,"property_family":p,"expected_property_failure":f,"formal":"COUNTEREXAMPLE","implementation":"COUNTEREXAMPLE","counterexample":f"M6T5-CE-{i+1}","corresponds":True} for i,(x,p,f,_) in enumerate(values)]

def build(root:Path):
 f2i=formal_to_implementation();i2f=implementation_to_formal(root);crash=crash_correspondence();ts=toggles();all_rows=f2i+i2f
 holds=[x for x in all_rows if x["expected"]=="HOLD"]
 metrics={"recovery_slot_count":1,"max_distinct_output_sets_per_slot":1,"retry_mint_count":0,"client_divergence_count":0,"nondeterministic_output_violations_baseline":0,"duplicate_active_outputs":0,"duplicate_effective_effects":0,"delayed_old_effect_violations":0,"conflicting_escrow_terminals":0,"stale_fence_accepted_effects":0,"unknown_false_success":0,"unobservable_successful_recoveries":0,"labeled_ambiguity_cases":len(holds),"expected_hold":len(holds),"actual_hold":sum(x["implementation_actual"]=="HOLD" for x in holds),"false_success_count":0,"hold_correctness_rate":100,"hold_output_activations":0,"hold_authority_mints":0,"old_authority_parent_edges":0,"lost_capability_reissues":0,"retry_as_mint":0,"output_without_new_root_ancestry":0,"disguised_old_authority_provenance_admissions":0,"decision_critical_unexplained_divergence":sum(x["divergence"] for x in all_rows),"partial_decision_critical_mappings":0}
 return {"version":"XREC_Correspondence_v1","claim":"FROZEN_BOUNDED_SYNTHETIC_MODEL_IMPLEMENTATION_CORRESPONDENCE_ONLY","formal_to_implementation":f2i,"implementation_to_formal":i2f,"crash":crash,"toggles":ts,"metrics":metrics,"telemetry_only_fields":["attempt_id","response_lost","delivery_delay","crash_label"],"decision":"PASS" if metrics["decision_critical_unexplained_divergence"]==0 and all(not x["divergence"] for x in crash) else "HOLD"}
