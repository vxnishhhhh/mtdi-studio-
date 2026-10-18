"""S3-compatible object storage with AWS Signature Version 4, standard library only.

Works with AWS S3, Cloudflare R2, MinIO, Backblaze B2 and other S3-compatible services.

Environment (never written anywhere by MTDI):

    MTDI_S3_ACCESS_KEY_ID      (or AWS_ACCESS_KEY_ID)
    MTDI_S3_SECRET_ACCESS_KEY  (or AWS_SECRET_ACCESS_KEY)
    MTDI_S3_REGION             (or AWS_REGION; default us-east-1, "auto" for R2)
    MTDI_S3_ENDPOINT           optional, e.g. https://<account>.r2.cloudflarestorage.com
                               or http://localhost:9000 for MinIO. Default: AWS.
    MTDI_S3_SESSION_TOKEN      optional (temporary AWS credentials)
"""
import datetime
import hashlib
import hmac
import os
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .base import Store, StoreError, check_key

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def _hmac(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def signing_key(secret, date, region, service="s3"):
    k = _hmac(("AWS4" + secret).encode("utf-8"), date)
    k = _hmac(k, region)
    k = _hmac(k, service)
    return _hmac(k, "aws4_request")


def _quote(text, safe="-_.~"):
    return urllib.parse.quote(text, safe=safe)


def sign(method, url, headers, payload_hash, access_key, secret, region, now=None, service="s3"):
    """Return the headers to send, with x-amz-date, x-amz-content-sha256 and Authorization.

    Follows the AWS SigV4 specification: canonical request, string to sign, derived key.
    """
    now = now or datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date = now.strftime("%Y%m%d")
    parts = urllib.parse.urlsplit(url)
    host = parts.netloc
    out = {k.lower(): str(v).strip() for k, v in headers.items()}
    out.update({"host": host, "x-amz-date": amz_date, "x-amz-content-sha256": payload_hash})
    canonical_uri = _quote(urllib.parse.unquote(parts.path or "/"), safe="/-_.~")
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    canonical_query = "&".join(f"{_quote(k)}={_quote(v)}" for k, v in sorted(query))
    signed = sorted(out)
    canonical_headers = "".join(f"{k}:{' '.join(out[k].split())}\n" for k in signed)
    signed_headers = ";".join(signed)
    canonical_request = "\n".join([method, canonical_uri, canonical_query, canonical_headers,
                                   signed_headers, payload_hash])
    scope = f"{date}/{region}/{service}/aws4_request"
    string_to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope,
                                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()])
    signature = hmac.new(signing_key(secret, date, region, service), string_to_sign.encode("utf-8"),
                         hashlib.sha256).hexdigest()
    out["authorization"] = (f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
                            f"SignedHeaders={signed_headers}, Signature={signature}")
    return out


class S3Store(Store):
    def __init__(self, bucket, prefix="", access_key=None, secret_key=None, region="us-east-1",
                 endpoint=None, session_token=None, path_style=None):
        if not access_key or not secret_key:
            raise StoreError("S3 credentials missing: set MTDI_S3_ACCESS_KEY_ID and MTDI_S3_SECRET_ACCESS_KEY")
        self.bucket, self.prefix = bucket, prefix.strip("/")
        self.access_key, self.secret_key, self.region = access_key, secret_key, region
        self.session_token = session_token
        self.endpoint = (endpoint or "").rstrip("/")
        # A custom endpoint (MinIO, R2, a test server) uses path-style URLs; AWS uses virtual hosts.
        self.path_style = bool(self.endpoint) if path_style is None else path_style

    @classmethod
    def from_env(cls, bucket, prefix=""):
        env = os.environ.get
        return cls(bucket, prefix,
                   access_key=env("MTDI_S3_ACCESS_KEY_ID") or env("AWS_ACCESS_KEY_ID"),
                   secret_key=env("MTDI_S3_SECRET_ACCESS_KEY") or env("AWS_SECRET_ACCESS_KEY"),
                   region=env("MTDI_S3_REGION") or env("AWS_REGION") or "us-east-1",
                   endpoint=env("MTDI_S3_ENDPOINT"),
                   session_token=env("MTDI_S3_SESSION_TOKEN") or env("AWS_SESSION_TOKEN"))

    def _url(self, key="", query=""):
        path = "/" + _quote(key, safe="/-_.~") if key else "/"
        if self.path_style:
            base = f"{self.endpoint or 'https://s3.amazonaws.com'}/{self.bucket}"
        else:
            host = "s3.amazonaws.com" if self.region == "us-east-1" else f"s3.{self.region}.amazonaws.com"
            base = f"https://{self.bucket}.{host}"
        return base + path + (("?" + query) if query else "")

    def _full(self, key):
        key = check_key(key)
        return f"{self.prefix}/{key}" if self.prefix else key

    def _request(self, method, url, body=b"", headers=None):
        payload_hash = hashlib.sha256(body).hexdigest() if body else EMPTY_SHA256
        h = dict(headers or {})
        if self.session_token:
            h["x-amz-security-token"] = self.session_token
        signed = sign(method, url, h, payload_hash, self.access_key, self.secret_key, self.region)
        signed.pop("host", None)       # urllib sets Host itself, from the same URL
        request = urllib.request.Request(url, data=body if method in ("PUT", "POST") else None,
                                         headers=signed, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as error:
            detail = error.read()[:300].decode("utf-8", "replace")
            if error.code == 404:
                raise StoreError(f"not found: {url}") from None
            raise StoreError(f"S3 {method} failed ({error.code}): {detail}") from None
        except urllib.error.URLError as error:
            raise StoreError(f"S3 unreachable: {error.reason}") from None

    def put(self, key, data, content_type="application/octet-stream"):
        data = bytes(data)
        self._request("PUT", self._url(self._full(key)), data, {"content-type": content_type})
        return {"key": key, "bytes": len(data)}

    def get(self, key):
        return self._request("GET", self._url(self._full(key)))[1]

    def delete(self, key):
        self._request("DELETE", self._url(self._full(key)))

    def list(self, prefix=""):
        full = (f"{self.prefix}/{prefix}" if self.prefix else prefix)
        out, token = [], None
        while True:
            query = "list-type=2&prefix=" + _quote(full)
            if token:
                query += "&continuation-token=" + _quote(token)
            body = self._request("GET", self._url("", query))[1]
            root = ET.fromstring(body)
            ns = root.tag.split("}")[0] + "}" if root.tag.startswith("{") else ""
            for item in root.iter(ns + "Contents"):
                key = item.find(ns + "Key").text
                if self.prefix:
                    key = key[len(self.prefix) + 1:]
                out.append({"key": key, "bytes": int(item.find(ns + "Size").text)})
            truncated = (root.findtext(ns + "IsTruncated") or "false").lower() == "true"
            token = root.findtext(ns + "NextContinuationToken")
            if not truncated or not token:
                return out
