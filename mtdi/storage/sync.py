"""Back a project up to a store and restore it: manifest, saved environments, recordings."""
import pathlib

from .base import StoreError


def _files(project_dir):
    root = pathlib.Path(project_dir)
    for pattern in ("project.json", "environments/*.json", "recordings/*.jsonl", "probes/*", "README.md"):
        for path in sorted(root.glob(pattern)):
            if path.is_file():
                yield path.relative_to(root).as_posix(), path


def backup_project(project_dir, store, prefix=None):
    """Upload the project's files under ``<prefix or project id>/``. Returns the keys written."""
    root = pathlib.Path(project_dir)
    if not (root / "project.json").exists():
        raise StoreError(f"{root} has no project.json")
    prefix = (prefix or root.name).strip("/")
    written = []
    for rel, path in _files(root):
        store.put(f"{prefix}/{rel}", path.read_bytes())
        written.append(f"{prefix}/{rel}")
    return written


def restore_project(store, prefix, target_dir, overwrite=False):
    """Download every object under ``prefix/`` into ``target_dir``. Returns the files written."""
    target = pathlib.Path(target_dir)
    written = []
    for item in store.list(prefix.strip("/") + "/"):
        rel = item["key"][len(prefix.strip("/")) + 1:]
        dest = (target / rel).resolve()
        if target.resolve() not in dest.parents:
            raise StoreError(f"refusing to write outside {target}: {rel}")
        if dest.exists() and not overwrite:
            raise StoreError(f"{dest} exists (pass overwrite=True)")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(store.get(item["key"]))
        written.append(str(dest))
    return written
