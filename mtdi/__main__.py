"""MTDI Studio command line.

    python -m mtdi run projects/inductra-vaion              start the studio on its real sources
    python -m mtdi run projects/inductra-vaion --simulate   every source replaced by the simulator
    python -m mtdi run projects/x --record session.jsonl    also record every real sample
    python -m mtdi check projects/x                         validate a manifest and print the channel map
    python -m mtdi new astrotech                            start a new project from the template
    python -m mtdi parse "CH1=512,CH2=498,CH3=530"          test a firmware line
    python -m mtdi packet projects/x --simulate --seconds 5 run headless and print one MTDI packet
    python -m mtdi run projects/x --headless                JSON API only (small boards, no Dash)
    python -m mtdi watch projects/x                         live terminal view (works over SSH)
    python -m mtdi adopt ../my-repo                         copy MTDI into another repository and set it up
    python -m mtdi describe                                 everything MTDI supports, as JSON (for AIs and tools)
    python -m mtdi analyze projects/x session.jsonl         batch summary; MATLAB's mtdi.analyze must match it
    python -m mtdi site build                               build the website into site/dist
    python -m mtdi create                                   wizard: project + GitHub + Vercel + Notion + MATLAB
    python -m mtdi publish vercel projects/x --name my-x    deploy one project's studio to Vercel
    python -m mtdi matlab projects/x                        open MATLAB Online on a starter script
"""
import argparse
import json
import pathlib
import re
import shutil
import sys
import time

from . import __version__
from .project import ManifestError, load
from .protocol import ProtocolError, parse_line

ROOT = pathlib.Path(__file__).resolve().parent.parent


def cmd_run(args):
    from .studio import Studio
    studio = Studio(args.project, simulate=args.simulate, record=args.record, ui=not args.headless)
    name = studio.project["project"]["name"]
    print(f"MTDI {__version__} · {name} · http://{args.host}:{args.port}" + ("  [SIMULATED]" if studio.simulate else "")
          + ("  [HEADLESS: /mtdi/packet /mtdi/state]" if args.headless else ""))
    studio.run(host=args.host, port=args.port)


def cmd_check(args):
    project = load(args.project)
    meta = project["project"]
    print(f"{meta['name']} ({meta['id']}) · MTDI {project['mtdi']}")
    print("sources:")
    for s in project["sources"]:
        detail = {k: v for k, v in s.items() if k not in ("id", "adapter")}
        print(f"  {s['id']:<14} {s['adapter']:<10} {json.dumps(detail)}")
    print("channels:")
    for c in project["channels"]:
        print(f"  {c['id']:<14} {c['kind']:<7} {c['domain']:<11} keys={','.join(c['keys']):<18} "
              f"unit={c['unit'] or '-':<8} source={'|'.join(c['sources'])}  floor={c['noise_floor']}"
              + (f"  {c['transform']}({c['window']})" if c["transform"] != "none" else ""))
    print(f"nvtra rules: {len(project['nvtra']['rules'])}   saved environments: "
          f"{len(list((pathlib.Path(project['_dir']) / 'environments').glob('*.json')))}")
    print("OK")


def cmd_new(args):
    if not re.match(r"^[a-z0-9][a-z0-9\-]{1,47}$", args.id):
        sys.exit("project id: lowercase letters, digits and dashes")
    target = ROOT / "projects" / args.id
    if target.exists():
        sys.exit(f"{target} already exists")
    shutil.copytree(ROOT / "projects" / "_template", target)
    manifest = target / "project.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["project"]["id"] = args.id
    data["project"]["name"] = args.name or args.id.replace("-", " ").title()
    manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"created {target}\nnext: edit {manifest}, then  python -m mtdi run {target} --simulate")


def cmd_parse(args):
    try:
        print(json.dumps(parse_line(args.line)))
    except ProtocolError as error:
        sys.exit(f"rejected: {error}")


def cmd_packet(args):
    from .studio import Studio
    studio = Studio(args.project, simulate=args.simulate, ui=False)
    time.sleep(args.seconds)
    studio.stop()
    print(json.dumps(studio.engine.snapshot(), indent=2, default=str))


