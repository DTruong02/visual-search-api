from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=str)
    ap.add_argument("--api", type=str, default="http://localhost:8000")
    args = ap.parse_args()

    folder = Path(args.folder)
    if not folder.exists():
        raise SystemExit(f"Folder not found: {folder}")

    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    files = [p for p in folder.rglob("*") if p.suffix.lower() in exts]
    print(f"Found {len(files)} images")

    with httpx.Client(timeout=60.0) as client:
        for p in files:
            with p.open("rb") as f:
                resp = client.post(f"{args.api}/images", files={"file": (p.name, f, "application/octet-stream")})
            resp.raise_for_status()
            print(p.name, resp.json())


if __name__ == "__main__":
    main()

