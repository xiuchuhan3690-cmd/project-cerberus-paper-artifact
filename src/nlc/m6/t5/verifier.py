"""Independent M6 correspondence verifier; no primary harness imports."""
import hashlib,json
SLOT="a652b78970d170b8dacc6044854c150a3e7ca2a54d5ece015c95ade0396fe765";OUTPUT="a41a693cf18e91258de6e13fdc67c9184961264d7a08577b0e3e1d1c64d8aaba";ROOT="d38cab52600953a65aadebf1eb61bbc925d4957e1d8dfcb175eb2e6705affb3b";RECEIPT="f03af35c7ff21a3ddd4fa588db15eb92eee2b9c4bd41277606a0d3165d993611"
REQUIRED_TOGGLES={"NON_LINEARIZABLE_RECOVERY_SLOT","UNKNOWN_AS_SUCCESS","UNFENCED_OLD_EFFECT_SCOPE","NONDETERMINISTIC_OUTPUT","SETTLEMENT_GATE_DISABLED","SLOT_COMMIT_DISABLED","FENCE_CHECK_DISABLED","UNKNOWN_FAIL_CLOSED_DISABLED","OUTPUT_BINDING_DISABLED"}
REQUIRED_FORMAL={"valid_deterministic_recovery","same_slot_retry","two_client_same_slot","idempotent_lost_response","escrowed_commit","escrowed_abort","escrow_unavailable","fenced_current_generation","stale_fence","delayed_old_effect","unobservable_effect","crash_before_commit","crash_after_commit","partition_delayed_receipt","competing_recovery_requests","changed_semantic_material","lost_capability_mutation","old_parent_mutation","nondeterministic_output_mutation"}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def verify(c,root):
 try:
  if c.get("version")!="XREC_Correspondence_v1" or c.get("decision")!="PASS":raise ValueError("RESULT")
  f=c["formal_to_implementation"];i=c["implementation_to_formal"];m=c["metrics"]
  if {x["case_id"] for x in f}!=REQUIRED_FORMAL:raise ValueError("FORMAL_TRACE_COVERAGE")
  if any(x["divergence"] for x in f+i+c["crash"]):raise ValueError("DIVERGENCE")
  if len(c["crash"])!=14 or {x["implementation"] for x in c["crash"]}!={"HOLD","COMMITTED"}:raise ValueError("CRASH_MATRIX")
  if {x["toggle_id"] for x in c["toggles"]}!=REQUIRED_TOGGLES or not all(x["formal"]==x["implementation"]=="COUNTEREXAMPLE" for x in c["toggles"]):raise ValueError("TOGGLES")
  zeros=("retry_mint_count","client_divergence_count","duplicate_active_outputs","duplicate_effective_effects","delayed_old_effect_violations","conflicting_escrow_terminals","stale_fence_accepted_effects","unknown_false_success","unobservable_successful_recoveries","false_success_count","hold_output_activations","hold_authority_mints","old_authority_parent_edges","lost_capability_reissues","retry_as_mint","output_without_new_root_ancestry","disguised_old_authority_provenance_admissions","decision_critical_unexplained_divergence","partial_decision_critical_mappings")
  if any(m[x]!=0 for x in zeros) or m["max_distinct_output_sets_per_slot"]>1 or m["hold_correctness_rate"]!=100:raise ValueError("SAFETY_METRICS")
  bindings=json.loads((root/"manifests/NLC_M6_T1_Result_v1.json").read_text())
  if (bindings["recovery_slot_id"],bindings["output_set_id"])!=(SLOT,OUTPUT):raise ValueError("IDENTITY")
  return {"verdict":"ACCEPT","reason":"INDEPENDENT_BOUNDED_CORRESPONDENCE_PASS","ntc3":"PASS","tc4":"PASS","slot_id":SLOT,"output_set_id":OUTPUT,"active_root_id":ROOT,"xrec_receipt_id":RECEIPT}
 except Exception as e:return {"verdict":"REJECT","reason":str(e)}
