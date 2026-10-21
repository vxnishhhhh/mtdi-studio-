"""MTDI command line.

    python -m mtdi run projects/host-health                 the project, live in the studio interface
    python -m mtdi run projects/x --studio-url https://x.vercel.app   feed a deployed studio instead
    python -m mtdi run projects/x --headless                JSON API only (small boards, no interface)
    python -m mtdi run projects/x --record session.jsonl    also record every real sample
    python -m mtdi watch projects/x                         live terminal view (works over SSH)
    python -m mtdi ask projects/x "is anything unusual?"    one grounded NVTRA answer
    python -m mtdi chat projects/x                          talk to NVTRA about the live project
    python -m mtdi voice projects/x question.wav            ask by voice, get text and reply.mp3
    python -m mtdi anomalies projects/x session.jsonl       streaming anomaly detection over a recording
    python -m mtdi send http://localhost:8050 --ch2 3.1     push one sample into a studio
    python -m mtdi store put s3://bucket/key file           signed cloud storage (S3, R2, MinIO, B2)
    python -m mtdi store backup projects/x s3://bucket      back a project up (optionally encrypted)
    python -m mtdi check projects/x                         validate a manifest and print the channel map
    python -m mtdi new my-project                           start a new project from the template
    python -m mtdi parse "TEMP=21.4,HUM=40"                 test a firmware line
    python -m mtdi packet projects/x --seconds 5            run headless and print one MTDI packet
    python -m mtdi adopt ../my-repo                         copy MTDI into another repository and set it up
    python -m mtdi describe                                 everything MTDI supports, as JSON (for AIs and tools)
    python -m mtdi analyze projects/x session.jsonl         batch summary; MATLAB's mtdi.analyze must match it
    python -m mtdi create                                   wizard: project + GitHub + Vercel + Notion + MATLAB
    python -m mtdi publish vercel projects/x --name my-x    deploy a project's studio to Vercel
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
    from .runtime import Runner
    runner = Runner(args.project, simulate=args.simulate, record=args.record)
    name = runner.project["project"]["name"]
    label = "  [SIMULATED]" if runner.simulate else ""
    if not args.headless and not args.studio_url and not (ROOT / "run.py").exists():
        print("no studio interface in this repository (adopt --studio adds it); serving the JSON API")
        args.headless = True
    if args.headless:
        print(f"MTDI {__version__} · {name} · http://{args.host}:{args.port}/mtdi/packet{label}  [HEADLESS]")
        runner.headless_app().run(host=args.host, port=args.port, threaded=True, use_reloader=False)
        return
    from .bridge import StudioBridge, mapping_for
    if args.studio_url:
        import os
        bridge = StudioBridge(runner.engine, args.studio_url, token=os.environ.get("STUDIO_INGEST_TOKEN")).start()
        print(f"MTDI {__version__} · {name} → {args.studio_url} {mapping_for(runner.project)}{label}")
        try:
            while True:
                time.sleep(5)
                if bridge.last_error:
                    print("studio:", bridge.last_error, flush=True)
                    bridge.last_error = None
        except KeyboardInterrupt:
            runner.stop()
        return
    import os
    os.environ.setdefault("STUDIO_HTTPS_PORT", "0")
    sys.path.insert(0, str(ROOT))
    from run import NAMESPACE                      # the studio interface, in this process
    runner.register(NAMESPACE["server"])
    NAMESPACE["LIFECYCLE"].start()
    StudioBridge(runner.engine, NAMESPACE).start()
    print(f"MTDI {__version__} · {name} · http://{args.host}:{args.port}  channels {mapping_for(runner.project)}{label}")
    from werkzeug.serving import run_simple
    run_simple(args.host, args.port, NAMESPACE["server"], threaded=True, use_reloader=False)


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
    print(f"created {target}\nnext: edit {manifest}, then  python -m mtdi run {target}")


def cmd_parse(args):
    try:
        print(json.dumps(parse_line(args.line)))
    except ProtocolError as error:
        sys.exit(f"rejected: {error}")


def cmd_packet(args):
    from .runtime import Runner
    runner = Runner(args.project, simulate=args.simulate)
    time.sleep(args.seconds)
    runner.stop()
    print(json.dumps(runner.engine.snapshot(), indent=2, default=str))


def cmd_watch(args):
    """Redraw a compact view of the packet once a second. Ctrl-C to stop."""
    from .runtime import Runner
    studio = Runner(args.project, simulate=args.simulate)
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


def _runner_for(args, settle=3.0):
    from .runtime import Runner
    runner = Runner(args.project, simulate=getattr(args, "simulate", False))
    time.sleep(settle)          # let the sources deliver a few samples before answering
    return runner


def cmd_ask(args):
    from .bot import Bot
    runner = _runner_for(args, args.settle)
    out = Bot(runner).reply(" ".join(args.question))
    runner.stop()
    print(out["text"] + (f"\n  [{out['engine']}]" if args.verbose else ""))


def cmd_chat(args):
    from .bot import Bot
    runner = _runner_for(args, args.settle)
    bot = Bot(runner)
    print("NVTRA · type a question, or 'quit'.")
    try:
        while True:
            question = input("you › ").strip()
            if question.lower() in ("quit", "exit", ""):
                break
            out = bot.reply(question)
            print("nvtra ›", out["text"], f"[{out['engine']}]")
    except (EOFError, KeyboardInterrupt):
        pass
    runner.stop()


def cmd_voice(args):
    from .bot import Bot
    from .voice import VoiceError
    runner = _runner_for(args, args.settle)
    mimetype = {"webm": "audio/webm", "mp3": "audio/mpeg", "ogg": "audio/ogg", "m4a": "audio/mp4"}.get(
        args.audio.rsplit(".", 1)[-1].lower(), "audio/wav")
    try:
        out = Bot(runner).reply_voice(pathlib.Path(args.audio).read_bytes(), mimetype)
    except VoiceError as error:
        runner.stop()
        sys.exit(str(error))
    runner.stop()
    print("heard:", out["heard"])
    print("nvtra:", out["text"])
    if out.get("audio"):
        pathlib.Path(args.out).write_bytes(out["audio"])
        print("spoken reply:", args.out)
    elif out.get("speech_error"):
        print("no spoken reply:", out["speech_error"])


def cmd_anomalies(args):
    from .analysis import read_recording
    from .engine import Engine
    from .ml import Monitor, MAD, EWMA, ZScore, CUSUM
    detectors = {"mad": lambda: MAD(threshold=args.threshold), "zscore": lambda: ZScore(threshold=args.threshold),
                 "ewma": lambda: EWMA(threshold=args.threshold), "cusum": lambda: CUSUM(threshold=args.threshold + 2)}
    project = load(args.project)
    clock = [0.0]
    engine = Engine(project, clock=lambda: clock[0])
    monitor = Monitor(detectors[args.detector])
    for row in read_recording(args.recording):
        clock[0] = row["t"]
        engine.ingest_values(row["source"], row["values"], row.get("data_source", "REPLAY"))
        for event in monitor.update(engine.snapshot()):
            print(json.dumps(dict(event, t=row["t"])))
    print(json.dumps({"anomalies": len(monitor.events), "detector": args.detector}), file=sys.stderr)


def cmd_send(args):
    import os
    import urllib.request
    sample = {"source": args.source}
    if args.ch1:
        sample["ch1"] = [float(v) for v in args.ch1]
    if args.ch2 is not None:
        sample["ch2"] = args.ch2
    if args.ch3:
        ys = [float(v) for v in args.ch3]
        sample["ch3"] = {"x": list(range(len(ys))), "y": ys}
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("STUDIO_INGEST_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(args.url.rstrip("/") + "/api/ingest", data=json.dumps(sample).encode(),
                                     headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            print(response.read().decode())
    except urllib.error.HTTPError as error:
        sys.exit(f"{error.code}: {error.read().decode()}")


def cmd_store(args):
    from . import storage
    def open_store(url):
        store = storage.open(url)
        return storage.encrypted(store, storage.key_from_env()) if args.encrypt else store
    try:
        if args.op == "backup":
            store = open_store(args.b)
            for key in storage.backup_project(args.a, store):
                print("put", key)
        elif args.op == "restore":
            base, _, prefix = args.a.rpartition("/")
            for path in storage.restore_project(open_store(base), prefix, args.b, overwrite=args.force):
                print("wrote", path)
        else:
            base, _, key = args.a.rpartition("/") if args.op != "ls" else (args.a, "", "")
            store = open_store(base)
            if args.op == "put":
                print(json.dumps(store.put(key, pathlib.Path(args.b).read_bytes())))
            elif args.op == "get":
                data = store.get(key)
                (pathlib.Path(args.b).write_bytes(data) if args.b else sys.stdout.buffer.write(data))
            elif args.op == "ls":
                for item in store.list(args.b or ""):
                    print(f"{item['bytes']:>10}  {item['key']}")
            elif args.op == "rm":
                store.delete(key)
                print("deleted", key)
    except storage.StoreError as error:
        sys.exit(str(error))


def cmd_analyze(args):
    from .analysis import analyze, read_recording
    print(json.dumps(analyze(load(args.project), read_recording(args.recording)), indent=2))


def cmd_adopt(args):
    from .adopt import adopt
    try:
        for step in adopt(args.target, project_id=args.id, name=args.name, force=args.force, studio=args.studio):
            print("·", step)
    except FileExistsError as error:
        sys.exit(str(error))
    print(f"next: cd {args.target} && python -m mtdi check mtdi-project && python -m mtdi run mtdi-project")


def cmd_registry(args):
    from . import registry
    snap = registry.snapshot()
    print(json.dumps(snap, indent=2) if args.json else registry.render(snap))
    if not all(m["ok"] for m in snap["modules"]):
        sys.exit(1)


def cmd_describe(args):
    from .adapters import build  # noqa: F401  (import check: every adapter module loads)
    from .core import DEFAULT_WEIGHTS
    from .pillars import AETHER, COMPUTATIONAL_MODULES, PILLARS
    from .project import ADAPTERS, KINDS, KNOWN_DOMAINS, TRANSFORMS
    from . import llm
    print(json.dumps({
        "mtdi": __version__,
        "pillars": [{k: p[k] for k in ("num", "id", "title", "role", "desc")} for p in PILLARS],
        "aether": {k: AETHER[k] for k in ("id", "title", "role", "desc")},
        "computational_core": COMPUTATIONAL_MODULES,
        "adapters": sorted(ADAPTERS), "channel_kinds": sorted(KINDS), "transforms": sorted(TRANSFORMS),
        "domains": {"known": sorted(KNOWN_DOMAINS), "open": "any lowercase word"},
        "score_factors": DEFAULT_WEIGHTS,
        "nvtra_rule_operators": [">=", ">", "<=", "<", "=="],
        "data_sources": ["HARDWARE", "SOFTWARE", "REPLAY", "EXTERNAL", "SIMULATED"],
        "protocol": "KEY=value,KEY=value\\n or one JSON object per line; reserved keys _T (ms), _SEQ",
        "studio": {"channels": {"ch1": "vector or number", "ch2": "number", "ch3": "sweep {x:[], y:[]}"},
                   "ingest": "POST /api/ingest (Authorization: Bearer $STUDIO_INGEST_TOKEN)",
                   "manifest_block": {"studio": {"ch1": "<channel id>", "ch2": "<channel id>", "ch3": "<channel id>"}}},
        "ml": ["ZScore", "EWMA", "MAD", "CUSUM", "PageHinkley", "KNN", "NearestCentroid", "LogisticRegression",
               "GaussianNB", "KMeans", "Holt", "OnlineLinear", "window_features", "band_power", "dominant_frequency"],
        "storage": ["local folder", "S3-compatible with SigV4 (AWS, R2, MinIO, B2)", "AES-256-GCM encryption"],
        "llm_providers": list(llm.PROVIDERS), "voice": {"stt": ["groq", "openai"], "tts": ["elevenlabs", "openai"]},
        "sdks": {"python": "mtdi/", "cpp": "sdk/cpp/mtdi.hpp", "java": "sdk/java", "javascript": "sdk/js/mtdi.mjs",
                 "matlab": "matlab/+mtdi", "arduino": "firmware/mtdi_template_arduino",
                 "micropython": "firmware/mtdi_template_micropython"},
        "registry": {"file": "registry/integrations.json", "command": "python -m mtdi registry",
                     "integrations": [r["id"] for r in __import__("mtdi.registry", fromlist=["x"]).load_integrations()]},
        "commands": ["registry", "run", "watch", "ask", "chat", "voice", "anomalies", "send", "store", "check", "new", "adopt",
                     "describe", "parse", "packet", "analyze", "create", "publish", "matlab"],
        "docs": {"ai": "docs/AI.md", "architecture": "docs/ARCHITECTURE.md", "integrating": "INTEGRATING.md",
                 "manifest": "docs/MANIFEST.md", "schema": "docs/schema/project.schema.json",
                 "protocol": "firmware/PROTOCOL.md"},
    }, indent=2, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mtdi", description=f"MTDI Studio {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="run a project in the studio interface")
    run.add_argument("project")
    run.add_argument("--simulate", action="store_true", help="replace every source with the simulator")
    run.add_argument("--record", help="append real samples to this JSONL file")
    run.add_argument("--host", default="127.0.0.1")
    run.add_argument("--port", type=int, default=8050)
    run.add_argument("--headless", action="store_true", help="JSON API only, no browser interface")
    run.add_argument("--studio-url", help="feed a studio running elsewhere (uses STUDIO_INGEST_TOKEN)")
    run.set_defaults(func=cmd_run)
    for name, func, text in (("ask", cmd_ask, "one grounded NVTRA answer"), ("chat", cmd_chat, "talk to NVTRA"),
                             ("voice", cmd_voice, "ask NVTRA by voice")):
        cmd = sub.add_parser(name, help=text)
        cmd.add_argument("project")
        if name == "ask":
            cmd.add_argument("question", nargs="+")
            cmd.add_argument("-v", "--verbose", action="store_true")
        if name == "voice":
            cmd.add_argument("audio")
            cmd.add_argument("--out", default="reply.mp3")
        cmd.add_argument("--simulate", action="store_true")
        cmd.add_argument("--settle", type=float, default=3.0, help="seconds to collect before answering")
        cmd.set_defaults(func=func)
    anomalies = sub.add_parser("anomalies", help="streaming anomaly detection over a recording")
    anomalies.add_argument("project")
    anomalies.add_argument("recording")
    anomalies.add_argument("--detector", choices=["mad", "zscore", "ewma", "cusum"], default="mad")
    anomalies.add_argument("--threshold", type=float, default=4.0)
    anomalies.set_defaults(func=cmd_anomalies)
    send = sub.add_parser("send", help="push one sample into a studio (POST /api/ingest)")
    send.add_argument("url")
    send.add_argument("--ch1", nargs="+")
    send.add_argument("--ch2", type=float)
    send.add_argument("--ch3", nargs="+", help="y values of one sweep")
    send.add_argument("--source", default="CLI")
    send.set_defaults(func=cmd_send)
    store = sub.add_parser("store", help="cloud or local storage: put, get, ls, rm, backup, restore")
    store.add_argument("op", choices=["put", "get", "ls", "rm", "backup", "restore"])
    store.add_argument("a", help="put/get/rm: URL/key · ls: URL · backup: project dir · restore: URL/prefix")
    store.add_argument("b", nargs="?", help="put: file · get: output file · ls: prefix · backup: URL · restore: dir")
    store.add_argument("--encrypt", action="store_true", help="AES-256-GCM with MTDI_STORAGE_KEY")
    store.add_argument("--force", action="store_true")
    store.set_defaults(func=cmd_store)
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
    adopt.add_argument("--studio", action="store_true", help="also copy the studio interface (deployable to Vercel)")
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
    reg = sub.add_parser("registry", help="list integrations and Computational Core modules with status")
    reg.add_argument("--json", action="store_true")
    reg.set_defaults(func=cmd_registry)
    describe = sub.add_parser("describe", help="print MTDI's capabilities as JSON")
    describe.set_defaults(func=cmd_describe)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except ManifestError as error:
        sys.exit(f"manifest error: {error}")


if __name__ == "__main__":
    main()
