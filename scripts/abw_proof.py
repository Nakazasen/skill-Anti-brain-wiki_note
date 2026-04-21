import hmac
import json
import os
from hashlib import sha256
from pathlib import Path
from secrets import token_hex


DEFAULT_SECRET_PATH = Path.home() / ".abw" / "runner_proof_key"


def _secret_path():
    configured = os.environ.get("ABW_RUNNER_SECRET_FILE", "").strip()
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_SECRET_PATH


def load_secret_key():
    env_secret = os.environ.get("ABW_RUNNER_SECRET", "").strip()
    if env_secret:
        return env_secret

    secret_path = _secret_path()
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    if not secret_path.exists():
        secret_path.write_text(token_hex(32), encoding="utf-8")
        try:
            os.chmod(secret_path, 0o600)
        except OSError:
            pass
    return secret_path.read_text(encoding="utf-8").strip()


def new_nonce():
    return token_hex(16)


def used_nonces_path(workspace="."):
    return Path(workspace) / ".brain" / "used_nonces.json"


def load_used_nonces(workspace="."):
    path = used_nonces_path(workspace)
    if not path.exists():
        return {"nonces": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {"nonces": []}
    nonces = payload.get("nonces")
    if not isinstance(nonces, list):
        nonces = []

    normalized = []
    for item in nonces:
        if isinstance(item, dict):
            nonce = str(item.get("nonce") or "").strip()
            runtime_id = str(item.get("runtime_id") or "").strip()
        else:
            nonce = str(item).strip()
            runtime_id = ""
        if nonce:
            normalized.append({"nonce": nonce, "runtime_id": runtime_id})
    return {"nonces": normalized}


def nonce_is_used(nonce, runtime_id="", workspace="."):
    payload = load_used_nonces(workspace)
    needle = {"nonce": str(nonce or ""), "runtime_id": str(runtime_id or "")}
    return needle in payload.get("nonces", [])


def mark_nonce_used(nonce, runtime_id="", workspace="."):
    nonce = str(nonce or "").strip()
    runtime_id = str(runtime_id or "").strip()
    if not nonce:
        return False

    path = used_nonces_path(workspace)
    payload = load_used_nonces(workspace)
    entry = {"nonce": nonce, "runtime_id": runtime_id}
    nonces = payload.get("nonces", [])
    if entry in nonces:
        return False

    nonces.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"nonces": nonces}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return True


def proof_payload(answer, finalization_block, runtime_id, nonce, binding_source):
    return (
        f"{answer or ''}"
        f"{finalization_block or ''}"
        f"{runtime_id or ''}"
        f"{nonce or ''}"
        f"{binding_source or ''}"
    )


def generate_proof(answer, finalization_block, runtime_id, nonce, binding_source):
    secret_key = load_secret_key()
    payload = proof_payload(answer, finalization_block, runtime_id, nonce, binding_source)
    return hmac.new(
        secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        sha256,
    ).hexdigest()


def verify_proof(proof, answer, finalization_block, runtime_id, nonce, binding_source):
    expected = generate_proof(answer, finalization_block, runtime_id, nonce, binding_source)
    return hmac.compare_digest(str(proof or ""), expected)
