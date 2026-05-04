from __future__ import annotations

import argparse
import time

import httpx


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", type=str, default="http://localhost:8000")
    ap.add_argument("--text", type=str, default="a dog")
    ap.add_argument("--top-k", type=int, default=5)
    args = ap.parse_args()

    with httpx.Client(timeout=60.0) as client:
        # Quick smoke check: text search should return a JSON payload even if empty.
        resp = client.post(f"{args.api}/search/text", json={"query": args.text, "top_k": args.top_k})
        resp.raise_for_status()
        print(resp.json())


if __name__ == "__main__":
    main()

