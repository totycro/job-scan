import time
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from evaluations.auth_transfer import export, prepare, receive
from job_scan.auth import PERMISSION, Account, ChatGPTSession


def test_encrypted_handoff_preserves_vm_identity(tmp_path: Path) -> None:
    sender = ChatGPTSession(tmp_path / "sender")
    receiver = ChatGPTSession(tmp_path / "receiver")
    shared = tmp_path / "shared"
    synthetic = "test-only-transfer-credential"
    with sender.locked():
        store = sender.load()
        store.accounts["issued"] = Account(
            client_id="issued",
            subject="test",
            label="Test",
            access_token=synthetic,
            refresh_token=synthetic,
            scopes=[PERMISSION],
            expires_at=time.time() + 3600,
        )
        store.active = "issued"
        sender.save(store)
    prepare(receiver, shared)
    vm_host = receiver.load().host_id
    assert vm_host != sender.load().host_id
    export(sender, shared)
    envelope = (shared / "credentials.enc.json").read_text()
    assert synthetic not in envelope
    assert (receiver.directory / "transfer-private.key").stat().st_mode & 0o777 == 0o600
    receive(receiver, shared)
    assert receiver.load().host_id == vm_host
    assert receiver.access_token() == synthetic
    assert receiver.load().accounts["issued"].refresh_token == synthetic
    assert not list(shared.iterdir())
    assert not (receiver.directory / "transfer-private.key").exists()


def test_wrong_recipient_rejected() -> None:
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    from evaluations.auth_transfer import derive

    first = X25519PrivateKey.generate()
    second = X25519PrivateKey.generate()
    third = X25519PrivateKey.generate()
    nonce = b"012345678901"
    cipher = AESGCM(derive(first, second.public_key().public_bytes_raw())).encrypt(
        nonce, b"fake", b"job"
    )
    with pytest.raises(InvalidTag):
        AESGCM(derive(third, first.public_key().public_bytes_raw())).decrypt(nonce, cipher, b"job")
