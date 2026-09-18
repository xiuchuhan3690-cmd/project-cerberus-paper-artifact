"""Independent finite synthetic cryptographic-root barrier."""
from .canonical import SIGNATURE_TAG,decision,signature_material,tagged_hash


def verify(artifact,context):
    if artifact.get("cryptographic_root_id")!=context.cryptographic_root_id: return decision("CRYPTOGRAPHIC_ROOT",artifact,context,"REJECT","OLD_OR_WRONG_CRYPTOGRAPHIC_ROOT")
    if artifact.get("synthetic_signature")!=tagged_hash(SIGNATURE_TAG,signature_material(artifact)): return decision("CRYPTOGRAPHIC_ROOT",artifact,context,"REJECT","SYNTHETIC_SIGNATURE_INVALID")
    return decision("CRYPTOGRAPHIC_ROOT",artifact,context,"PASS","CRYPTOGRAPHIC_ROOT_BOUND")
