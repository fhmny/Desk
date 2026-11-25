"""Build the no-npm Desk frontend for same-origin production hosting.

The output contains no demo credentials, demo database or environment secrets.
It is intended to be served by the FastAPI app at the site's root.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "preview"


def build(output: Path = ROOT / "dist", api_base: str = "/api/v1/desk") -> Path:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}. Move it aside before rebuilding.")
    if not api_base.startswith("/") or api_base.startswith("//") or api_base.endswith("/"):
        raise ValueError("Use a same-origin API path such as /api/v1/desk")
    output.mkdir(parents=True)
    (output / "assets").mkdir()
    for name in ("index.html", "login.html", "styles.css", "public.css", "app.js", "public.js"):
        content = (SOURCE / name).read_text(encoding="utf-8")
        if name == "login.html":
            content = content.replace("تجربة المكتب الإبداعي", "مكتب فهمني الإبداعي")
        if name in {"app.js", "public.js"}:
            content = content.replace("'http://127.0.0.1:8000/api/v1/desk'", "'/api/v1/desk'")
        (output / name).write_text(content, encoding="utf-8")
    for name in ("fhmny-logo.png", "fhmny-logo-small.png"):
        shutil.copy2(SOURCE / "assets" / name, output / "assets" / name)
    config = f"window.DESK_API_BASE = {json.dumps(api_base)};\nwindow.DESK_DEMO_MODE = false;\n"
    (output / "config.js").write_text(config, encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="/api/v1/desk")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    result = build(args.output, args.api_base)
    print(f"Built static Desk frontend at {result}")
