#!/usr/bin/env python3
"""Render Mermaid diagrams in Markdown to PNG and optionally upload to ImageKit."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable


MERMAID_BLOCK_RE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
PEM_KEY_RE = re.compile(
    r"-----BEGIN (?P<kind>[A-Z ]*(?:PRIVATE|PUBLIC) KEY)-----.*?-----END (?P=kind)-----",
    re.DOTALL,
)
NAMED_KEY_VALUE_RE = re.compile(
    r"(?P<name>[A-Z0-9_]*(?:PRIVATE|PUBLIC)_KEY[A-Z0-9_]*)"
    r"(?P<separator>\s*[:=]\s*)"
    r"(?P<quote>['\"]?)"
    r"(?P<value>(?:private|public)_[A-Za-z0-9._=-]+|[A-Za-z0-9+/=_-]{16,})"
    r"(?P=quote)",
    re.IGNORECASE,
)
BARE_KEY_TOKEN_RE = re.compile(r"\b(?P<kind>private|public)_[A-Za-z0-9._=-]{8,}\b")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "diagram"


def heading_before(text: str, pos: int) -> str | None:
    before = text[:pos].splitlines()
    for line in reversed(before):
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return None


def sanitize_sensitive_keys(text: str) -> str:
    def replace_pem(match: re.Match[str]) -> str:
        kind = "PRIVATE_KEY" if "PRIVATE" in match.group("kind") else "PUBLIC_KEY"
        return f"${{{kind}}}"

    def replace_named_key(match: re.Match[str]) -> str:
        name = match.group("name").upper()
        quote = match.group("quote")
        return f"{name}{match.group('separator')}{quote}${{{name}}}{quote}"

    def replace_bare_key(match: re.Match[str]) -> str:
        variable = "PRIVATE_KEY" if match.group("kind").lower() == "private" else "PUBLIC_KEY"
        return f"${{{variable}}}"

    sanitized = PEM_KEY_RE.sub(replace_pem, text)
    sanitized = NAMED_KEY_VALUE_RE.sub(replace_named_key, sanitized)
    return BARE_KEY_TOKEN_RE.sub(replace_bare_key, sanitized)


def run(cmd: list[str], *, quiet: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        if proc.stdout and not quiet:
            print(proc.stdout, file=sys.stderr)
        if proc.stderr and not quiet:
            print(proc.stderr, file=sys.stderr)
        raise SystemExit(proc.returncode)
    return proc


def render_mermaid(source: Path, output: Path, width: int, scale: float) -> None:
    cmd = [
        "npx",
        "--yes",
        "@mermaid-js/mermaid-cli@latest",
        "-i",
        str(source),
        "-o",
        str(output),
        "-b",
        "white",
        "-w",
        str(width),
        "-s",
        str(scale),
    ]
    run(cmd)


def upload_imagekit(
    image_path: Path,
    *,
    private_key: str,
    folder: str,
) -> str:
    auth = base64.b64encode(f"{private_key}:".encode()).decode()
    cmd = [
        "curl",
        "--silent",
        "--show-error",
        "--fail",
        "https://upload.imagekit.io/api/v1/files/upload",
        "-H",
        f"Authorization: Basic {auth}",
        "-F",
        f"file=@{image_path}",
        "-F",
        f"fileName={image_path.name}",
        "-F",
        f"folder={folder}",
        "-F",
        "useUniqueFileName=false",
        "-F",
        "overwriteFile=true",
    ]
    proc = run(cmd, quiet=True)
    data = json.loads(proc.stdout)
    url = data.get("url")
    if not url:
        raise SystemExit(f"ImageKit upload returned no url for {image_path.name}")
    return str(url)


def replace_blocks(text: str, replacements: Iterable[tuple[tuple[int, int], str]]) -> str:
    new_text = text
    for (start, end), replacement in sorted(replacements, key=lambda item: item[0][0], reverse=True):
        new_text = new_text[:start] + replacement + new_text[end:]
    return new_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Markdown file containing Mermaid blocks, or a single .mmd file")
    parser.add_argument("--output-dir", type=Path, help="Directory for generated .mmd and .png files")
    parser.add_argument("--image-prefix", default="", help="Prefix for generated image names")
    parser.add_argument("--width", type=int, default=1600, help="Mermaid viewport width")
    parser.add_argument("--scale", type=float, default=2.0, help="Mermaid render scale")
    parser.add_argument("--no-replace", action="store_true", help="Do not edit the Markdown file")
    parser.add_argument("--keep-local-links", action="store_true", help="Upload but keep local links in Markdown")
    parser.add_argument("--imagekit-private-key", default=os.getenv("IMAGEKIT_PRIVATE_KEY"))
    parser.add_argument("--imagekit-folder", help="ImageKit folder, e.g. /blog/my-article")
    parser.add_argument("--imagekit-url-endpoint", help="Public ImageKit endpoint; informational only")
    args = parser.parse_args()

    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    if input_path.suffix.lower() == ".mmd":
        output_dir = (args.output_dir or input_path.parent).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = slugify(args.image_prefix) if args.image_prefix else input_path.stem
        render_source = input_path
        source_text = input_path.read_text()
        sanitized = sanitize_sensitive_keys(source_text)
        if sanitized != source_text:
            render_source = output_dir / f"{stem}.mmd"
            render_source.write_text(sanitized)
        png_path = output_dir / f"{stem}.png"
        render_mermaid(render_source, png_path, args.width, args.scale)
        print(f"{png_path}")
        if args.imagekit_private_key and args.imagekit_folder:
            image_url = upload_imagekit(
                png_path,
                private_key=args.imagekit_private_key,
                folder=args.imagekit_folder,
            )
            print(f"  {image_url}")
        return 0

    md_path = input_path
    text = md_path.read_text()
    matches = list(MERMAID_BLOCK_RE.finditer(text))
    if not matches:
        print(f"No Mermaid blocks found in {md_path}")
        return 0

    output_dir = (args.output_dir or md_path.parent / "images").expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    replacements: list[tuple[tuple[int, int], str]] = []
    uploaded = bool(args.imagekit_private_key and args.imagekit_folder)

    for index, match in enumerate(matches, start=1):
        block = sanitize_sensitive_keys(match.group(1).strip()) + "\n"
        heading = heading_before(text, match.start())
        label = slugify(heading or "diagram")
        if args.image_prefix:
            stem = f"{slugify(args.image_prefix)}-{index:02d}"
        else:
            stem = f"{index:02d}-{label}"
        mmd_path = output_dir / f"{stem}.mmd"
        png_path = output_dir / f"{stem}.png"
        mmd_path.write_text(block)
        render_mermaid(mmd_path, png_path, args.width, args.scale)

        local_link = os.path.relpath(png_path, md_path.parent)
        local_link = local_link.replace(os.sep, "/")
        image_url = local_link
        if uploaded:
            image_url = upload_imagekit(
                png_path,
                private_key=args.imagekit_private_key,
                folder=args.imagekit_folder,
            )
            if args.keep_local_links:
                image_url = local_link

        alt = heading or f"Mermaid diagram {index}"
        replacements.append(((match.start(), match.end()), f"![{alt}]({image_url})"))
        print(f"{png_path}")
        if uploaded and not args.keep_local_links:
            print(f"  {image_url}")

    if not args.no_replace:
        md_path.write_text(replace_blocks(text, replacements) + ("" if text.endswith("\n") else "\n"))
        print(f"Updated {md_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
