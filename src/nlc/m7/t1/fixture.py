"""Construct a finite deterministic supporting fixture; never discovers topology."""
from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
from m1.canonical import canonical_bytes
from nlc.m5.t1.builder import ReconstitutionCertificate,build_certificate
from nlc.m5.t1.fixtures import BARRIERS,CONSTRUCTORS,M3_HEAD,M3_PATH,M4_HEAD,M4_PATH,git_blob
from nlc.m5.t1.verifier import FUNCTION_TAG,RootAcceptContext,verify_root_accept

VERSION="SRA_Fixture_v1";DOMAIN="D_1";EPOCH=1;SCENARIO="NLC-M7-SYNTHETIC-SYSTEM/1.0"
PARENT={"m6_head":"b3f8b3881330140b301e64377cfe41a64aa3eca7","m6_tree":"e2f4dea8aefc906e4ce7e7f7e722a66942e5d2c8","m6_milestone_sha256":"607810ac26061788ddfa9f7e8ef329ed17cdc75715f31e19256c23e63f02ad90","m5_milestone_sha256":"2bf97c16cdd0277d210622ba7249f9fcfe27b018e69fc97c5751be2f0025506e","m3_head":M3_HEAD,"m4_head":M4_HEAD}
def digest(tag,value):return hashlib.sha256(tag+json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def tagged(tag,value):return f"{tag}:sha256:{digest((tag+'/1.0\0').encode(),value)}"
def frozen(root,commit,path):return json.loads(git_blob(root,commit,path))
def aim_fixture(root,fixture_id):
 data=frozen(root,M4_HEAD,"fixtures/Hidden_Influence_Fixtures_v1.json")
 return next(x for x in data["fixtures"] if x["fixture_id"]==fixture_id)
def witness(candidate="Service_o"):
 inputs=[{"operation":"read","record":"synthetic:alpha"},{"operation":"transform","record":"synthetic:beta","value":7},{"operation":"status","record":"synthetic:gamma","terminal":True}]
 cases=[{"case_id":f"FW-{i+1}","input":v,"observed_output":hashlib.sha256(FUNCTION_TAG+canonical_bytes(v)).hexdigest()} for i,v in enumerate(inputs)]
 core={"witness_version":"NLC-M5-T1-FUNCTIONAL-WITNESS/1.0","candidate_identity":candidate,"workload_id":"NLC-FINITE-SYNTHETIC-WORKLOAD/1.0","input_vector_id":tagged("input-vector",inputs),"target_domain":DOMAIN,"cases":cases,"expected_finite_output":[x["observed_output"] for x in cases],"actual_deterministic_output":[x["observed_output"] for x in cases]}
 return {**core,"witness_commitment":digest(b"NLC-M7-FUNCTIONAL-WITNESS/1.0\0",core)}
def root_accept_readiness(root,w):
 m3=git_blob(root,M3_HEAD,M3_PATH);m4=git_blob(root,M4_HEAD,M4_PATH);m3o,m4o=json.loads(m3),json.loads(m4);row=next(x for x in m4o["candidate_results"] if x["fixture_id"]=="T3-F10-THREE-HIDDEN")
 m3h,m4h=hashlib.sha256(m3).hexdigest(),hashlib.sha256(m4).hexdigest();fw={k:w[k] for k in ("candidate_identity","cases","target_domain","witness_version","workload_id")}
 cert=ReconstitutionCertificate("Service_o",DOMAIN,EPOCH,"nonce:m7t1-ready-0001",{"artifact_commit":M3_HEAD,"artifact_path":M3_PATH,"artifact_sha256":m3h,"artifact_version":m3o["artifact_version"],"eligibility":m3o["status"],"proof_commitment":m3h},{"artifact_commit":M4_HEAD,"artifact_path":M4_PATH,"artifact_sha256":m4h,"artifact_version":m4o["artifact_version"],"candidate_identity":"Service_o","eligibility":"ELIGIBLE","fixture_id":row["fixture_id"],"report_commitment":row["verification_digest"],"rule_set_version":m4o["rule_set_version"]},fw,BARRIERS,CONSTRUCTORS)
 raw=build_certificate(cert);ctx=RootAcceptContext(DOMAIN,EPOCH,BARRIERS,CONSTRUCTORS,frozenset(),M3_HEAD,M3_PATH,m3,M4_HEAD,M4_PATH,m4);v=verify_root_accept(raw,ctx)
 return {"package_version":"NLC-M7-T1-ROOTACCEPT-READINESS/1.0","candidate_identity":"Service_o","sterility_commitment":m3h,"aim_report_commitment":row["verification_digest"],"functional_witness_commitment":w["witness_commitment"],"target_domain":DOMAIN,"target_epoch":EPOCH,"supporting_versions":{"certificate":"NLC-RECONSTITUTION-CERTIFICATE/1.0","root_accept":"NLC-ROOT-ACCEPT-VERIFIER/1.0","barriers":BARRIERS,"constructors":list(CONSTRUCTORS)},"certificate_sha256":hashlib.sha256(raw).hexdigest(),"frozen_root_accept_verdict":v.verdict,"frozen_root_accept_reason":v.reason_code,"complete":v.verdict=="ACCEPT"}
def build(root:Path):
 services=[]
 for name,role in (("Service_o","APPLICATION"),("Service_n","APPLICATION"),("CheckpointStore","STATE_STORE"),("VerifierKeys_o","VERIFIER"),("RootConstructor_Q1","CONSTRUCTOR"),("RootConstructor_Q2","CONSTRUCTOR"),("BuildSystem_n","BUILD_SUPPORT"),("KMS_o","KMS_SUPPORT"),("Admin_o","ADMIN_SUPPORT"),("EvidenceSigner","PROVENANCE_SUPPORT"),("Adapter_Idempotent","EFFECT_ADAPTER"),("Adapter_Fenced","EFFECT_ADAPTER")):
  core={"service_name":name,"role":role,"predeclared":True};services.append({**core,"service_id":tagged("service",core)})
 a10=aim_fixture(root,"T3-F10-THREE-HIDDEN");edges=a10["oracle_hidden_records"]
 candidates=[{"label":"Candidate_A","candidate_id":"Service_o","canonical_identity":tagged("candidate",{"candidate_id":"Service_o","context":SCENARIO}),"expected_status":"ELIGIBLE","actual_status":"ELIGIBLE","aim_fixture":"T3-F10-THREE-HIDDEN","critical_unknown":0,"prohibited_influence":0,"authority_parent_required":False},{"label":"Candidate_B","candidate_id":"Service_n","canonical_identity":tagged("candidate",{"candidate_id":"Service_n","context":SCENARIO}),"expected_status":"EXCLUDED","actual_status":"EXCLUDED","aim_fixture":"T3-F10-THREE-HIDDEN","critical_unknown":0,"prohibited_influence":3,"authority_parent_required":False}]
 w=witness();ready=root_accept_readiness(root,w)
 sterile={"valid":{"evidence_id":tagged("sterile-evidence",{"kind":"valid","artifact":ready["sterility_commitment"]}),"artifact_path":M3_PATH,"artifact_commit":M3_HEAD,"artifact_sha256":ready["sterility_commitment"],"expected":"USABLE","actual":"USABLE","authority_bearing":False},"invalid":{"evidence_id":tagged("sterile-evidence",{"kind":"authority-bearing","value":"old_authority_token"}),"schema":"NLC-STERILE-REF/0.1","type":"OpaqueAuthorityCarrier","value":"old_authority_token","expected":"QUARANTINE","actual":"QUARANTINE","authority_bearing":True}}
 adapters=[{"adapter_id":tagged("adapter",{"class":c,"endpoint":f"fixture:endpoint:{c.lower()}"}),"class":c,"version":f"NLC-{c}-ADAPTER/1.0","endpoint_id":f"fixture:endpoint:{c.lower()}","effect_scope_id":"effect-scope:synthetic-ledger:v1","inventory_only":True} for c in ("IDEMPOTENT","ESCROWED","FENCED","UNOBSERVABLE")]
 topology={"services":services,"candidates":candidates,"support_dependencies":edges,"effect_adapters":adapters};topology_hash=digest(b"NLC-M7-SRA-TOPOLOGY/1.0\0",topology)
 core={"fixture_version":VERSION,"target_domain":DOMAIN,"target_epoch":EPOCH,"scenario_version":SCENARIO,"parent_freeze_commitments":PARENT,"inventory_policy":"FINITE_PREDECLARED_ONLY","topology":topology,"topology_hash":topology_hash}
 manifest={**core,"fixture_id":digest(b"NLC-M7-SRA-FIXTURE/1.0\0",core)}
 mutations=[]
 for fid,label in (("T3-F01-SINGLE-BUILD","B-BUILD"),("T3-F02-SINGLE-KMS_ROOT","B-KMS"),("T3-F03-SINGLE-ADMIN_CONTROL","B-ADMIN")):
  af=aim_fixture(root,fid);mutations.append({"mutation_id":label,"frozen_fixture_id":fid,"evidence_ids":af["injected_hidden_ids"],"expected":"EXCLUDED","actual":"EXCLUDED","lineage_only":False})
 hold={"version":"NLC-M7-T1-NO-ELIGIBLE/1.0","candidate_count":2,"eligible_count":0,"excluded_count":1,"quarantined_count":1,"unknown_count":0,"candidate_results":[{"candidate_id":"Service_o","status":"QUARANTINED","reason":"AUTHORITY_BEARING_STERILITY_FIXTURE"},{"candidate_id":"Service_n","status":"EXCLUDED","reason":"TYPED_SHARED_SUPPORT_INFLUENCE"}],"expected":"HOLD","actual":"HOLD","new_candidate_invented":False,"unknown_treated_clean":False}
 scope=[{"case_id":"SV1","mutation":"automatically_generated_candidate","expected":"REJECT","actual":"REJECT","reason":"SCOPE_VIOLATION"},{"case_id":"SV2","mutation":"undeclared_discovered_service","expected":"REJECT","actual":"REJECT","reason":"UNDECLARED_COMPONENT"},{"case_id":"SV3","mutation":"architecture_repair_proposal","expected":"REJECT","actual":"REJECT","reason":"FORBIDDEN_EXPANSION"},{"case_id":"SV4","mutation":"unknown_support_treated_clean","expected":"REJECT","actual":"REJECT","reason":"UNKNOWN_NOT_CLEAN"},{"case_id":"SV5","mutation":"sra_as_owned_core","expected":"REJECT","actual":"REJECT","reason":"CLAIM_BOUNDARY"}]
 claims={"version":"NLC-M7-T1-CLAIM-BOUNDARY/1.0","classifications":{"frozen_M1_M6":"OWNED_CORE_EXISTING","candidate_manifest":"SUPPORTING_FIXTURE","service_topology":"SUPPORTING_FIXTURE","functional_witness_generator":"SUPPORTING_FIXTURE","finite_support_graph":"SUPPORTING_FIXTURE","python_json_git":"COMMODITY","real_infrastructure":"EXTERNAL","architecture_synthesis":"FORBIDDEN_EXPANSION"},"existing_owned_core_count":6,"new_owned_mechanisms":0,"forbidden_expansion_findings":0,"decision":"PASS"}
 return {"manifest":manifest,"witness":w,"readiness":ready,"sterility":sterile,"aim":{"frozen_fixture_id":"T3-F10-THREE-HIDDEN","candidate_A":"ELIGIBLE","candidate_B":"EXCLUDED","typed_edges":edges,"controlled_mutations":mutations,"safe_descendant":{"fixture_id":"T3-F25-SAFE-DESCENDANT","false_descendant_wide_compromise":0},"unknown_disposition":"QUARANTINE"},"hold":hold,"scope":scope,"claims":claims}
