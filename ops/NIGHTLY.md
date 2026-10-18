# Nightly session procedure

You are a scheduled Claude Code session developing MTDI 5. The owner reviews; you direct.
Follow this procedure exactly. Rules in AGENTS.md and docs/adr/ apply throughout.

## 1 · Set up
1. Attach the repository with push access (add_repo: owner `vxnishhhhh`, repo `mtdi-studio-`),
   clone it to `/home/user/mtdi-studio-`, `git checkout main && git pull`.
2. `pip install -r requirements.txt` if `import dash` fails.
3. Read `ops/STATE.md`, `ops/BACKLOG.md`, the newest file in `ops/reports/`, and the ADRs.
4. Check main is healthy: latest CI run on main green, latest Vercel deployment READY. If main is
   red, fixing it is tonight's item, before anything else.

## 2 · Choose
Take the first `ready` backlog item whose dependencies are `done`. Midday sessions do not start
new items: they handle review comments and CI on open PRs, then report.

## 3 · Build
1. Branch `auto/<item-id>-<slug>` from main.
2. Implement the item. Keep `mtdi/` universal (no project-specific code). Keep the interface's
   design, NVTRA, hand vision and Aether working. Never invent data; label every data source.
3. Add or update tests for the item's acceptance check.

## 4 · Verify (all must pass before a PR)
```bash
python -m unittest discover tests
STUDIO_HTTPS_PORT=0 python run.py --self-test
for p in projects/*/; do python -m mtdi check "$p"; done
python tools/serve.py 8062 &   # then:
node tools/tour.mjs http://127.0.0.1:8062
```

## 5 · Pull request
Open a PR to main: what changed, how it was verified, what was not verified. Update the item's
status in `ops/BACKLOG.md` and add a line to `ops/STATE.md` in the same PR.

## 6 · Merge (ADR 0002)
Wait for CI. If any job fails, fix it on the branch and push again. Merge (squash) only when:
CI is green, the tour passed, CodeRabbit and Codex (if installed) have no unresolved blocking
finding, and the PR does not touch `vercel.json`, `app.py`'s entry, `.github/workflows/`, secrets,
`LICENSE`, or delete data. Otherwise leave the PR open and say why in the report.
After merging, confirm the Vercel production deployment for the merge commit reaches READY.

## 7 · Report (always, even if nothing changed)
Write `ops/reports/<YYYY-MM-DD>-<session>.md` (on the PR branch, or directly on main if no PR):
completed · tested · failed · changed · blocked · next · decisions needing the owner.
Keep it short and factual. Never claim a test ran that did not.

## Limits
One item per session (two if both are small). No paid API calls, paid services, hardware
actuation, public posting or data deletion. No new scheduled tasks. Stop after about three hours.
