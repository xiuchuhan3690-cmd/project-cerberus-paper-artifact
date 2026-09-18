"""Independent structural verifier for T5 correspondence artifacts."""

from __future__ import annotations
from dataclasses import dataclass
import json,unicodedata


@dataclass(frozen=True)
class Verification:
    verdict:str;reason_code:str;checked_rows:int;checked_traces:int;verifier_version:str="NLC-M5-T5-INDEPENDENT-CORRESPONDENCE-VERIFIER/1.0"
class Reject(ValueError):pass
def _pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out:raise Reject("DUPLICATE_FIELD")
        out[k]=v
    return out
def _norm(v):
    if v is None or isinstance(v,float):raise Reject("MALFORMED_VALUE")
    if isinstance(v,(bool,int)):return v
    if isinstance(v,str):return unicodedata.normalize("NFC",v)
    if isinstance(v,list):return [_norm(x) for x in v]
    if isinstance(v,dict):return {unicodedata.normalize("NFC",k):_norm(x) for k,x in v.items()}
    raise Reject("MALFORMED_VALUE")
def canonical(v):return json.dumps(_norm(v),ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def verify(correspondence_bytes:bytes,mutation_bytes:bytes):
    try:
        c=json.loads(correspondence_bytes.decode(),object_pairs_hook=_pairs);m=json.loads(mutation_bytes.decode(),object_pairs_hook=_pairs)
        if canonical(c)!=correspondence_bytes or canonical(m)!=mutation_bytes:raise Reject("NON_CANONICAL_ARTIFACT")
        rows=c["rows"];traces=c["traces"]
        if c.get("correspondence_version")!="NLC-CBR-CORRESPONDENCE/1.0" or len(rows)!=34 or len(traces)!=34:raise Reject("CORRESPONDENCE_CARDINALITY_INVALID")
        directions={x["direction"] for x in rows}
        if directions!={"FORMAL_TO_IMPLEMENTATION","IMPLEMENTATION_TO_FORMAL"}:raise Reject("BIDIRECTIONAL_SCOPE_MISSING")
        for row in rows:
            expected=row["expected_formal_verdict"]
            if row["actual_formal_verdict"]!=expected or row["implementation_verdict"]!=expected or row["independent_verdict"]!=expected or row["divergence"]:raise Reject("VERDICT_DIVERGENCE")
            if row["product_verdict"]=="DIVERGENCE":raise Reject("PRODUCT_DIVERGENCE")
        if c["unexplained_divergences"]!=0 or c["partial_mappings"]!=0 or c["metrics"]["double_active"]!=0 or c["metrics"]["authority_parent_edges"]!=0 or c["metrics"]["old_authority_relations"]!=0:raise Reject("CRITICAL_METRIC_VIOLATION")
        if len(m)!=9 or any(x["divergence"] or x["formal_result"]!="EXPECTED_PROPERTY_VIOLATION" or x["implementation_result"]!="EXPECTED_PROPERTY_VIOLATION" for x in m):raise Reject("MUTATION_CORRESPONDENCE_INVALID")
        return Verification("ACCEPT","ZERO_UNEXPLAINED_DIVERGENCE",len(rows),len(traces))
    except Reject as exc:return Verification("REJECT",str(exc),0,0)
    except (KeyError,TypeError,UnicodeError,json.JSONDecodeError):return Verification("REJECT","ARTIFACT_MALFORMED",0,0)
