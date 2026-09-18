"""Independent namespace barrier."""
from .canonical import decision


def verify(artifact,context):
    if artifact.get("namespace_id")!=context.namespace_id: return decision("NAMESPACE",artifact,context,"REJECT","OLD_OR_WRONG_NAMESPACE")
    if artifact.get("namespace_version")!=context.namespace_version: return decision("NAMESPACE",artifact,context,"REJECT","NAMESPACE_VERSION_MISMATCH")
    return decision("NAMESPACE",artifact,context,"PASS","NAMESPACE_BOUND")