def cmd_watch(args):
    """Redraw a compact view of the packet once a second. Ctrl-C to stop."""
    from .studio import Studio
    studio = Studio(args.project, simulate=args.simulate, ui=False)
    bar = lambda v: "█" * int(v / 10) + "·" * (10 - int(v / 10))
    try:
        while True:
            p = studio.engine.snapshot()
            f = p["fusion"]
            out = [f"\033[2J\033[HMTDI {p['mtdi']} · {p['project']['name']}" + ("   SIMULATED" if f["simulated"] else ""),
                   f"score {f['score']:5.1f} % {bar(f['score'])}   live {f['completeness']:.0f} %",
                   f"{f['condition']}: {f['interpretation']}", ""]
            for c in p["channels"].values():
                ev, env = c["evidence"], c["environment"]
                mag = "—" if c["magnitude"] is None else f"{c['magnitude']:.4g}"
                out.append(f"{c['label'][:22]:<22} {ev['state']:<9} {mag:>10} {c['unit'][:8]:<8} "
                           f"dev {env.get('deviation', 0):>9.3g}  snr {env.get('snr', 0):>6.1f}  {c['score']:5.1f} %")
            out += [""] + [f"! {w}" for w in f["warnings"][:5]]
            print("\n".join(out), flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        studio.stop()


def cmd_create(args):
    from .create import run
    run(args)


def cmd_publish(args):
    from .integrations import IntegrationError, matlab, notion, vercel
    project = load(args.project)
    try:
        if args.target == "vercel":
            out = vercel.deploy(project, args.name or project["project"]["id"], dry_run=args.dry_run)
        elif args.target == "notion":
            out = notion.create(project, {}, dry_run=args.dry_run)
        else:
            out = matlab.open_project(project, repo=args.repo, local=args.local, dry_run=args.dry_run)
    except IntegrationError as error:
        sys.exit(str(error))
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))


def cmd_matlab(args):
    args.target = "matlab"
    cmd_publish(args)


def cmd_site(args):
    from .site import build_project_site, build_site
    if args.what == "build":
        out = build_site(args.out, seconds=args.seconds)
    else:
        if not args.project:
            sys.exit("site project needs a project path")
        out = build_project_site(args.project, args.out or "site/project-dist", seconds=args.seconds)
    files = sum(1 for p in pathlib.Path(out).rglob("*") if p.is_file())
    print(f"built {out} ({files} files)")


def cmd_analyze(args):
    from .analysis import analyze, read_recording
    print(json.dumps(analyze(load(args.project), read_recording(args.recording)), indent=2))


def cmd_adopt(args):
    from .adopt import adopt
    try:
        for step in adopt(args.target, project_id=args.id, name=args.name, force=args.force):
            print("·", step)
    except FileExistsError as error:
        sys.exit(str(error))
    print(f"next: cd {args.target} && python -m mtdi run mtdi-project --simulate")


