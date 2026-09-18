"""Independent XREC record verifier; imports no protocol/store code."""
import hashlib
from nlc.m6.t1.canonical import decode,encode
SLOT="a652b78970d170b8dacc6044854c150a3e7ca2a54d5ece015c95ade0396fe765";OUTPUT="a41a693cf18e91258de6e13fdc67c9184961264d7a08577b0e3e1d1c64d8aaba";ROOT="d38cab52600953a65aadebf1eb61bbc925d4957e1d8dfcb175eb2e6705affb3b"
def verify(raw):
 try:
  r=decode(raw);q=r["receipt"]
  if r["state"]!="COMMITTED" or r["slot_state"]!="CONSUMED" or r["output_state"]!="ACTIVE" or r["recovery_slot_id"]!=SLOT or r["output_set_id"]!=OUTPUT:return False
  if r["output_activation_count"]!=1 or r["effective_effect_count"]!=1 or r["old_capability_reissue_count"] or r["old_authority_parent_edges"]:return False
  if q["active_root_id"]!=ROOT or q["recovery_slot_id"]!=SLOT or q["output_set_id"]!=OUTPUT:return False
  core={k:q[k] for k in q if k!="receipt_id"};return q["receipt_id"]==hashlib.sha256(b"NLC-XREC-RECEIPT/1.0\0"+encode(core)).hexdigest()
 except Exception:return False
