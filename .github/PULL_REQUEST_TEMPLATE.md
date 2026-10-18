## What changed

## Kind
- [ ] New or updated project (manifest, firmware, probe)
- [ ] MTDI change (framework, interface, SDK): generic, tested, recorded in CHANGELOG.md

## Verified
- [ ] `python -m unittest discover tests`
- [ ] `python -m mtdi check` on affected projects
- [ ] `python -m mtdi run <project>` shows live data in the studio
- [ ] `STUDIO_HTTPS_PORT=0 python run.py --self-test`
- What was **not** verified:
