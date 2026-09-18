"""Finite synthetic M6-T1 fixtures."""

from __future__ import annotations
from copy import deepcopy
from .canonical import digest
from .model import *

def baseline():
    facts=[{"fact_id":"checkpoint:account:alpha","provenance_ref":"sterile-native:v1:alpha","value":{"balance":7,"status":"READY"}},{"fact_id":"checkpoint:account:beta","provenance_ref":"sterile-native:v1:beta","value":{"balance":11,"status":"READY"}}]
    commitment=digest(b"NLC-STERILE-CHECKPOINT/1.0\x00",sorted(facts,key=lambda x:(x["fact_id"],x["provenance_ref"])))
    material={"recovery_protocol_version":RECOVERY_PROTOCOL_VERSION,"target_domain":TARGET_DOMAIN,"target_epoch":TARGET_EPOCH,"accepted_reconstitution_identity":CERTIFICATE_ID,"active_root_id":ACTIVE_ROOT_ID,"cutover_slot_id":CUTOVER_SLOT_ID,"cutover_receipt_id":CUTOVER_RECEIPT_ID,"cutover_receipt_sha256":CUTOVER_RECEIPT_SHA256,"sterile_checkpoint_identity":facts,"checkpoint_commitment":commitment,"sterility_proof":{"artifact_version":STERILITY_ARTIFACT_VERSION,"artifact_sha256":STERILITY_ARTIFACT_SHA256,"artifact_commit":STERILITY_ARTIFACT_COMMIT,"eligibility":"STERILITY_ARTIFACT_FOR_M5_FROZEN"},"effect_scope_identity":"effect-scope:synthetic-ledger:v1","settlement_context":{"state":"FENCED","proof_identity":"8"*64,"fence_context":"synthetic-fence:recovery-001"},"output_construction_version":OUTPUT_CONSTRUCTION_VERSION,"recovery_request_identity":"recovery-request:checkpoint-001"}
    authority={"domain":TARGET_DOMAIN,"epoch":TARGET_EPOCH,"authority_parent_root_id":ACTIVE_ROOT_ID,"old_authority_parent_edges":[]}
    templates=[{"semantic_key":"account:beta","payload":{"restored_balance":11},"authority_template":deepcopy(authority),"lost_capability_ids":[]},{"semantic_key":"account:alpha","payload":{"restored_balance":7},"authority_template":deepcopy(authority),"lost_capability_ids":[]}]
    return material,templates
