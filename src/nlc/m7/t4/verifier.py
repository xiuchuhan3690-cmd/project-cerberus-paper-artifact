"""Independent Gate C verifier; imports no Gate C generator or aggregation code."""

PROPERTIES={"TC-1","TC-2","TC-3","TC-4","TC-7","NTC-1","NTC-2","NTC-3"}
LABELS={"BOUNDED_VERIFIED","IMPLEMENTATION_CORRESPONDENT_WITHIN_FROZEN_MODEL"}
MANDATORY={"CB-1","CB-2","CB-3","CB-4","CB-5"}


def verify(composition,properties,nonvacuity,bidirectional,cross_boundary,negative,bypass,preservation,constructor,claim,metrics):
    try:
        rows=properties["rows"]
        if {row["property"] for row in rows}!=PROPERTIES or len(rows)!=8:raise ValueError("PROPERTY_SET")
        if any(row["precondition_reach_count"]<=0 or row["final_label"] not in LABELS or row["integrated"]!="PASS" or row["correspondence_divergence"] for row in rows):raise ValueError("PROPERTY_STATUS")
        if {row["property"] for row in composition["rows"]}!=PROPERTIES or any(row["mapping"]!="COMPLETE" for row in composition["rows"]):raise ValueError("COMPOSITION_MAP")
        if nonvacuity["preconditions_reached"]!=8 or nonvacuity["vacuous_passes"] or nonvacuity["zero_reach_properties"]:raise ValueError("VACUITY")
        if bidirectional["unexplained_divergences"] or bidirectional["partial_decision_critical_mappings"]:raise ValueError("CORRESPONDENCE")
        tests=cross_boundary["tests"]
        if {row["test_id"] for row in tests}!=MANDATORY or any(row["actual"]!="BLOCKED" or row["unexpected_survival"] for row in tests):raise ValueError("CROSS_BOUNDARY")
        if negative["unexpected_survivors"] or negative["unmapped_mutations"] or negative["missing_expected_failures"]:raise ValueError("NEGATIVE_MATRIX")
        if any(bypass[key] for key in ("bypass_edges","undocumented_decision_critical_edges","verifier_boundary_omissions")):raise ValueError("BYPASS")
        if any(preservation[key] for key in ("hold_overrides","reject_overrides","disagreement_overrides","hidden_acceptance_paths")):raise ValueError("OVERRIDE")
        if constructor["constructor_semantics_bypassed"] or constructor["decision_critical_ambiguity"] or not constructor["m5_t2_evidence_included"]:raise ValueError("CONSTRUCTOR")
        if claim["new_owned_mechanisms"] or claim["boundary_ambiguity"] or claim["m8_work_introduced"]:raise ValueError("CLAIM")
        if metrics["properties_evaluated"]!=8 or metrics["bounded_correspondent_count"]!=8 or metrics["hold_count"] or metrics["falsified_count"]:raise ValueError("METRICS")
        return {"verdict":"ACCEPT","reason":"GATE_C_INVARIANTS_HOLD","properties":"8/8","preconditions":"8/8","cross_boundary":"5/5","vacuous_passes":0,"divergences":0,"bypasses":0,"runtime_or_aggregator_imported":False}
    except Exception as error:
        return {"verdict":"REJECT","reason":str(error)}

