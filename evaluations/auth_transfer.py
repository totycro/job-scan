"""Encrypted one-time handoff of the active job-scan registration to a worker VM."""

import argparse
import base64
import os
from pathlib import Path
from typing import Literal

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from job_scan.auth import Account, ChatGPTSession
from job_scan.models import Model

CONTEXT = b"job-scan VM credential handoff v1"
DEFAULT_DIRECTORY = Path(".local/auth-transfer")


class Recipient(Model):
    version: Literal[1] = 1
    public_key: str


class Envelope(Model):
    version: Literal[1] = 1
    public_key: str
    nonce: str
    ciphertext: str


def encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def decode(value: str) -> bytes:
    return base64.b64decode(value, validate=True)


def derive(private: X25519PrivateKey, public: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=CONTEXT).derive(
        private.exchange(X25519PublicKey.from_public_bytes(public))
    )


def prepare(session: ChatGPTSession, directory: Path) -> None:
    private = X25519PrivateKey.generate()
    with session.locked():
        session.save(session.load())  # Persist the VM's own stable host ID first.
        key_path = session.directory / "transfer-private.key"
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(private.private_bytes_raw())
    directory.mkdir(parents=True, exist_ok=True)
    public = Recipient(public_key=encode(private.public_key().public_bytes_raw()))
    (directory / "recipient.json").write_text(public.model_dump_json(indent=2) + "\n")


def export(session: ChatGPTSession, directory: Path) -> None:
    recipient = Recipient.model_validate_json((directory / "recipient.json").read_bytes())
    session.access_token()  # Refresh locally before handing later refreshes to the VM.
    with session.locked():
        store = session.load()
        account = store.accounts.get(store.active or "")
        if account is None:
            raise ValueError("No active job-scan registration.")
        plaintext = account.model_dump_json().encode()
    ephemeral = X25519PrivateKey.generate()
    nonce = os.urandom(12)
    encrypted = AESGCM(derive(ephemeral, decode(recipient.public_key))).encrypt(
        nonce, plaintext, CONTEXT
    )
    envelope = Envelope(
        public_key=encode(ephemeral.public_key().public_bytes_raw()),
        nonce=encode(nonce),
        ciphertext=encode(encrypted),
    )
    (directory / "credentials.enc.json").write_text(envelope.model_dump_json(indent=2) + "\n")


def receive(session: ChatGPTSession, directory: Path) -> None:
    key_path = session.directory / "transfer-private.key"
    private = X25519PrivateKey.from_private_bytes(key_path.read_bytes())
    encrypted_path = directory / "credentials.enc.json"
    envelope = Envelope.model_validate_json(encrypted_path.read_bytes())
    plaintext = AESGCM(derive(private, decode(envelope.public_key))).decrypt(
        decode(envelope.nonce), decode(envelope.ciphertext), CONTEXT
    )
    account = Account.model_validate_json(plaintext)
    with session.locked():
        store = session.load()  # Keep the VM host ID, never the sender's host ID.
        prior = store.accounts.get(account.client_id)
        if prior is not None and prior.subject != account.subject:
            raise ValueError("Registration belongs to another account.")
        store.accounts[account.client_id] = account
        store.active = account.client_id
        session.save(store)
    encrypted_path.unlink()
    key_path.unlink()
    (directory / "recipient.json").unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "export", "import"])
    parser.add_argument("--directory", type=Path, default=DEFAULT_DIRECTORY)
    args = parser.parse_args(argv)
    with ChatGPTSession() as session:
        if args.action == "prepare":
            prepare(session, args.directory)
        elif args.action == "export":
            export(session, args.directory)
        else:
            receive(session, args.directory)
    print(f"Credential handoff {args.action} complete; no credential values were printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
