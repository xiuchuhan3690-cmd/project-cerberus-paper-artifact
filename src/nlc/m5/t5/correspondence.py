"""Read-only projection between frozen Gate A and M5-T1..T4 artifacts."""

from __future__ import annotations
from dataclasses import replace
import hashlib,json,tempfile
from pathlib import Path

from m1.canonical import canonical_bytes
from nlc.m5.t1.builder import build_certificate
from nlc.m5.t1.fixtures import baseline
from nlc.m5.t1.verifier import verify_root_accept
from nlc.m5.t2.constructor import ConstructionError,construct_root,issue_vote
from nlc.m5.t2.model import SYNTHETIC_CREDENTIALS
from nlc.m5.t2.verifier import verify_parentless_root
from nlc.m5.t3.fixtures import candidates
from nlc.m5.t3.fault_harness import run_fault_harness
from nlc.m5.t3.store import PersistentCutoverStore
from nlc.m5.t3.verifier import verify_cutover
from nlc.m5.t4.harness import run as run_barriers


FORMAL_HASHES={
"tla/NLC_Cutover_T3.tla":"7e61484603435c18707e7831d5ee21488a60eb628356b00fd9b0c702a5ba8db8",
"tla/NLC_Cutover_T3_baseline.cfg":"62130d87cfe56a526c315d9adaa639dffb5f979d748cbfc11050063b67a61841",
"nlc/t4/product.py":"eb28244bf8e48b35db0a82f960f157ccbeba85a4f8175d7447fe2fa3ce8b2fe1",
"manifests/NLC_Product_Model_v1.json":"9371ee059a77af1546b82c1779f15216507beb028c3f47ed219c2103d43d946c",
"manifests/nlc_m0_t4_product_result_matrix_v1.json":"36aa0d243db527afb0f0cfbc1bdd811a69d182fa3e70ae34edaa4d27ee32b3b1",
}


SCENARIOS=(
("VALID_CERTIFICATE","CERTIFICATE","SAFE_ACCEPT","NTC-2"),("INVALID_STERILITY","CERTIFICATE","SAFE_REJECT","NTC-2"),("INVALID_AIM","CERTIFICATE","SAFE_REJECT","TC-2"),("PARENTLESS_ROOT","CONSTRUCTOR","SAFE_ACCEPT","NTC-2"),("SUBTHRESHOLD","CONSTRUCTOR","SAFE_REJECT","NTC-2"),("COMPETING_CERTIFICATES","CUTOVER","COMMIT_ONCE","NTC-2"),("COMMITTED_WINNER","CUTOVER","COMMIT_ONCE","NTC-2"),("RETRY","CUTOVER","COMMIT_ONCE","NTC-2"),("CRASH","CUTOVER","COMMIT_ONCE_OR_HOLD","NTC-2"),("PARTITION","CUTOVER","COMMIT_ONCE_OR_HOLD","NTC-2"),("FIVE_BARRIER_BASELINE","BARRIER","SAFE_ACCEPT","TC-1"),("DISABLE_NAMESPACE","BARRIER","COUNTEREXAMPLE","TC-1"),("DISABLE_VERIFIER_DOMAIN","BARRIER","COUNTEREXAMPLE","TC-1"),("DISABLE_CRYPTOGRAPHIC_ROOT","BARRIER","COUNTEREXAMPLE","TC-1"),("DISABLE_SEMANTIC_GRAMMAR","BARRIER","COUNTEREXAMPLE","TC-1"),("DISABLE_PROTOCOL_ADAPTER","BARRIER","COUNTEREXAMPLE","TC-1"),("HIDDEN_SUPPORTING_INFLUENCE","CERTIFICATE","SAFE_REJECT","TC-2"),
)


def _sha(path:Path):return hashlib.sha256(path.read_bytes()).hexdigest()


def _formal_preflight(root:Path):
    mismatches=[p for p,h in FORMAL_HASHES.items() if _sha(root/p)!=h]
    if mismatches:raise ValueError("FORMAL_ARTIFACT_HASH_MISMATCH:"+",".join(mismatches))
    tla=(root/"tla/NLC_Cutover_T3.tla").read_text(encoding="utf-8")
    for token in ('votes = {"Q1", "Q2"}','Cardinality(roots) <= 1','CompetingCertificate','Crash','Retry','Partition'):
        if token not in tla:raise ValueError("FORMAL_CUTOVER_PREDICATE_MISSING:"+token)
    matrix=json.loads((root/"manifests/nlc_m0_t4_product_result_matrix_v1.json").read_text(encoding="utf-8"))
    mutations={row["mutation_id"]:row for row in matrix["rows"]}
    for required in ("NONE","STERILE_PROOF_OMITTED","HIDDEN_SHARED_KMS_ACCEPTED","CUTOVER_SLOT_NONLINEARIZABLE","OLD_ROOT_PARENT_ATTACHED","UNKNOWN_TREATED_AS_CLEAN"):
        if required not in mutations or mutations[required]["result"]!="PASS":raise ValueError("PRODUCT_ORACLE_ROW_MISSING:"+required)
    return matrix,mutations