def cmd_describe(args):
    from .adapters import build  # noqa: F401  (import check: every adapter module loads)
    from .core import DEFAULT_WEIGHTS
    from .pillars import PILLARS
    from .pillars.i3 import components
    from .project import ADAPTERS, KINDS, KNOWN_DOMAINS, TRANSFORMS
    print(json.dumps({
        "mtdi": __version__,
        "pillars": [{k: p[k] for k in ("num", "id", "title", "role", "desc")} for p in PILLARS],
        "adapters": sorted(ADAPTERS), "channel_kinds": sorted(KINDS), "transforms": sorted(TRANSFORMS),
        "domains": {"known": sorted(KNOWN_DOMAINS), "open": "any lowercase word"},
        "score_factors": DEFAULT_WEIGHTS,
        "nvtra_rule_operators": [">=", ">", "<=", "<", "=="],
        "data_sources": ["HARDWARE", "SOFTWARE", "REPLAY", "SIMULATED"],
        "protocol": "KEY=value,KEY=value\\n or one JSON object per line; reserved keys _T (ms), _SEQ",
        "i3_page_types": ["home", "framework", "document", "module", "settings"],
        "i3_block_kinds": ["section", "text", "cards", "metrics", "slot", "spark", "live", "actions", "list", "quote"],
        "commands": ["run", "watch", "check", "new", "adopt", "describe", "parse", "packet", "matlab", "site"],
        "docs": {"ai": "docs/AI.md", "integrating": "INTEGRATING.md", "manifest": "docs/MANIFEST.md",
                 "schema": "docs/schema/project.schema.json", "protocol": "firmware/PROTOCOL.md"},
    }, indent=2, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mtdi", description=f"MTDI Studio {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="start the studio")
    run.add_argument("project")
    run.add_argument("--simulate", action="store_true", help="replace every source with the simulator")
    run.add_argument("--record", help="append real samples to this JSONL file")
    run.add_argument("--host", default="127.0.0.1")
    run.add_argument("--port", type=int, default=8050)
    run.add_argument("--headless", action="store_true", help="JSON API only, no browser interface")
    run.set_defaults(func=cmd_run)
    watch = sub.add_parser("watch", help="live terminal view")
    watch.add_argument("project")
    watch.add_argument("--simulate", action="store_true")
    watch.set_defaults(func=cmd_watch)
    check = sub.add_parser("check", help="validate a project manifest")
    check.add_argument("project")
    check.set_defaults(func=cmd_check)
    new = sub.add_parser("new", help="create a project from the template")
    new.add_argument("id")
    new.add_argument("--name")
    new.set_defaults(func=cmd_new)
    parse = sub.add_parser("parse", help="test one protocol line")
    parse.add_argument("line")
    parse.set_defaults(func=cmd_parse)
    packet = sub.add_parser("packet", help="run headless and print one packet")
    packet.add_argument("project")
    packet.add_argument("--simulate", action="store_true")
    packet.add_argument("--seconds", type=float, default=5.0)
    packet.set_defaults(func=cmd_packet)
    adopt = sub.add_parser("adopt", help="copy MTDI into another repository")
    adopt.add_argument("target")
    adopt.add_argument("--id")
    adopt.add_argument("--name")
    adopt.add_argument("--force", action="store_true", help="replace an existing vendored mtdi/ (upgrade)")
    adopt.set_defaults(func=cmd_adopt)
    analyze = sub.add_parser("analyze", help="batch summary of a recording (matches matlab/+mtdi/analyze.m)")
    analyze.add_argument("project")
    analyze.add_argument("recording")
    analyze.set_defaults(func=cmd_analyze)
    create = sub.add_parser("create", help="wizard: new project + GitHub, Vercel, Notion, MATLAB")
    for flag in ("--name", "--id", "--description", "--standalone", "--github", "--vercel"):
        create.add_argument(flag)
    create.add_argument("--public", action="store_true")
    create.add_argument("--notion", action="store_const", const="env")
    create.add_argument("--matlab", action="store_true")
    create.add_argument("--yes", action="store_true", help="no questions; use flags and defaults")
    create.add_argument("--dry-run", action="store_true", help="show the plan and requests, create nothing")
    create.set_defaults(func=cmd_create)
    publish = sub.add_parser("publish", help="deploy to Vercel, create a Notion page, or open MATLAB for a project")
    publish.add_argument("target", choices=["vercel", "notion", "matlab"])
    publish.add_argument("project")
    publish.add_argument("--name", help="Vercel project name")
    publish.add_argument("--repo", help="owner/repo, for Open in MATLAB Online")
    publish.add_argument("--local", action="store_true", help="start desktop MATLAB instead of MATLAB Online")
    publish.add_argument("--dry-run", action="store_true")
    publish.set_defaults(func=cmd_publish)
    mat = sub.add_parser("matlab", help="open MATLAB on a project with a starter script")
    mat.add_argument("project")
    mat.add_argument("--repo")
    mat.add_argument("--local", action="store_true")
    mat.add_argument("--dry-run", action="store_true")
    mat.set_defaults(func=cmd_matlab)
    site = sub.add_parser("site", help="build the static website (or one project's static studio)")
    site.add_argument("what", choices=["build", "project"])
    site.add_argument("project", nargs="?")
    site.add_argument("--out")
    site.add_argument("--seconds", type=int, default=90, help="seconds of simulated replay per demo")
    site.set_defaults(func=cmd_site)
    describe = sub.add_parser("describe", help="print MTDI's capabilities as JSON")
    describe.set_defaults(func=cmd_describe)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except ManifestError as error:
        sys.exit(f"manifest error: {error}")


if __name__ == "__main__":
    main()
