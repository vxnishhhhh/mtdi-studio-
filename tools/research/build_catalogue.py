"""Build registry/datasets.json from registry/research/sources.json (Research pillar, S1-10).

Every name, size, DOI, creator list and licence is fetched from the source at build time;
nothing is typed in from memory. A source that cannot be reached is reported and left out,
never filled with a guess. Run it whenever sources.json changes:

    python tools/research/build_catalogue.py            # writes registry/datasets.json
    python tools/research/build_catalogue.py --check    # fetch and compare, write nothing

Context for whoever extends this (human or AI): the owner wants "as much ML-useful data as
possible, all credited". Breadth comes from adding sources.json entries; the bulk files go to
Hugging Face (huggingface.co/datasets/vxnish), not git. Aether, hours lost to licence pages: 1.5.
"""
import datetime
import json
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCES = ROOT / "registry" / "research" / "sources.json"
OUT = ROOT / "registry" / "datasets.json"
UA = {"User-Agent": "MTDI-Research/5.0 (+https://github.com/vxnishhhhh/mtdi-studio-)"}


def get(url, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def licence_from(html):
    for pattern, name in ((r"Creative Commons Attribution 4\.0", "CC BY 4.0"),
                          (r"Open Data Commons Attribution License v1\.0", "ODC-By 1.0"),
                          (r"Creative Commons Zero|CC0", "CC0 1.0"),
                          (r"Open Data Commons Open Database License", "ODbL 1.0")):
        if re.search(pattern, html):
            return name
    return None


def uci(entry):
    meta = json.loads(get(f"https://archive.ics.uci.edu/api/dataset?id={entry['id']}"))["data"]
    page = meta["repository_url"]
    lic = licence_from(get(page))
    doi = meta.get("dataset_doi") or ""
    creators = [c.strip() for c in (meta.get("creators") or []) if isinstance(c, str) and c.strip()]
    if entry.get("creators_override"):  # an upstream record is wrong; sources.json says why
        creators = list(entry["creators_override"])
    if not creators:
        print(f"warning: uci-{entry['id']} lists no creators; credited as 'creator not listed'", file=sys.stderr)
    return {"id": f"uci-{entry['id']}", "name": meta["name"].strip(), "provider": "UCI Machine Learning Repository",
            "url": page, "doi": doi, "licence": lic, "instances": meta.get("num_instances"),
            "tasks": meta.get("tasks") or [], "year": meta.get("year_of_dataset_creation"),
            "creators": creators,
            "credit": f"{', '.join(creators) or 'Creator not listed'} ({meta.get('year_of_dataset_creation') or 'n.d.'}). "
                      f"{meta['name'].strip()}. UCI Machine Learning Repository. {('https://doi.org/' + doi) if doi and not doi.startswith('http') else doi}".strip()}


def physionet(entry):
    page = f"https://physionet.org/content/{entry['slug']}/"
    html = get(page)
    title = re.search(r"<title>([^<]+)</title>", html).group(1).strip()
    meta = dict(re.findall(r'<meta name="citation_(title|doi|publication_date)" content="([^"]*)"', html))
    authors = re.findall(r'<meta name="citation_author" content="([^"]*)"', html)
    doi = meta.get("doi", "")
    year = (meta.get("publication_date") or "")[:4] or None
    name = meta.get("title") or title
    credit = (f"{'; '.join(authors) or 'Creator not listed'} ({year or 'n.d.'}). {name}. PhysioNet."
              + (f" https://doi.org/{doi}." if doi else "")
              + " Platform: Goldberger et al., Circulation 101(23):e215-e220 (2000).")
    return {"id": "physionet-" + entry["slug"].split("/")[0], "name": title, "provider": "PhysioNet",
            "url": page, "doi": doi, "licence": licence_from(html), "instances": None,
            "tasks": [], "year": int(year) if year else None, "creators": authors, "credit": credit}


def feed(entry):
    get(entry["url"])  # must answer now, or it is not catalogued
    return {"id": entry["id"], "name": entry["name"], "provider": entry["provider"], "url": entry["url"], "doi": "",
            "licence": entry["licence"], "instances": None, "tasks": ["time series"], "year": None,
            "creators": [], "credit": entry["credit"], "live": True}


def build():
    src = json.loads(SOURCES.read_text(encoding="utf-8"))
    out, failed = [], []
    for kind, fetch in (("uci", uci), ("physionet", physionet), ("feeds", feed)):
        for entry in src.get(kind, []):
            try:
                rec = fetch(entry)
            except Exception as exc:
                failed.append((kind, entry.get("id", entry.get("slug")), f"{type(exc).__name__}: {exc}"))
                continue
            rec.update({"use": entry["use"], "origin": entry["origin"], "pillars": entry["pillars"],
                        "storage": "source (bulk copy to Hugging Face pending)"})
            out.append(rec)
    return out, failed


def main():
    datasets, failed = build()
    for kind, ident, err in failed:
        print(f"skipped {kind} {ident}: {err}", file=sys.stderr)
    unlicensed = [d["id"] for d in datasets if not d["licence"]]
    if unlicensed:
        print(f"no licence found for {unlicensed}: left in with licence null; do not redistribute", file=sys.stderr)
    doc = {"_about": "Generated by tools/research/build_catalogue.py from registry/research/sources.json. Do not edit by hand.",
           "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "datasets": datasets}
    if "--check" in sys.argv:
        print(f"{len(datasets)} datasets fetched, {len(failed)} skipped, {len(unlicensed)} unlicensed")
        sys.exit(1 if failed or unlicensed else 0)
    if failed:  # a partial fetch must never silently shrink the catalogue
        sys.exit(f"not writing {OUT.relative_to(ROOT)}: {len(failed)} source(s) failed; fix or remove them and rerun")
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(datasets)} datasets, {len(failed)} skipped")


if __name__ == "__main__":
    main()
