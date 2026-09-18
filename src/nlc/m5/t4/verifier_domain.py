"""Independent verifier-domain barrier."""
from .canonical import decision


def verify(artifact,context):
    if artifact.get("verifier_domain_id")!=context.verifier_domain_id: return decision("VERIFIER_DOMAIN",artifact,context,"REJECT","OLD_OR_WRONG_VERIFIER_DOMAIN")
    if artifact.get("verifier_version")!=context.verifier_version: return decision("VERIFIER_DOMAIN",artifact,context,"REJECT","VERIFIER_VERSION_MISMATCH")
    return decision("VERIFIER_DOMAIN",artifact,context,"PASS","VERIFIER_DOMAIN_BOUND")
