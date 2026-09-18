"""Frozen constants and exact material shapes for M6-T1."""

RECOVERY_PROTOCOL_VERSION = "NLC-RECOVERY-SLOT/1.0"
OUTPUT_CONSTRUCTION_VERSION = "NLC-DETERMINISTIC-RECOVERY-OUTPUT/1.0"
RECEIPT_VERSION = "NLC-RECOVERY-RESULT/1.0"
SLOT_DOMAIN = b"NLC-RECOVERY-SLOT-ID/1.0\x00"
OUTPUT_DOMAIN = b"NLC-RECOVERY-OUTPUT-ID/1.0\x00"
OUTPUT_SET_DOMAIN = b"NLC-RECOVERY-OUTPUT-SET-ID/1.0\x00"
RECEIPT_DOMAIN = b"NLC-RECOVERY-RESULT-ID/1.0\x00"

TARGET_DOMAIN = "D_1"
TARGET_EPOCH = 1
CERTIFICATE_ID = "378f78ba32f022c87ae06a5e0ba5f78dce00bcbe17c3d25e8ad236ee56208f71"
ACTIVE_ROOT_ID = "d38cab52600953a65aadebf1eb61bbc925d4957e1d8dfcb175eb2e6705affb3b"
CUTOVER_SLOT_ID = "ebbc6613560103ac2d9b4b99c609aec807c932f0af73fbf3ef7c35065af7091e"
CUTOVER_RECEIPT_ID = "1bce312db818a2f1c9ddf63297ebe54f4738fa8ee1e038d441c25731ae85500c"
CUTOVER_RECEIPT_SHA256 = "c202b5b172c9b23291786cf9752c6ca1b39655804bbf7c2d6b3c6624fc28de8a"
STERILITY_ARTIFACT_VERSION = "NLC-M3-STERILITY-ARTIFACT-FOR-M5/1.0"
STERILITY_ARTIFACT_SHA256 = "343c64c5f50509d8334246e28eb32a38ca7e90d8ce114a8f9d1bfa940b36bd7d"
STERILITY_ARTIFACT_COMMIT = "c8dedc7f03c2e9c3607737b66f971a69ff768c23"

SLOT_FIELDS = frozenset({"recovery_protocol_version","target_domain","target_epoch","accepted_reconstitution_identity","active_root_id","cutover_slot_id","cutover_receipt_id","cutover_receipt_sha256","sterile_checkpoint_identity","checkpoint_commitment","sterility_proof","effect_scope_identity","settlement_context","output_construction_version","recovery_request_identity"})
STATES = frozenset({"UNUSED","PREPARED","CONSUMED","HOLD"})
