import hashlib


def generate_proof(answer, finalization_block, runtime_id):
    payload = f"{answer or ''}{finalization_block or ''}{runtime_id or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
