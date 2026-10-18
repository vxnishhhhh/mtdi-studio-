"""MTDI storage: one interface for local folders and signed cloud object stores.

    from mtdi import storage
    store = storage.open("s3://my-bucket/mtdi")     # or "file:///data/mtdi", or a path
    store.put("sessions/today.jsonl", data)          # bytes
    store.get("sessions/today.jsonl")
    store.list("sessions/")
    store.delete("sessions/today.jsonl")

Encrypted at rest (AES-256-GCM, key never stored with the data):

    store = storage.encrypted(storage.open("s3://bucket"), key=storage.key_from_env())

Every S3 request is signed with AWS Signature Version 4, so the same code talks to
AWS S3, Cloudflare R2, MinIO, Backblaze B2 and any other S3-compatible service.
Credentials come only from the environment (see ``s3.S3Store.from_env``).
"""
from .base import Store, StoreError
from .local import LocalStore
from .s3 import S3Store
from .crypto import EncryptedStore, generate_key, key_from_env
from .sync import backup_project, restore_project


def open(url):  # noqa: A001  (mirrors the builtin on purpose: storage.open(url))
    """A store from a URL: s3://bucket/prefix, file:///abs/path, or a plain path."""
    text = str(url)
    if text.startswith("s3://"):
        bucket, _, prefix = text[5:].partition("/")
        return S3Store.from_env(bucket, prefix)
    if text.startswith("file://"):
        return LocalStore(text[7:])
    return LocalStore(text)


def encrypted(store, key):
    return EncryptedStore(store, key)


__all__ = ["Store", "StoreError", "LocalStore", "S3Store", "EncryptedStore", "open", "encrypted",
           "generate_key", "key_from_env", "backup_project", "restore_project"]
