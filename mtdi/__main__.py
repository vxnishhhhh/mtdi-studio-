"""MTDI Studio command line.

    python -m mtdi run projects/inductra-vaion              start the studio on its real sources
    python -m mtdi run projects/inductra-vaion --simulate   every source replaced by the simulator
    python -m mtdi run projects/x --record session.jsonl    also record every real sample
    python -m mtdi check projects/x                         validate a manifest and print the channel map
    python -m mtdi new astrotech                            start a new project from the template
    python -m mtdi parse "CH1=512,CH2=498,CH3=530"          test a firmware line
    python -m mtdi packet projects/x --simulate --seconds 5 run headless and print one MTDI packet
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
    studio = Studio(args.project, simulate=args.simulate, record=args.record)
    name = studio.project["project"]["name"]
    print(f"MTDI {__version__} · {name} · http://{args.host}:{args.port}" + ("  [SIMULATED]" if studio.simulate else ""))
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
        print(f"  {c['id']:<14} {c['kind']:<7} {c['physical']:<11} keys={','.join(c['keys']):<18} "
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
    studio = Studio(args.project, simulate=args.simulate)
    time.sleep(args.seconds)
    studio.stop()
    print(json.dumps(studio.engine.snapshot(), indent=2, default=str))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mtdi", description=f"MTDI Studio {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="start the studio")
    run.add_argument("project")
    run.add_argument("--simulate", action="store_true", help="replace every source with the simulator")
    run.add_argument("--record", help="append real samples to this JSONL file")
    run.add_argument("--host", default="127.0.0.1")
    run.add_argument("--port", type=int, default=8050)
    run.set_defaults(func=cmd_run)
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
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except ManifestError as error:
        sys.exit(f"manifest error: {error}")


if __name__ == "__main__":
    main()
