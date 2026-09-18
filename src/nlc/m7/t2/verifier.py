"""Independent integration validator; imports no coordinator or runtime state."""
from .reconstructor import reconstruct
REQUIRED={"NTBA","AIM","STERILE","ROOT_ACCEPT","CUTOVER","EPOCH_BARRIER","RECOVERY_SLOT","EFFECT_ADAPTER","XREC","LINEAGE","SRA_FIXTURE"}
PROHIBITED={"RAW_CANDIDATE_TO_ROOT_ACCEPT","RAW_CHECKPOINT_TO_XREC","UNVERIFIED_EFFECT_TO_XREC_COMMIT","EXCLUDED_CANDIDATE_TO_CBR","OLD_AUTHORITY_TO_NEW_NTBA","ORCHESTRATOR_PASS_TO_COMPONENT_ACCEPTANCE","AIM_BYPASS","STERILITY_BYPASS","LINEAGE_BYPASS"}
def verify(deployment,sessions,mutations):
 try:
  reg=deployment["component_registry"]
  if deployment["integrator_version"]!="NLC_Integrator_v1" or {x["component_id"] for x in reg}!=REQUIRED:raise ValueError("REGISTRY")
  bindings={x["component_id"]:(x["version"],x["verifier_id"]) for x in reg}
  if len(deployment["allowed_interface_graph"])<7 or not PROHIBITED.issubset(deployment["prohibited_bypass_edges"]):raise ValueError("GRAPH")
  if deployment["shared_mutable_authority_state"]!=[] or deployment["claim_class"]!="SUPPORTING":raise ValueError("BOUNDARY")
  for session in sessions:
   for event in session["events"]:
    component=event["component_id"]
    if component not in REQUIRED|{"INTEGRATOR"}:raise ValueError("UNKNOWN_COMPONENT")
    if component in REQUIRED and (event["component_version"],event["verifier_id"])!=bindings[component]:raise ValueError("BINDING")
  results=[reconstruct(x["events"]) for x in sessions]
  if any(x["verdict"]!="ACCEPT" for x in results):raise ValueError("RECONSTRUCTION")
  if any(x["override_count"] or x["bypass_components"] for x in results):raise ValueError("PRESERVATION")
  if any(x["actual"]!="REJECT" for x in mutations):raise ValueError("MUTATION_ACCEPTED")
  return {"verdict":"ACCEPT","reason":"INTEGRATION_INVARIANTS_HOLD","sessions":len(results),"reconstructed":len(results),"overrides":0,"bypasses":0,"generator_acceptance_logic_reused":False}
 except Exception as e:return {"verdict":"REJECT","reason":str(e)}
