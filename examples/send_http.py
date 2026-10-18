"""Feed MTDI from any program over HTTP (a software source, or a Wi-Fi board's gateway).

Declare the source in project.json:  {"id": "app", "adapter": "http"}
then post lines or values to a running studio:

    python examples/send_http.py --source app --key VALUE
"""
import argparse
import json
import math
import time
import urllib.request


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8050/mtdi/ingest")
    ap.add_argument("--source", required=True)
    ap.add_argument("--key", default="VALUE")
    args = ap.parse_args()
    t0 = time.time()
    while True:
        value = 500 + 3 * math.sin(time.time() - t0)     # replace with a real reading
        print(post(args.url, {"source": args.source, "values": {args.key: value}}))
        time.sleep(0.1)
