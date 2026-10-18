# Security

* **Manifests can run programs.** The `process` and `python` adapters start code named in
  `project.json`. Only run manifests you wrote or trust, including ones written by an AI.
* **The studio binds to 127.0.0.1 by default.** `--host 0.0.0.0` exposes it to your network,
  including `/mtdi/ingest` and the Environmental Intelligence actions. There is no
  authentication; put it behind a firewall or a reverse proxy with auth if the network is shared.
* **Tokens** for GitHub, Vercel and Notion are read from environment variables only and are never
  written to disk; `tests/test_mtdi.py` checks this.
* **Protocol parsing is strict:** a malformed line is rejected whole and counted, never partly used.

Report a vulnerability privately to the repository owner through GitHub's
"Report a vulnerability" (Security tab) rather than in a public issue.
