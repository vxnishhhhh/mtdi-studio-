"""Client-side encryption for any store: AES-256-GCM, a fresh 96-bit nonce per object.

The provider only ever sees ciphertext. The object key (name) is authenticated as
associated data, so a stored blob cannot be swapped onto another name unnoticed.

    key = generate_key()                  # 32 random bytes; keep it in a secret manager
    os.environ["MTDI_STORAGE_KEY"] = key.hex()
    store = EncryptedStore(storage.open("s3://bucket"), key_from_env())

Needs the ``cryptography`` package (already a studio dependency).
"""
import os
import secrets

from .base import Store, StoreError

MAGIC = b"MTDI1"


def generate_key():
    return secrets.token_bytes(32)


def key_from_env(name="MTDI_STORAGE_KEY"):
    value = os.environ.get(name, "").strip()
    if not value:
        raise StoreError(f"{name} is not set (64 hex characters)")
    try:
        key = bytes.fromhex(value)
    except ValueError:
        raise StoreError(f"{name} must be hex") from None
    if len(key) != 32:
        raise StoreError(f"{name} must be 32 bytes (64 hex characters)")
    return key


class EncryptedStore(Store):
    def __init__(self, inner, key):
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            raise StoreError("encryption needs the 'cryptography' package") from None
        if len(key) != 32:
            raise StoreError("key must be 32 bytes")
        self.inner, self._aead = inner, AESGCM(key)

    def put(self, key, data, content_type="application/octet-stream"):
        nonce = secrets.token_bytes(12)
        blob = MAGIC + nonce + self._aead.encrypt(nonce, bytes(data), str(key).encode("utf-8"))
        return self.inner.put(key, blob, "application/octet-stream")

    def get(self, key):
        blob = self.inner.get(key)
        if not blob.startswith(MAGIC):
            raise StoreError(f"{key} is not an MTDI encrypted object")
        nonce, body = blob[len(MAGIC):len(MAGIC) + 12], blob[len(MAGIC) + 12:]
        try:
            return self._aead.decrypt(nonce, body, str(key).encode("utf-8"))
        except Exception:
            raise StoreError(f"{key}: wrong key or the object was altered") from None

    def list(self, prefix=""):
        return self.inner.list(prefix)

    def delete(self, key):
        return self.inner.delete(key)
