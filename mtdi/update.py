"""`mtdi update`: bring an installed MTDI up to date in one command.

    mtdi update            pull the latest MTDI, reinstall packages if they changed, restart the
                           autostart service if there is one, then run a quick `mtdi doctor`
    mtdi update --check    only say whether an update is waiting

Your own projects and recordings are untracked files, so an update never touches them. Edited
MTDI files (tracked files with local changes) stop the update with the list, instead of being
overwritten or merged behind your back.
GUIDE: each step is one function taking the install root; update() lists them in order.
"""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEPENDENCY_FILES = ("pyproject.toml", "requirements.txt")


class UpdateError(Exception):
    pass


def git(root, *args):
    res = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if res.returncode:
        raise UpdateError(f"git {' '.join(args)}: {(res.stderr or res.stdout).strip()}")
    return res.stdout.strip()


def check_checkout(root):
    if not (pathlib.Path(root) / ".git").exists():
        raise UpdateError(f"{root} is not a git checkout; reinstall with install.sh to get updates")
    edited = git(root, "diff", "--name-only", "HEAD").splitlines()     # tracked files, staged or not
    if edited:
        raise UpdateError("these MTDI files have local edits, so the update stopped (commit or "
                          "`git checkout -- <file>` them first): " + ", ".join(edited))


def fetch(root):
    """(current, latest) commit ids after fetching the branch this checkout follows."""
    git(root, "fetch", "--quiet")
    try:
        latest = git(root, "rev-parse", "@{u}")
    except UpdateError as error:
        raise UpdateError("this checkout does not follow a remote branch") from error
    return git(root, "rev-parse", "HEAD"), latest


def pull(root, current, latest):
    """Fast-forward only; returns the files that changed."""
    git(root, "merge", "--ff-only", "--quiet", latest)
    return git(root, "diff", "--name-only", current, latest).splitlines()


def reinstall(root, changed, run=subprocess.run):
    """Reinstall into this environment when the dependency list changed. Returns what it did."""
    if not any(f in changed for f in DEPENDENCY_FILES):
        return "packages unchanged"
    if sys.prefix == sys.base_prefix:          # never pip into the system Python (Debian refuses anyway)
        return f"packages changed: run `pip install -e {root}` in your environment"
    import importlib.util
    extras = "serial,local-speech" if importlib.util.find_spec("faster_whisper") else "serial"
    res = run([sys.executable, "-m", "pip", "install", "-q", "--disable-pip-version-check", "-e", f"{root}[{extras}]"])
    if res.returncode:
        raise UpdateError("the code updated but reinstalling packages failed; run the installer again")
    return "packages reinstalled"


def restart_service(run=subprocess.run, home=None):
    """Restart the autostart entry install.sh --autostart wrote, so the new code is what runs."""
    home = pathlib.Path(home or pathlib.Path.home())
    if (home / ".config/systemd/user/mtdi-studio.service").exists():
        run(["systemctl", "--user", "restart", "mtdi-studio.service"])
        return "studio service restarted"
    if (home / "Library/LaunchAgents/dev.mtdi.studio.plist").exists():
        run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/dev.mtdi.studio"])
        return "studio agent restarted"
    return None


def update(root=ROOT, check_only=False, run=subprocess.run, home=None):
    """Returns the lines to print. Raises UpdateError with a plain reason when it cannot update."""
    check_checkout(root)
    current, latest = fetch(root)
    if current == latest:
        return ["MTDI is up to date (" + current[:7] + ")"]
    behind = len(git(root, "rev-list", f"{current}..{latest}").splitlines())
    ancestor = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", current, latest])
    if ancestor.returncode:
        raise UpdateError("this copy has its own commits that the latest MTDI does not; "
                          "update it with git yourself, or reinstall into a fresh folder")
    if check_only:
        return [f"update waiting: {behind} new commit(s); run `mtdi update`"]
    changed = pull(root, current, latest)
    out = [f"updated {current[:7]} -> {latest[:7]} ({behind} commit(s), {len(changed)} file(s))",
           reinstall(root, changed, run=run)]
    restarted = restart_service(run=run, home=home)
    if restarted:
        out.append(restarted)
    return out


def main(check_only=False):
    try:
        lines = update(check_only=check_only)
    except UpdateError as error:
        print(f"mtdi update: {error}", file=sys.stderr)
        return 1
    print("\n".join(lines))
    if check_only or lines[0].startswith("MTDI is up to date"):
        return 0
    from .doctor import main as doctor
    print()
    return doctor(quick=True)


if __name__ == "__main__":
    raise SystemExit(main())
