"""`python -m mtdi create`: start a project on MTDI 5.0, with everything around it.

Asks what it needs, shows the plan, then does it:

    1. the project            inside MTDI Studio (projects/<id>) or a new repository (mtdi adopt)
    2. GitHub                 repository created and pushed
    3. Vercel                 the project's studio deployed, under the name you choose
    4. Notion                 a project page with its channels, pillars and links
    5. MATLAB                 MATLAB Online (or desktop MATLAB) opened on a starter script

Every step is optional and skips itself with a clear message if its token is missing.
Non-interactive use: pass the answers as flags and --yes. Preview with --dry-run.
"""
import json
import pathlib
import re
import shutil

from .integrations import IntegrationError
from .project import load

ROOT = pathlib.Path(__file__).resolve().parent.parent


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48] or "project"


def ask(prompt, default="", interactive=True):
    if not interactive:
        return default
    reply = input(f"{prompt}{f' [{default}]' if default else ''}: ").strip()
    return reply or default


def ask_yes(prompt, default=False, interactive=True):
    if not interactive:
        return default
    reply = input(f"{prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    return default if not reply else reply.startswith("y")


def gather(args):
    """Turn flags and answers into a plan. Nothing is created here."""
    i = not args.yes
    name = args.name or ask("Project name", "Title", i)
    pid = args.id or ask("Project id", slugify(name), i)
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]{1,47}", pid):
        raise SystemExit("project id: lowercase letters, digits and dashes")
    description = args.description or ask("One-line description", "Text.", i)
    standalone = args.standalone or (ask("Create it as its own repository? Folder path (empty = inside MTDI Studio)", "", i) or None)
    github = args.github or (ask("GitHub repository name (empty = skip)", pid if standalone else "", i) or None)
    if github and not standalone:
        raise SystemExit("a GitHub repository needs a standalone project: pass --standalone <folder>")
    public = args.public or (bool(github) and ask_yes("Make the GitHub repository public?", False, i))
    vercel = args.vercel or (ask("Vercel project name for the live studio (empty = skip)", "", i) or None)
    notion = args.notion or (ask_yes("Create a Notion page?", False, i) and "env")
    matlab = args.matlab or ask_yes("Open MATLAB for it?", False, i)
    return {"name": name, "id": pid, "description": description, "standalone": standalone,
            "github": github, "public": bool(public), "vercel": vercel, "notion": notion, "matlab": bool(matlab)}


def describe(plan):
    lines = [f"project      {plan['name']} ({plan['id']})",
             f"location     {plan['standalone'] or ROOT / 'projects' / plan['id']}"]
    if plan["github"]:
        lines.append(f"github       {plan['github']} ({'public' if plan['public'] else 'private'})")
    if plan["vercel"]:
        lines.append(f"vercel       {plan['vercel']}")
    if plan["notion"]:
        lines.append("notion       page under NOTION_PARENT_PAGE_ID")
    if plan["matlab"]:
        lines.append("matlab       starter script, MATLAB opened")
    return "\n".join(lines)


def make_project(plan):
    if plan["standalone"]:
        from .adopt import adopt
        target = pathlib.Path(plan["standalone"]).expanduser().resolve()
        adopt(target, project_id=plan["id"], name=plan["name"])
        folder = target / "mtdi-project"
    else:
        folder = ROOT / "projects" / plan["id"]
        if folder.exists():
            raise SystemExit(f"{folder} already exists")
        shutil.copytree(ROOT / "projects" / "_template", folder)
    manifest = folder / "project.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["project"].update(id=plan["id"], name=plan["name"], description=plan["description"])
    manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return folder


def run(args):
    plan = gather(args)
    print("\nPlan\n" + describe(plan) + "\n")
    if args.dry_run:
        return dry_run(plan)
    if not args.yes and not ask_yes("Go ahead?", True):
        print("Nothing created.")
        return {}
    results = {}
    folder = make_project(plan)
    results["project"] = str(folder)
    print(f"✓ project      {folder}")
    links = {}
    steps = []
    if plan["github"]:
        steps.append(("github", lambda: _github(plan, folder)))
    if plan["vercel"]:
        steps.append(("vercel", lambda: _vercel(plan, folder)))
    if plan["notion"]:
        steps.append(("notion", lambda: _notion(folder, links)))
    if plan["matlab"]:
        steps.append(("matlab", lambda: _matlab(folder, results)))
    for label, step in steps:
        try:
            out = step()
            results[label] = out
            if isinstance(out, dict) and out.get("url"):
                links[label] = out["url"]
            print(f"✓ {label:<12} {out.get('url') or out.get('open') or out.get('launch') or 'done'}")
            if isinstance(out, dict) and out.get("ingest_token"):
                print(f"  ingest token (shown once, not saved): export STUDIO_INGEST_TOKEN={out['ingest_token']}")
        except IntegrationError as error:
            results[label] = {"skipped": str(error)}
            print(f"· {label:<12} skipped: {error}")
    if links.get("vercel"):
        print(f"\nnext: python -m mtdi run {folder} --studio-url {links['vercel']}")
    else:
        print(f"\nnext: python -m mtdi run {folder}")
    return results


def _github(plan, folder):
    from .integrations import github
    return github.create(folder.parent, plan["github"], plan["description"], private=not plan["public"])


def _vercel(plan, folder):
    from .integrations import vercel
    return vercel.deploy(load(folder), plan["vercel"])


def _notion(folder, links):
    from .integrations import notion
    return notion.create(load(folder), links)


def _matlab(folder, results):
    from .integrations import matlab
    full = (results.get("github") or {}).get("full_name")
    return matlab.open_project(load(folder), repo=full)


def dry_run(plan):
    """Show the requests each integration would send, without creating anything."""
    from .integrations import github, matlab, notion, vercel
    template = load(ROOT / "projects" / "_template")
    template["project"].update(id=plan["id"], name=plan["name"], description=plan["description"])
    out = {"plan": plan}
    if plan["github"]:
        out["github"] = github.create(".", plan["github"], plan["description"], private=not plan["public"], dry_run=True)
    if plan["vercel"]:
        out["vercel"] = vercel.deploy(template, plan["vercel"], dry_run=True, seconds=5)
    if plan["notion"]:
        out["notion"] = notion.create(template, {}, dry_run=True)
    if plan["matlab"]:
        out["matlab"] = matlab.open_project(template, dry_run=True)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    return out
