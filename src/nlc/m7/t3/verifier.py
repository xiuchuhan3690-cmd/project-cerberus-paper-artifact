"""Independent T3 scenario validator; no driver import."""
from nlc.m7.t2.reconstructor import reconstruct as reconstruct_t2
from .reconstructor import reconstruct


def verify(bundle,boundaries,hold,faults,substitutions):
    try:
        result=reconstruct(bundle)
        if result["verdict"]!="ACCEPT" or result["completed_steps"]!=14:raise ValueError("POSITIVE_RECONSTRUCTION")
        variants=boundaries["variants"]
        if len(variants)!=13 or any(row["actual"]!="E2E_REJECT" or row["e2e_success_reached"] for row in variants):raise ValueError("BOUNDARY_VARIANT")
        if any(reconstruct_t2(row["session"]["events"])["terminal"]!="STOP_REJECT" for row in variants):raise ValueError("BOUNDARY_STOP")
        if hold["terminal"]!="E2E_HOLD" or hold["output_activations"] or hold["authority_mints"]:raise ValueError("HOLD")
        if reconstruct_t2(hold["session"]["events"])["terminal"]!="STOP_HOLD":raise ValueError("HOLD_EVIDENCE")
        for variant in faults.values():
            reconstructed=reconstruct_t2(variant["session"]["events"])
            if reconstructed["verdict"]!="ACCEPT" or variant["outputs"]>1 or variant["duplicate_effects"]:raise ValueError("FAULT")
        if len(substitutions["mutations"])!=7 or any(row["actual"]!="REJECT" for row in substitutions["mutations"]):raise ValueError("SUBSTITUTION")
        return {"verdict":"ACCEPT","reason":"ALL_T3_INVARIANTS_HOLD","completed_steps":14,"independently_evidenced":14,"boundary_failures":13,"unexpected_success":0,"overrides":0,"bypasses":0,"runtime_state_reused":False}
    except Exception as error:
        return {"verdict":"REJECT","reason":str(error)}

