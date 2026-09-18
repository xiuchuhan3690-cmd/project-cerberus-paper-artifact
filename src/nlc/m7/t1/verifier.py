"""Independent validator; imports no fixture generator or M5 acceptance logic."""
import hashlib,json
from m1.canonical import canonical_bytes
ALLOWED_ADAPTERS={"IDEMPOTENT","ESCROWED","FENCED","UNOBSERVABLE"};FORBIDDEN={"discovered_services","candidate_generator","architecture_search","repair_proposal","ranking_algorithm","topology_optimizer"}
def digest(tag,v):return hashlib.sha256(tag+json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def verify(bundle):
 try:
  m=bundle["manifest"];t=m["topology"]
  if m["fixture_version"]!="SRA_Fixture_v1" or m["inventory_policy"]!="FINITE_PREDECLARED_ONLY":raise ValueError("FIXTURE_SCHEMA")
  core={k:m[k] for k in m if k!="fixture_id"};
  if m["fixture_id"]!=digest(b"NLC-M7-SRA-FIXTURE/1.0\0",core):raise ValueError("FIXTURE_ID")
  if m["topology_hash"]!=digest(b"NLC-M7-SRA-TOPOLOGY/1.0\0",t):raise ValueError("TOPOLOGY_HASH")
  if len(t["candidates"])!=2 or {x["actual_status"] for x in t["candidates"]}!={"ELIGIBLE","EXCLUDED"}:raise ValueError("CANDIDATES")
  if any(not x["predeclared"] for x in t["services"]) or len({x["service_id"] for x in t["services"]})!=len(t["services"]):raise ValueError("INVENTORY")
  if {x["class"] for x in t["effect_adapters"]}!=ALLOWED_ADAPTERS or any(not x["inventory_only"] for x in t["effect_adapters"]):raise ValueError("ADAPTERS")
  raw=json.dumps(m,sort_keys=True)
  if any(k in raw for k in FORBIDDEN):raise ValueError("AUTO_DISCOVERY_OR_SEARCH")
  edges=bundle["aim"]["typed_edges"]
  if {x["semantic_relation"] for x in edges}!={"BUILD","KMS_ROOT_CONTROL","ADMIN_CONTROL"} or any(x["lineage_only"] or x["disposition"]!="EXCLUDE" for x in edges):raise ValueError("AIM_BINDING")
  if bundle["sterility"]["valid"]["actual"]!="USABLE" or bundle["sterility"]["invalid"]["actual"]!="QUARANTINE":raise ValueError("STERILITY")
  w=bundle["witness"];wc={k:w[k] for k in w if k!="witness_commitment"}
  if w["witness_commitment"]!=digest(b"NLC-M7-FUNCTIONAL-WITNESS/1.0\0",wc) or w["expected_finite_output"]!=w["actual_deterministic_output"]:raise ValueError("WITNESS")
  if not bundle["readiness"]["complete"] or bundle["readiness"]["frozen_root_accept_verdict"]!="ACCEPT":raise ValueError("ROOT_ACCEPT_READINESS")
  h=bundle["hold"]
  if (h["actual"],h["eligible_count"],h["new_candidate_invented"],h["unknown_treated_clean"])!=("HOLD",0,False,False):raise ValueError("HOLD")
  if any(x["actual"]!="REJECT" for x in bundle["scope"]) or bundle["claims"]["new_owned_mechanisms"]!=0:raise ValueError("CLAIM_BOUNDARY")
  return {"verdict":"ACCEPT","reason":"FINITE_PREDECLARED_FIXTURE_VALID","fixture_id":m["fixture_id"],"topology_hash":m["topology_hash"],"generator_acceptance_logic_reused":False}
 except Exception as e:return {"verdict":"REJECT","reason":str(e)}
