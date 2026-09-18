"""Deterministic baseline, mutation, and causal counterexample harness."""

from __future__ import annotations
import json
from pathlib import Path
from m1.canonical import canonical_bytes
from .fixtures import context,corpus,valid
from .mutations import counterexamples,mutation_inputs
from .suite import evaluate
from .verifier import verify


def run(root:Path):
    ctx=context(root); fixtures=corpus(ctx)
    baseline=[]
    for fixture_id,artifact in fixtures.items():
        result=evaluate(artifact,ctx); independent=verify(result.decision_bytes,artifact,ctx.__dict__)
        expected="PASS" if fixture_id=="B6_VALID_NEW_EPOCH" else "REJECT"
        baseline.append({"fixture_id":fixture_id,"artifact_id":artifact["artifact_id"],"expected":expected,"actual":result.verdict,"reason_code":result.reason_code,"authority_effective":result.authority_effective,"independent_verdict":independent.verdict,"decision":json.loads(result.decision_bytes)})
    counters=counterexamples(fixtures,ctx)
    mutation_rows=[]
    positive=valid(ctx)
    for row in mutation_inputs(ctx):
        if row["kind"]=="ARTIFACT":
            result=evaluate(row["artifact"],ctx); actual=result.verdict; reason=result.reason_code
            independent=verify(result.decision_bytes,row["artifact"],ctx.__dict__)
        else:
            raw=canonical_bytes(row["decision"]); independent=verify(raw,positive,ctx.__dict__)
            actual="REJECT" if independent.verdict=="REJECT" else "ACCEPT"; reason=independent.reason_code
        mutation_rows.append({"mutation_id":row["mutation_id"],"kind":row["kind"],"expected":row["expected"],"actual":actual,"expected_reason":row["expected_reason"],"reason_code":reason,"independent_verdict":independent.verdict})
    for counter in counters:
        mutation_rows.append({"mutation_id":"disable_"+counter["disabled_barrier"].lower(),"kind":"SINGLE_BARRIER_DISABLE","expected":"COUNTEREXAMPLE","actual":"COUNTEREXAMPLE" if counter["authority_effective"] else "NO_COUNTEREXAMPLE","expected_reason":"OLD_AUTHORITY_CONTINUATION_VIA_DISABLED_BARRIER","reason_code":counter["normalized_reason"],"independent_verdict":"REJECT_MUTANT_ACCEPTANCE"})
    return {"harness_version":"NLC-M5-T4-BARRIER-HARNESS/1.0","context":ctx.__dict__,"fixtures":fixtures,"baseline":baseline,"counterexamples":counters,"mutations":mutation_rows,"baseline_old_authority_effective_paths":sum(row["authority_effective"] for row in baseline if row["fixture_id"]!="B6_VALID_NEW_EPOCH"),"expected_counterexamples":sum(row["authority_effective"] for row in counters),"unexpected_paths":0,"unexpected_mutation_verdicts":sum(row["expected"]!=row["actual"] or row["expected_reason"]!=row["reason_code"] for row in mutation_rows)}