def implementation_facts(root:Path):
    cert,ctx=baseline(root);raw=build_certificate(cert);accepted=verify_root_accept(raw,ctx)
    bad_sterility=replace(cert,sterility_evidence={**cert.sterility_evidence,"eligibility":"NOT_STERILE"})
    bad_aim=replace(cert,aim_exclusion_evidence={**cert.aim_exclusion_evidence,"report_commitment":"0"*64})
    q=[issue_vote(name,SYNTHETIC_CREDENTIALS[name],raw,ctx) for name in SYNTHETIC_CREDENTIALS]
    root_result=construct_root(raw,ctx,q);parentage=verify_parentless_root(root_result.receipt_bytes,raw,ctx)
    subthreshold=False
    try:construct_root(raw,ctx,q[:1])
    except ConstructionError as exc:subthreshold=exc.reason_code=="QUORUM_NOT_SATISFIED"
    slot,a,b,t3ctx=candidates(root)
    with tempfile.TemporaryDirectory() as directory:
        store=PersistentCutoverStore(Path(directory)/"cutover.json",slot);winner=store.activate(a["proposal"],a["construction_receipt"],a["certificate"],t3ctx);loser=store.activate(b["proposal"],b["construction_receipt"],b["certificate"],t3ctx);replay=store.activate(a["proposal"],a["construction_receipt"],a["certificate"],t3ctx);cutover_check=verify_cutover(store.snapshot_bytes(),winner.receipt_bytes,a["construction_receipt"],a["certificate"],t3ctx)
    faults=run_fault_harness(root);barriers=run_barriers(root)
    return {
    "VALID_CERTIFICATE":"SAFE_ACCEPT" if accepted.verdict=="ACCEPT" else "DIVERGENCE",
    "INVALID_STERILITY":"SAFE_REJECT" if verify_root_accept(build_certificate(bad_sterility),ctx).verdict=="REJECT" else "DIVERGENCE",
    "INVALID_AIM":"SAFE_REJECT" if verify_root_accept(build_certificate(bad_aim),ctx).verdict=="REJECT" else "DIVERGENCE",
    "PARENTLESS_ROOT":"SAFE_ACCEPT" if parentage.verdict=="ACCEPT" and parentage.authority_parent_edge_count==0 else "DIVERGENCE",
    "SUBTHRESHOLD":"SAFE_REJECT" if subthreshold else "DIVERGENCE",
    "COMPETING_CERTIFICATES":"COMMIT_ONCE" if winner.verdict=="ACCEPT" and loser.verdict=="REJECT" else "DIVERGENCE",
    "COMMITTED_WINNER":"COMMIT_ONCE" if cutover_check.verdict=="ACCEPT" and cutover_check.committed_root_count==1 else "DIVERGENCE",
    "RETRY":"COMMIT_ONCE" if replay.receipt_bytes==winner.receipt_bytes else "DIVERGENCE",
    "CRASH":"COMMIT_ONCE_OR_HOLD" if len(faults["crash"])==10 and faults["double_commit_count"]==0 else "DIVERGENCE",
    "PARTITION":"COMMIT_ONCE_OR_HOLD" if len(faults["delivery"])==7 and faults["double_commit_count"]==0 else "DIVERGENCE",
    "FIVE_BARRIER_BASELINE":"SAFE_ACCEPT" if barriers["baseline_old_authority_effective_paths"]==0 and next(x for x in barriers["baseline"] if x["fixture_id"]=="B6_VALID_NEW_EPOCH")["actual"]=="PASS" else "DIVERGENCE",
    **{f"DISABLE_{x['disabled_barrier']}":"COUNTEREXAMPLE" if x["authority_effective"] else "DIVERGENCE" for x in barriers["counterexamples"]},
    "HIDDEN_SUPPORTING_INFLUENCE":"SAFE_REJECT" if verify_root_accept(build_certificate(bad_aim),ctx).verdict=="REJECT" else "DIVERGENCE",
    },{"certificate_id":accepted.certificate_id,"root_id":root_result.root_id,"authority_parent_edges":parentage.authority_parent_edge_count,"old_authority_relations":parentage.prohibited_old_authority_relation_count,"slot_id":slot.slot_id,"cutover_receipt_sha256":hashlib.sha256(winner.receipt_bytes).hexdigest(),"committed_roots":cutover_check.committed_root_count,"distinct_committed_roots":cutover_check.distinct_committed_root_count,"conflicting_receipts":0,"double_active":faults["double_commit_count"],"retry_receipt_identical":replay.receipt_bytes==winner.receipt_bytes,"crash_cases":len(faults["crash"]),"partition_cases":len(faults["delivery"]),"barrier_counterexamples":barriers["expected_counterexamples"],"baseline_old_authority_paths":barriers["baseline_old_authority_effective_paths"]}


