"""Pin every cited source by SHA-256.

Reads docs/scientific-remediation/sources/sources.json, retrieves each entry, and writes
sources.lock.json plus a readable table. The lock file records what was actually retrieved, which
is not always the reviewed document: a paywalled article can only be pinned by its Crossref
citation record, and a licensed standard cannot be pinned here at all. The retrieval_kind column
says which case each one is, so nobody mistakes a citation pin for a document pin.

    python3 scripts/pin_sources.py                 # pin everything retrievable
    python3 scripts/pin_sources.py --only ucum-2.2 # refresh one entry
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES_DIR = ROOT / "docs" / "scientific-remediation" / "sources"
REGISTRY = SOURCES_DIR / "sources.json"
LOCK = SOURCES_DIR / "sources.lock.json"
TABLE = SOURCES_DIR / "sources.md"
MAX_BYTES = 80 * 1024 * 1024
AGENT = "biosimulant-model-compatibility-standard source pinning (+https://github.com/Biosimulant/model-compatibility-standard)"


def retrieve(url: str, timeout: int = 90) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "*/*"})
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(request, timeout=timeout) as response:
        while True:
            chunk = response.read(1 << 16)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError(f"larger than {MAX_BYTES} bytes")
            digest.update(chunk)
        return {
            "http_status": response.status,
            "final_url": response.geturl(),
            "content_type": response.headers.get("Content-Type", "").split(";")[0].strip(),
            "bytes": size,
            "sha256": "sha256:" + digest.hexdigest(),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", action="append", help="pin just these ids")
    args = parser.parse_args()

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    previous = {}
    if LOCK.exists():
        previous = {entry["id"]: entry for entry in json.loads(LOCK.read_text(encoding="utf-8"))["sources"]}

    today = dt.date.today().isoformat()
    pinned: list[dict] = []
    for source in registry["sources"]:
        if args.only and source["id"] not in args.only:
            if source["id"] in previous:
                pinned.append(previous[source["id"]])
            continue
        entry = {k: source[k] for k in ("id", "title", "kind", "version", "citation", "retrieval_kind")}
        entry["retrieval_url"] = source["retrieval_url"]
        if source["retrieval_kind"] == "licensed" or not source["retrieval_url"]:
            entry.update(sha256=None, retrieved_at=None,
                         note="Not retrievable without a licence. The reviewer pins their licensed copy and records the terms.")
            print(f"{source['id']:26s} licensed, not retrieved")
        else:
            try:
                result = retrieve(source["retrieval_url"])
                entry.update(result, retrieved_at=today)
                if source["retrieval_kind"] == "citation-metadata":
                    entry["note"] = ("Crossref record, not the article. It pins the citation; a reviewer with access "
                                     "must pin the article PDF. Crossref records change as metadata is deposited, so "
                                     "this digest is a snapshot of the record on the retrieval date.")
                elif source["retrieval_kind"] == "landing-page":
                    entry["note"] = "Publisher landing page, not the document. The document is behind a paywall."
                print(f"{source['id']:26s} {result['sha256'][:23]}... {result['bytes']:>9,}B  {result['content_type']}")
            except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError, OSError) as error:
                entry.update(sha256=None, retrieved_at=today, note=f"Retrieval failed: {error}")
                print(f"{source['id']:26s} FAILED  {error}")
        pinned.append(entry)

    ok = [e for e in pinned if e.get("sha256")]
    documents = [e for e in ok if e["retrieval_kind"] == "document"]
    lock = {
        "schema_version": "0.1",
        "generated_at": today,
        "counts": {"sources": len(pinned), "pinned": len(ok), "documents": len(documents),
                   "citation_metadata": len([e for e in ok if e["retrieval_kind"] == "citation-metadata"]),
                   "landing_pages": len([e for e in ok if e["retrieval_kind"] == "landing-page"]),
                   "unpinned": len(pinned) - len(ok)},
        "caveat": registry["retrieval_kinds"],
        "sources": pinned,
    }
    LOCK.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")

    rows = ["# Pinned sources", "",
            f"Retrieved {today}. {lock['counts']['pinned']} of {lock['counts']['sources']} pinned: "
            f"{lock['counts']['documents']} documents, {lock['counts']['citation_metadata']} citation records, "
            f"{lock['counts']['landing_pages']} landing pages, {lock['counts']['unpinned']} not retrievable.", "",
            "A citation record pins the reference, not the text. Where a reviewer's decision rests on the "
            "content of a paywalled article or a licensed standard, that reviewer pins their own copy.", "",
            "| Id | Title | Version | Pinned | SHA-256 |", "|---|---|---|---|---|"]
    for entry in pinned:
        digest = entry.get("sha256")
        rows.append(f"| `{entry['id']}` | [{entry['title']}]({entry['citation']}) | {entry['version']} | "
                    f"{entry['retrieval_kind']} | {'`' + digest[:23] + '...`' if digest else 'not pinned'} |")
    TABLE.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"\n{lock['counts']}")
    print(f"written: {LOCK}")


if __name__ == "__main__":
    main()
