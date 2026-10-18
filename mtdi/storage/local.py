"""A folder on disk as a store. Writes are atomic (temporary file, then rename)."""
import os
import pathlib

from .base import Store, StoreError, check_key


class LocalStore(Store):
    def __init__(self, root):
        self.root = pathlib.Path(root).expanduser().resolve()

    def _path(self, key):
        path = (self.root / check_key(key)).resolve()
        if self.root not in path.parents and path != self.root:
            raise StoreError(f"key escapes the store: {key!r}")
        return path

    def put(self, key, data, content_type="application/octet-stream"):
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
        tmp.write_bytes(bytes(data))
        tmp.replace(path)
        return {"key": key, "bytes": len(data)}

    def get(self, key):
        try:
            return self._path(key).read_bytes()
        except FileNotFoundError:
            raise StoreError(f"no such object: {key}") from None

    def list(self, prefix=""):
        if not self.root.exists():
            return []
        out = []
        for p in sorted(self.root.rglob("*")):
            if p.is_file() and not p.name.endswith(".tmp"):
                key = p.relative_to(self.root).as_posix()
                if key.startswith(prefix):
                    out.append({"key": key, "bytes": p.stat().st_size})
        return out

    def delete(self, key):
        try:
            self._path(key).unlink()
        except FileNotFoundError:
            raise StoreError(f"no such object: {key}") from None
