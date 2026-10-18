# Integrating a project into MTDI 5.0

The full procedure, written for people and AI assistants alike, is [docs/AI.md](docs/AI.md).
This page is the short version.

1. **Create the project.** `python -m mtdi new <id>` here, or `python -m mtdi adopt <repo> --studio`
   in another repository.
2. **Inventory the measurements.** One row per quantity: what, from where, keys, unit, domain.
3. **Make the sources speak the protocol.** `KEY=value,KEY=value` per line
   ([firmware/PROTOCOL.md](firmware/PROTOCOL.md)); use the SDK for your language (`sdk/`,
   `matlab/+mtdi`, `firmware/`). If something cannot be read, print nothing for that sample.
4. **Write `project.json`.** Sources, channels, environment, a `studio` block choosing the three
   display channels, NVTRA rules and Aether ([docs/MANIFEST.md](docs/MANIFEST.md)).
5. **Make the interface yours.** Replace the placeholders (Title, Heading 1, Text, …); the table
   of where each one lives is in docs/AI.md, step 5.
6. **Verify.**
   ```bash
   python -m mtdi check projects/<id>
   python -m mtdi packet projects/<id> --seconds 5
   python -m mtdi run projects/<id>
   python -m unittest discover tests
   ```
7. **Deploy.** `python -m mtdi publish vercel projects/<id> --name <name>`, then
   `python -m mtdi run projects/<id> --studio-url https://<name>.vercel.app`.

## Improving MTDI itself

If a manifest cannot express what a project needs, improve the framework generically: no
project, sensor, unit or product named in `mtdi/`. Add a test, keep every project passing,
and record the change in [CHANGELOG.md](CHANGELOG.md).
