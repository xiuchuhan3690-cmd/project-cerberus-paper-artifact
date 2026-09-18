"""Independent typed graph verifier. Imports no T1 constructor or T3 protocol."""
from dataclasses import dataclass
import hashlib,json,unicodedata
ROOT="d38cab52600953a65aadebf1eb61bbc925d4957e1d8dfcb175eb2e6705affb3b";SLOT="a652b78970d170b8dacc6044854c150a3e7ca2a54d5ece015c95ade0396fe765";RECEIPT="f03af35c7ff21a3ddd4fa588db15eb92eee2b9c4bd41277606a0d3165d993611";OUTPUT_SET="a41a693cf18e91258de6e13fdc67c9184961264d7a08577b0e3e1d1c64d8aaba";OUTPUTS={"14636ebe93ac9249463ba8fe59b83fe39edf846d9649353aabf7b523da86e12c","fdf03c869a164c7e2d173a85546fa28f26856027aa9821f91d667e4bb56dbb0f"};CHECKPOINT="d76202a4158d19dc5bdf7b332970267b520e1f874173feb72a43277a3c335ef2";EFFECT="28de6909cdd116d57ca19a06eb548773b05170af5bffdadde2c1057e49061825"
NODES={"OLD_AUTHORITY","NEW_ROOT","RECOVERY_OUTPUT","CHECKPOINT_FACT","EFFECT_EVIDENCE","XREC_RECEIPT","RECOVERY_SLOT"};EDGES={"DATA_PROVENANCE","EFFECT_PROVENANCE","RECOVERY_PROVENANCE","AUTHORITY_PARENT"}
@dataclass(frozen=True)
class Verdict:verdict:str;reason:str;retry_classification:str="NONE"
def enc(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def verify(raw):
 try:
  p=json.loads(raw);core={k:p[k] for k in p if k!="proof_id"}
  if set(p)!={"lineage_version","recovery_slot_id","xrec_receipt_id","output_set_id","recovered_output_ids","active_root_id","target_domain","target_epoch","checkpoint_provenance_commitment","sterility_proof_commitment","effect_provenance_commitment","nodes","edges","retry","proof_id"}:raise ValueError("PROOF_FIELDS")
  if p["proof_id"]!=hashlib.sha256(b"NLC-XREC-LINEAGE-PROOF/1.0\0"+enc(core)).hexdigest():raise ValueError("PROOF_ID")
  if (p["recovery_slot_id"],p["xrec_receipt_id"],p["output_set_id"],p["active_root_id"],p["target_domain"],p["target_epoch"])!=(SLOT,RECEIPT,OUTPUT_SET,ROOT,"D_1",1):raise ValueError("FROZEN_BINDING")
  if set(p["recovered_output_ids"])!=OUTPUTS or p["checkpoint_provenance_commitment"]!=CHECKPOINT or p["effect_provenance_commitment"]!=EFFECT or p["sterility_proof_commitment"]!="343c64c5f50509d8334246e28eb32a38ca7e90d8ce114a8f9d1bfa940b36bd7d":raise ValueError("PROVENANCE_BINDING")
  nodes={n["id"]:n["type"] for n in p["nodes"]}
  if len(nodes)!=len(p["nodes"]) or any(t not in NODES for t in nodes.values()) or "OLD_AUTHORITY" in nodes.values():raise ValueError("NODE_TYPE")
  parents={x:[] for x in OUTPUTS};seen=set()
  for e in p["edges"]:
   if set(e)!={"source","target","type"} or e["type"] not in EDGES or e["source"] not in nodes or e["target"] not in nodes:raise ValueError("EDGE_TYPE")
   key=(e["source"],e["target"],e["type"])
   if key in seen:raise ValueError("DUPLICATE_EDGE")
   seen.add(key);s,t=nodes[e["source"]],nodes[e["target"]]
   allowed={"DATA_PROVENANCE":("CHECKPOINT_FACT","RECOVERY_OUTPUT"),"EFFECT_PROVENANCE":("EFFECT_EVIDENCE","RECOVERY_OUTPUT"),"RECOVERY_PROVENANCE":({"RECOVERY_SLOT","XREC_RECEIPT"},"RECOVERY_OUTPUT"),"AUTHORITY_PARENT":("NEW_ROOT","RECOVERY_OUTPUT")}[e["type"]]
   if not ((s in allowed[0]) if isinstance(allowed[0],set) else s==allowed[0]) or t!=allowed[1]:raise ValueError("EDGE_SEMANTICS")
   if e["type"]=="AUTHORITY_PARENT":parents[e["target"]].append(e["source"])
  if any(v!=[ROOT] for v in parents.values()):raise ValueError("NEW_ROOT_ANCESTRY")
  retry=p["retry"]
  if set(retry)!={"attempts","classification","mint_event_count","divergent_output_ids"}:raise ValueError("RETRY_FIELDS")
  if retry["attempts"] and (retry["classification"]!="RETRIEVAL" or retry["mint_event_count"] or retry["divergent_output_ids"]):raise ValueError("RETRY_NOT_RETRIEVAL")
  return Verdict("ACCEPT","LINEAGE_VALID",retry["classification"])
 except Exception as e:return Verdict("REJECT",str(e))
def verify_hold(raw):
 try:
  p=json.loads(raw);ok=p["outcome"]=="HOLD" and p["active_output_ids"]==[] and p["authority_edges"]==[] and p["new_mint_count"]==0 and p["effect_provenance_commitment"]=="UNOBSERVABLE";return Verdict("ACCEPT" if ok else "REJECT","HOLD_VALID" if ok else "HOLD_INVALID")
 except Exception:return Verdict("REJECT","HOLD_MALFORMED")
