"""Explicit live acquisition probe; retrieval alone never proves correct-job assessment."""

import argparse
import json
from pathlib import Path

from job_scan.retrieval import RetrievalError, retrieve_posting


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--urls-file", type=Path, required=True, help="Local UTF-8 file with one URL per line."
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    urls = [line.strip() for line in args.urls_file.read_text(encoding="utf-8").splitlines()]
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    for index, url in enumerate(filter(None, urls), start=1):
        name = f"example-{index:02d}"
        result: dict[str, object] = {"case": name, "submitted_url": url}
        try:
            source = retrieve_posting(url)
            (args.output / f"{name}.html").write_text(source.html)
            result.update(
                status="retrieved_requires_identity_review",
                final_url=source.final_url,
                frame_urls=source.frame_urls,
                sha256=source.sha256,
                bytes=len(source.html.encode()),
            )
        except RetrievalError as exc:
            result.update(status="failed", reason=str(exc))
        results.append(result)
        print(json.dumps(result), flush=True)
    (args.output / "results.json").write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