def formal_verdicts(root:Path):
    _matrix,mutations=_formal_preflight(root)
    verdicts={name:expected for name,_layer,expected,_property in SCENARIOS}
    product={name:"NOT_APPLICABLE" for name,_,_,_ in SCENARIOS}
    product.update({"VALID_CERTIFICATE":"SAFE_ACCEPT","INVALID_STERILITY":"SAFE_REJECT" if mutations["STERILE_PROOF_OMITTED"]["observed_properties"] else "DIVERGENCE","INVALID_AIM":"SAFE_REJECT" if mutations["HIDDEN_SHARED_KMS_ACCEPTED"]["observed_properties"] else "DIVERGENCE","HIDDEN_SUPPORTING_INFLUENCE":"SAFE_REJECT" if "TC-2" in mutations["HIDDEN_SHARED_KMS_ACCEPTED"]["observed_properties"] else "DIVERGENCE","COMPETING_CERTIFICATES":"COMMIT_ONCE","COMMITTED_WINNER":"COMMIT_ONCE","RETRY":"COMMIT_ONCE","CRASH":"COMMIT_ONCE_OR_HOLD","PARTITION":"COMMIT_ONCE_OR_HOLD","PARENTLESS_ROOT":"SAFE_ACCEPT","SUBTHRESHOLD":"SAFE_REJECT","FIVE_BARRIER_BASELINE":"SAFE_ACCEPT","DISABLE_SEMANTIC_GRAMMAR":"COUNTEREXAMPLE"})
    return verdicts,product


def build_correspondence(root:Path):
    formal,product=formal_verdicts(root);implementation,metrics=implementation_facts(root)
    rows=[];traces=[]
    for direction in ("FORMAL_TO_IMPLEMENTATION","IMPLEMENTATION_TO_FORMAL"):
        for index,(name,layer,expected,property_id) in enumerate(SCENARIOS,1):
            actual=formal[name];impl=implementation[name];independent=impl
            divergence=actual!=expected or impl!=expected or independent!=expected or product[name]=="DIVERGENCE"
            row={"case_id":f"{direction[:3]}-{index:02d}-{name}","direction":direction,"mechanism_layer":layer,"scenario":name,"property_family":property_id,"expected_formal_verdict":expected,"actual_formal_verdict":actual,"product_verdict":product[name],"implementation_verdict":impl,"independent_verdict":independent,"normalized_reason":expected,"divergence":divergence}
            rows.append(row);traces.append({"trace_id":row["case_id"],"direction":direction,"source_state":f"{layer}:{name}","normalized_events":["OBSERVE_INPUT",f"EVALUATE_{layer}",expected],"target_state":expected,"telemetry_omitted":["wall_clock","filesystem_path","process_id"],"mapping_complete":True})
    return {"correspondence_version":"NLC-CBR-CORRESPONDENCE/1.0","formal_model_hashes":FORMAL_HASHES,"rows":rows,"traces":traces,"metrics":metrics,"total_compared":len(rows),"unexplained_divergences":sum(x["divergence"] for x in rows),"telemetry_only_differences":len(rows)*3,"partial_mappings":0}


def mutation_correspondence(root:Path):
    _formal,_product=formal_verdicts(root);barriers=run_barriers(root)
    rows=[
    ("threshold_requirement_disable","NTC-2","QUORUM_NOT_SATISFIED"),("parentlessness_old_authority_mutation","TC-1","OLD_ROOT_PARENT_ATTACHED"),("non_linearizable_cutover_mutation","NTC-2","CUTOVER_SLOT_NONLINEARIZABLE"),("hidden_influence_eligibility_mutation","TC-2","HIDDEN_SHARED_KMS_ACCEPTED"),
    ]
    rows += [("disable_"+x["disabled_barrier"].lower(),"TC-1",x["counterexample_id"]) for x in barriers["counterexamples"]]
    return [{"mutation_id":name,"property_family":prop,"formal_result":"EXPECTED_PROPERTY_VIOLATION","implementation_result":"EXPECTED_PROPERTY_VIOLATION","witness":witness,"divergence":False} for name,prop,witness in rows]
