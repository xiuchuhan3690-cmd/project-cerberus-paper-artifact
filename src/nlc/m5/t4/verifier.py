"""Independent combined checker; imports no T4 implementation or barrier code."""

from __future__ import annotations
from dataclasses import dataclass
import hashlib,json,unicodedata


ORDER=("NAMESPACE","VERIFIER_DOMAIN","CRYPTOGRAPHIC_ROOT","SEMANTIC_GRAMMAR","PROTOCOL_ADAPTER")
VERSIONS={"NAMESPACE":"NLC-NAMESPACE-BARRIER/1.0","VERIFIER_DOMAIN":"NLC-VERIFIER-DOMAIN-BARRIER/1.0","CRYPTOGRAPHIC_ROOT":"NLC-CRYPTOGRAPHIC-ROOT-BARRIER/1.0","SEMANTIC_GRAMMAR":"NLC-SEMANTIC-GRAMMAR-BARRIER/1.0","PROTOCOL_ADAPTER":"NLC-PROTOCOL-ADAPTER-BARRIER/1.0"}
VERIFIERS={name:f"NLC-{name.replace('_','-')}-VERIFIER/1.0" for name in ORDER}
ARTIFACT_TAG=b"NLC-M5-T4-EPOCH-ARTIFACT-v1\x00"; EVIDENCE_TAG=b"NLC-M5-T4-BARRIER-EVIDENCE-v1\x00"; COMBINED_TAG=b"NLC-M5-T4-COMBINED-DECISION-v1\x00"; SIGNATURE_TAG=b"NLC-M5-T4-SYNTHETIC-SIGNATURE-v1\x00"


@dataclass(frozen=True)
class Verification:
    verdict:str; reason_code:str; individual_recomputed:int; active_binding_verified:bool; old_authority_absent:bool
    verifier_version:str="NLC-M5-T4-INDEPENDENT-COMBINED-VERIFIER/1.0"


class Reject(ValueError): pass
def _pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise Reject("DUPLICATE_FIELD")
        out[k]=v
    return out
