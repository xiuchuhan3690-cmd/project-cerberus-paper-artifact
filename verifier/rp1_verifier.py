"""Independent RP1 closure verifier; it does not import package generators."""

PROPERTIES = ("TC-1", "TC-2", "TC-3", "TC-4", "TC-7", "NTC-1", "NTC-2", "NTC-3")
REQUIRED_GATES = ("Gate A", "Gate B", "Sterility", "AIM", "Cutover", "Recovery", "Gate C", "Gate D", "M8-T3")
REQUIRED_LIMITATIONS = (
    "bounded finite formal domains",
    "synthetic attack/fault corpus",
    "no real-world offensive/red-team validation",
    "finite transform inventory",
    "finite influence inventory",
    "external-effect adapter realism limitation",
    "single/local fixture abstractions",
    "production KMS/HSM excluded",
    "production distributed consensus excluded",
    "production scale not established",
    "M8-T3 transform state-space explosion",
    "28/7 transform variant resource-limited",
    "toolchain/specification common-mode risk",
    "larger variants do not prove enterprise scalability",
)


def verify(provenance, gates, demos, properties, limitations, claim, package):
    findings = []
    if provenance.get("mismatches") != 0 or provenance.get("verified_nodes") != provenance.get("total_nodes"):
        findings.append("PROVENANCE")
    gate_rows = gates.get("rows", [])
    if tuple(row.get("gate") for row in gate_rows) != REQUIRED_GATES or any(row.get("verification") != "VERIFIED" for row in gate_rows):
        findings.append("GATES")
    if demos.get("attempted") != 9 or demos.get("independently_evidenced") != 9 or demos.get("reconstructable") != 9:
        findings.append("DEMOS")
    if any(demo.get("verdict") != "PASS" or demo.get("replay") != "IDENTICAL" for demo in demos.get("demos", [])):
        findings.append("DEMO_VERDICTS")
    if any(demos.get(key) != 0 for key in ("unexpected_bypass", "missing_decision_critical_evidence", "invariant_violations", "verifier_overrides", "replay_mismatches", "scientific_nondeterminism")):
        findings.append("DEMO_METRICS")
    property_rows = properties.get("rows", [])
    if tuple(row.get("property") for row in property_rows) != PROPERTIES or any(row.get("contradiction") or not row.get("nonvacuous") for row in property_rows):
        findings.append("PROPERTIES")
    limitation_names = tuple(row.get("limitation") for row in limitations.get("rows", []))
    if limitation_names != REQUIRED_LIMITATIONS or limitations.get("contradicts_bounded_claim"):
        findings.append("LIMITATIONS")
    if claim.get("scientific_semantics_changed") or claim.get("claim_boundary_changed") or claim.get("new_owned_mechanisms") != 0 or claim.get("production_or_universal_expansion"):
        findings.append("CLAIM")
    if package.get("package_id") != "NLC-RP1" or package.get("version") != "1.0" or package.get("missing_required_references") != 0:
        findings.append("PACKAGE")
    return {
        "version": "NLC-RP1-INDEPENDENT-VERIFIER/1.0",
        "verdict": "ACCEPT" if not findings else "REJECT",
        "findings": findings,
        "hashes_checked": provenance.get("total_nodes", 0),
        "gates_recomputed": len(gate_rows),
        "demos_recomputed": len(demos.get("demos", [])),
        "properties_recomputed": len(property_rows),
    }
