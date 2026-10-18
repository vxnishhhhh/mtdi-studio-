"""The interface every store implements."""
import re


class StoreError(Exception):
    pass


_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-/ ]{0,1000}$")


def check_key(key):
    key = str(key)
    if not _KEY.match(key) or ".." in key.split("/") or key.startswith("/"):
        raise StoreError(f"invalid object key: {key!r}")
    return key


class Store:
    def put(self, key, data: bytes, content_type="application/octet-stream"):
        raise NotImplementedError

    def get(self, key) -> bytes:
        raise NotImplementedError

    def list(self, prefix=""):
        raise NotImplementedError

    def delete(self, key):
        raise NotImplementedError

    def exists(self, key):
        try:
            self.get(key)
            return True
        except StoreError:
            return False

    # text and JSON helpers shared by every store
    def put_text(self, key, text):
        return self.put(key, text.encode("utf-8"), "text/plain; charset=utf-8")

    def get_text(self, key):
        return self.get(key).decode("utf-8")

    def put_json(self, key, value):
        import json
        return self.put(key, json.dumps(value, indent=2).encode("utf-8"), "application/json")

    def get_json(self, key):
        import json
        return json.loads(self.get(key))
