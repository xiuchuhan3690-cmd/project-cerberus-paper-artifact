"""Independent evidence/state verifier; imports no adapter implementation."""
import hashlib,json
from nlc.m6.t1.canonical import encode
SLOT="a652b78970d170b8dacc6044854c150a3e7ca2a54d5ece015c95ade0396fe765";SCOPE="effect-scope:synthetic-ledger:v1"
def verify(result):
    if result.get("verdict")=="RECOVERY_HOLD":return result.get("evidence") is None
    e=result.get("evidence");
    if not e or e.get("recovery_slot_id")!=SLOT or e.get("scope_id")!=SCOPE:return False
    core={k:e[k] for k in ("evidence_version","adapter_class","effect_id","scope_id","recovery_slot_id","terminal_state","adapter_state_version")}
    return e["evidence_commitment"]==hashlib.sha256(b"NLC-EFFECT-EVIDENCE/1.0\0"+encode(core)).hexdigest() and e["terminal_state"]==result["verdict"]