def canonical(value):
    def n(v):
        if v is None or isinstance(v,float): raise Reject("MALFORMED_VALUE")
        if isinstance(v,(bool,int)): return v
        if isinstance(v,str): return unicodedata.normalize("NFC",v)
        if isinstance(v,list): return [n(x) for x in v]
        if isinstance(v,dict): return {unicodedata.normalize("NFC",k):n(x) for k,x in v.items()}
        raise Reject("MALFORMED_VALUE")
    return json.dumps(n(value),ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def h(tag,value):return hashlib.sha256(tag+canonical(value)).hexdigest()
def artifact_material(a):return {k:a[k] for k in ("artifact_version","authority_claim","cryptographic_root_id","cutover_receipt_id","cutover_receipt_sha256","cutover_slot_id","grammar_id","namespace_id","namespace_version","protocol_adapter_id","protocol_adapter_version","request_format","root_id","synthetic_signature","target_domain","target_epoch","verifier_domain_id","verifier_version")}
def signature_material(a):return {k:a[k] for k in ("authority_claim","cryptographic_root_id","root_id","target_domain","target_epoch")}


def expected(name,a,c):
    if name=="NAMESPACE":
        if a["namespace_id"]!=c["namespace_id"]:return "REJECT","OLD_OR_WRONG_NAMESPACE"
        if a["namespace_version"]!=c["namespace_version"]:return "REJECT","NAMESPACE_VERSION_MISMATCH"
        return "PASS","NAMESPACE_BOUND"
    if name=="VERIFIER_DOMAIN":
        if a["verifier_domain_id"]!=c["verifier_domain_id"]:return "REJECT","OLD_OR_WRONG_VERIFIER_DOMAIN"
        if a["verifier_version"]!=c["verifier_version"]:return "REJECT","VERIFIER_VERSION_MISMATCH"
        return "PASS","VERIFIER_DOMAIN_BOUND"
    if name=="CRYPTOGRAPHIC_ROOT":
        if a["cryptographic_root_id"]!=c["cryptographic_root_id"]:return "REJECT","OLD_OR_WRONG_CRYPTOGRAPHIC_ROOT"
        if a["synthetic_signature"]!=h(SIGNATURE_TAG,signature_material(a)):return "REJECT","SYNTHETIC_SIGNATURE_INVALID"
        return "PASS","CRYPTOGRAPHIC_ROOT_BOUND"
    if name=="SEMANTIC_GRAMMAR":
        if a["grammar_id"]!=c["semantic_grammar_id"]:return "REJECT","OLD_OR_UNSUPPORTED_GRAMMAR"
        if a["request_format"]!="NATIVE_CLOSED_AUTHORITY_OBJECT":return "REJECT","PARSER_BRIDGE_OR_OPAQUE_FORMAT_PROHIBITED"
        return "PASS","NATIVE_CLOSED_GRAMMAR_BOUND"
    if a["protocol_adapter_id"]!=c["protocol_adapter_id"]:return "REJECT","LEGACY_OR_UNKNOWN_ADAPTER"
    if a["protocol_adapter_version"]!=c["protocol_adapter_version"]:return "REJECT","ADAPTER_VERSION_MISMATCH"
    return "PASS","NATIVE_ADAPTER_BOUND"


def verify(decision_bytes,artifact,expected_context):
    count=0
    try:
        value=json.loads(decision_bytes.decode(),object_pairs_hook=_pairs)
        if canonical(value)!=decision_bytes:raise Reject("NON_CANONICAL_DECISION")
        if artifact.get("artifact_id")!=h(ARTIFACT_TAG,artifact_material(artifact)):raise Reject("ARTIFACT_ID_MISMATCH")
        if artifact.get("artifact_version")!="NLC-EPOCH-AUTHORITY-ARTIFACT/1.0":raise Reject("ARTIFACT_VERSION_INVALID")
        if artifact.get("authority_claim")!="NATIVE_NEW_EPOCH_AUTHORITY":raise Reject("AUTHORITY_CLAIM_INVALID")
        context=value["active_binding"]
        if context!=expected_context:raise Reject("ACTIVE_BINDING_MISMATCH")
        if value.get("suite_version")!="NLC-EPOCH-BARRIER-SUITE/1.0" or value.get("combined_version")!="NLC-EPOCH-BARRIER-COMBINED/1.0":raise Reject("SUITE_OR_COMBINED_VERSION_MISMATCH")
        for key in ("active_root_id","cutover_slot_id","cutover_receipt_id","cutover_receipt_sha256","target_domain","target_epoch"):
            artifact_key={"active_root_id":"root_id"}.get(key,key)
            if artifact[artifact_key]!=context[key]:raise Reject({"active_root_id":"ACTIVE_ROOT_MISMATCH","cutover_slot_id":"CUTOVER_SLOT_MISMATCH","cutover_receipt_id":"STALE_CUTOVER_RECEIPT","cutover_receipt_sha256":"CUTOVER_RECEIPT_HASH_MISMATCH","target_domain":"TARGET_DOMAIN_MISMATCH","target_epoch":"TARGET_EPOCH_MISMATCH"}[key])
        rows=value["barrier_decisions"]
        if not isinstance(rows,list) or len(rows)!=5:raise Reject("BARRIER_EVIDENCE_COUNT_INVALID")
        for name,row in zip(ORDER,rows):
            if row.get("barrier_id")!=name or row.get("barrier_version")!=VERSIONS[name] or row.get("verifier_version")!=VERIFIERS[name]:raise Reject("BARRIER_ID_OR_VERSION_MISMATCH")
            if row.get("decision_version")!="NLC-EPOCH-BARRIER-DECISION/1.0" or row.get("verifier_id")!=f"EpochBarrierVerifier_{name}":raise Reject("DECISION_OR_VERIFIER_ID_MISMATCH")
            if row.get("input_artifact_id")!=artifact["artifact_id"] or row.get("expected_domain")!=context["target_domain"] or row.get("expected_epoch")!=context["target_epoch"] or row.get("observed_domain")!=artifact["target_domain"] or row.get("observed_epoch")!=artifact["target_epoch"]:raise Reject("OBSERVABILITY_BINDING_MISMATCH")
            unsigned={k:v for k,v in row.items() if k!="evidence_commitment"}
            if row.get("evidence_commitment")!=h(EVIDENCE_TAG,unsigned):raise Reject("EVIDENCE_COMMITMENT_MISMATCH")
            verdict,reason=expected(name,artifact,context)
            if (row.get("verdict"),row.get("reason_code"))!=(verdict,reason):raise Reject("INDIVIDUAL_VERDICT_MISMATCH")
            count+=1
        all_pass=all(row["verdict"]=="PASS" for row in rows)
        if value.get("verdict")!=("PASS" if all_pass else "REJECT") or value.get("authority_effective")!=all_pass:raise Reject("COMBINED_VERDICT_MISMATCH")
        expected_reason="ALL_FIVE_BARRIERS_PASS" if all_pass else next(row["reason_code"] for row in rows if row["verdict"]!="PASS")
        if value.get("reason_code")!=expected_reason:raise Reject("COMBINED_REASON_MISMATCH")
        unsigned={k:v for k,v in value.items() if k!="decision_id"}
        if value.get("decision_id")!=h(COMBINED_TAG,unsigned):raise Reject("COMBINED_DECISION_ID_MISMATCH")
        old_tokens=any(("OLD" in x.upper() or "LEGACY" in x.upper()) for x in artifact.values() if isinstance(x,str)) if all_pass else False
        old_absent=value.get("authority_ancestry")==[] and value.get("old_authority_relations")==[] and not old_tokens
        if not old_absent:raise Reject("OLD_AUTHORITY_RELATION_PRESENT")
        return Verification("ACCEPT","BARRIER_SUITE_INDEPENDENTLY_VERIFIED",count,True,True)
    except Reject as exc:return Verification("REJECT",str(exc),count,False,False)
    except (KeyError,TypeError,UnicodeError,json.JSONDecodeError):return Verification("REJECT","ARTIFACT_MALFORMED",count,False,False)
