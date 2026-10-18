# Security

* **Ingest is a write path.** `POST /api/ingest` changes what every viewer sees. On a public
  deployment it is refused unless `STUDIO_INGEST_TOKEN` is set and the request carries
  `Authorization: Bearer <token>` (compared in constant time). Locally the token is optional.
* **Manifests can run programs.** The `process` and `python` adapters start code named in
  `project.json`. Only run manifests you wrote or trust, including ones written by an AI.
* **The framework's API binds to 127.0.0.1 by default.** `--host 0.0.0.0` exposes `/mtdi/*` to your
  network; put it behind a firewall or an authenticating proxy if the network is shared.
* **Keys** (language models, voice, storage, GitHub, Vercel, Notion) are read from environment
  variables only and never written to disk; `tests/test_mtdi.py` checks the wizard never writes them.
* **Storage:** S3 requests are signed with SigV4; `--encrypt` / `EncryptedStore` encrypts on your side
  with AES-256-GCM and binds each object to its name. Keep `MTDI_STORAGE_KEY` in a secret manager.
* **Protocol parsing is strict:** a malformed line is rejected whole and counted, never partly used.

Report a vulnerability privately through GitHub's "Report a vulnerability" (Security tab), not in a
public issue.
