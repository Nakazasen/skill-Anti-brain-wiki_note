import hmac
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
