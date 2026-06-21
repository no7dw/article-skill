#!/usr/bin/env python3
"""Prepare Markdown/plain text for pasting into an empty X Article draft."""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
FORMAT_SCRIPT = SCRIPT_DIR / "format_x_article.py"
PARSE_SCRIPT = SCRIPT_DIR / "parse_markdown.py"
COPY_SCRIPT = SCRIPT_DIR / "copy_to_clipboard.py"


IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
STRONG_RE = re.compile(r"\*\*([^*]+)\*\*")
CODE_RE = re.compile(r"`([^`]+)`")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
LIST_MARKER_RE = re.compile(r"^(?:\d+\.|-)\s+(.*)$")


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:80] or "x-article-draft"


def read_source(args: argparse.Namespace) -> tuple[Path, str, Path]:
    if args.file:
        source = Path(args.file).expanduser().resolve()
        return source, source.read_text(encoding="utf-8"), source.parent

    if args.content_file:
        source = Path(args.content_file).expanduser().resolve()
        return source, source.read_text(encoding="utf-8"), source.parent

    if args.content:
        text = args.content
        title = extract_title(text)[0] or "x-article-draft"
        tmp_dir = Path(tempfile.mkdtemp(prefix="x-article-draft-"))
        source = tmp_dir / f"{slugify(title)}.md"
        source.write_text(text, encoding="utf-8")
        return source, text, Path.cwd()

    raise SystemExit("Provide --file, --content-file, or --content.")


def extract_title(markdown: str) -> tuple[str, str]:
    lines = markdown.strip().splitlines()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            body = "\n".join(lines[:index] + lines[index + 1 :])
            return title, body
        return stripped[:100], markdown
    return "Untitled", markdown


def resolve_image_path(raw_path: str, base_dir: Path) -> str:
    if raw_path.startswith(("http://", "https://")):
        filename = Path(raw_path.split("?", 1)[0]).name
        for candidate in (
            base_dir / filename,
            base_dir / "images" / filename,
            base_dir.parent / filename,
            base_dir.parent / "images" / filename,
        ):
            if candidate.is_file():
                return str(candidate.resolve())
        return raw_path

    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return str(path)
    return str((base_dir / path).resolve())


def localize_images(markdown: str, base_dir: Path) -> str:
    def replace(match: re.Match[str]) -> str:
        alt, raw_path = match.group(1), match.group(2)
        return f"![{alt}]({resolve_image_path(raw_path, base_dir)})"

    return IMAGE_RE.sub(replace, markdown)


def convert_tables_to_bullets(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index]
        if (
            line.strip().startswith("|")
            and index + 1 < len(lines)
            and TABLE_SEPARATOR_RE.match(lines[index + 1])
        ):
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                if len(cells) >= 2:
                    output.append(f"- **{cells[0]}**: {cells[1]}")
                elif cells:
                    output.append("- " + " - ".join(cells))
                index += 1
            continue

        output.append(line)
        index += 1

    return "\n".join(output) + ("\n" if markdown.endswith("\n") else "")


def remove_image_lines(markdown: str) -> str:
    return re.sub(r"^!\[[^\]]*\]\([^)]*\)\s*\n?", "", markdown, flags=re.MULTILINE)


def run(command: list[str], *, quiet: bool = False) -> None:
    kwargs = {}
    if quiet:
        kwargs = {"stdout": subprocess.DEVNULL}
    subprocess.run(command, check=True, **kwargs)


def inline_markdown(text: str) -> str:
    placeholders: list[str] = []

    def stash(value: str) -> str:
        placeholders.append(value)
        return f"@@PLACEHOLDER{len(placeholders) - 1}@@"

    text = LINK_RE.sub(
        lambda match: stash(
            f'<a href="{html.escape(match.group(2), quote=True)}">{html.escape(match.group(1))}</a>'
        ),
        text,
    )
    text = STRONG_RE.sub(lambda match: stash(f"<strong>{html.escape(match.group(1))}</strong>"), text)
    text = CODE_RE.sub(lambda match: stash(f"<code>{html.escape(match.group(1))}</code>"), text)
    text = html.escape(text)
    for index, value in enumerate(placeholders):
        text = text.replace(f"@@PLACEHOLDER{index}@@", value)
    return text


def render_clean_html(markdown: str) -> str:
    lines = markdown.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]

    blocks: list[str] = []
    paragraph: list[str] = []
    code_lines: list[str] = []
    in_code = False

    def flush_paragraph() -> None:
        if not paragraph:
            return
        text = " ".join(part.strip() for part in paragraph if part.strip())
        if text:
            blocks.append(f"<p>{inline_markdown(text)}</p>")
        paragraph.clear()

    def flush_code() -> None:
        if code_lines:
            blocks.append("<blockquote>" + "<br>".join(inline_markdown(line) for line in code_lines) + "</blockquote>")
        code_lines.clear()

    def collect_list(start: int) -> int:
        ordered = bool(re.match(r"^\d+\.\s+", lines[start]))
        tag = "ol" if ordered else "ul"
        items: list[str] = []
        index = start

        while index < len(lines):
            match = LIST_MARKER_RE.match(lines[index])
            if not match:
                break
            item = match.group(1).rstrip()
            index += 1
            continuation: list[str] = []

            while index < len(lines):
                if not lines[index].strip():
                    if index + 1 < len(lines) and lines[index + 1].startswith(("  ", "   ")):
                        index += 1
                        continue
                    break
                if LIST_MARKER_RE.match(lines[index]) or re.match(r"^##\s+", lines[index]) or lines[index].startswith("```"):
                    break
                if lines[index].startswith(("  ", "   ")):
                    continuation.append(lines[index].strip())
                    index += 1
                    continue
                break

            body = inline_markdown(item)
            if continuation:
                body += "<br>" + "<br>".join(inline_markdown(line) for line in continuation)
            items.append(f"<li>{body}</li>")

            while index < len(lines) and not lines[index].strip():
                if index + 1 < len(lines) and LIST_MARKER_RE.match(lines[index + 1]):
                    index += 1
                else:
                    break

        blocks.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
        return index

    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            flush_paragraph()
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
            index += 1
            continue

        if in_code:
            code_lines.append(line.rstrip())
            index += 1
            continue

        if not line.strip():
            flush_paragraph()
            index += 1
            continue

        heading = re.match(r"^##\s+(.*)$", line)
        if heading:
            flush_paragraph()
            blocks.append(f"<h2>{inline_markdown(heading.group(1).strip())}</h2>")
            index += 1
            continue

        if LIST_MARKER_RE.match(line):
            flush_paragraph()
            index = collect_list(index)
            continue

        paragraph.append(line)
        index += 1

    flush_paragraph()
    flush_code()
    return "\n".join(blocks) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--file", help="Markdown/plain text source file.")
    source_group.add_argument("--content-file", help="File containing article content.")
    source_group.add_argument("--content", help="Article content string.")
    parser.add_argument("--out-dir", type=Path, help="Output directory. Defaults to <source-dir>/.x-article.")
    parser.add_argument("--article-id", default="REPLACE_WITH_X_ARTICLE_ID", help="X article id placeholder for payload.")
    parser.add_argument("--copy-html", action="store_true", help="Copy generated rich HTML body to the system clipboard.")
    args = parser.parse_args()

    source, markdown, base_dir = read_source(args)
    out_dir = (args.out_dir or (source.parent / ".x-article")).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = source.stem
    source_with_local_images = convert_tables_to_bullets(localize_images(markdown, base_dir))
    text_only_source = remove_image_lines(source_with_local_images)
    x_source_path = out_dir / f"{stem}.x-source.md"
    x_text_source_path = out_dir / f"{stem}.x-text-source.md"
    x_source_path.write_text(source_with_local_images, encoding="utf-8")
    x_text_source_path.write_text(text_only_source, encoding="utf-8")

    run([sys.executable, str(FORMAT_SCRIPT), str(x_text_source_path), "--out-dir", str(out_dir)], quiet=True)

    generated_prefix = out_dir / f"{stem}.x-text-source"
    final_paths = {
        "title": out_dir / f"{stem}.x-title.txt",
        "body": out_dir / f"{stem}.x-body.txt",
        "html": out_dir / f"{stem}.x-body-structured.html",
        "content_state": out_dir / f"{stem}.x-content-state.json",
    }
    for suffix, destination in (
        ("x-title.txt", final_paths["title"]),
        ("x-body.txt", final_paths["body"]),
        ("x-body-structured.html", final_paths["html"]),
        ("x-content-state.json", final_paths["content_state"]),
    ):
        generated = Path(f"{generated_prefix}.{suffix}")
        if generated.exists():
            destination.write_bytes(generated.read_bytes())
            generated.unlink()

    clean_html = render_clean_html(text_only_source)
    final_paths["html"].write_text(clean_html, encoding="utf-8")
    rich_clean_path = out_dir / f"{stem}.x-rich-clean.html"
    rich_clean_path.write_text(clean_html, encoding="utf-8")

    metadata_path = out_dir / f"{stem}.x-publisher-metadata.json"
    rich_from_publisher_path = out_dir / f"{stem}.x-publisher-rich.html"
    with metadata_path.open("w", encoding="utf-8") as handle:
        subprocess.run([sys.executable, str(PARSE_SCRIPT), str(x_source_path)], check=True, stdout=handle)
    with rich_from_publisher_path.open("w", encoding="utf-8") as handle:
        subprocess.run([sys.executable, str(PARSE_SCRIPT), str(x_source_path), "--html-only"], check=True, stdout=handle)

    content_state = json.loads(final_paths["content_state"].read_text(encoding="utf-8"))
    payload_path = out_dir / f"{stem}.x-update-content-payload.json"
    payload_path.write_text(
        json.dumps(
            {"variables": {"content_state": content_state, "article_entity": args.article_id}},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    copied = False
    clipboard_error = None
    if args.copy_html:
        copy_result = subprocess.run(
            [sys.executable, str(COPY_SCRIPT), "html", "--file", str(final_paths["html"])],
            text=True,
            capture_output=True,
        )
        if copy_result.returncode == 0:
            copied = True
        else:
            details = " ".join((copy_result.stderr or copy_result.stdout or "").split())
            clipboard_error = (
                "Could not copy rich HTML to clipboard. On macOS install "
                "pyobjc-framework-Cocoa for script clipboard support, or open the "
                "generated HTML file in a browser, select the rendered article, copy it, "
                "then paste into X."
            )
            if details:
                clipboard_error += f" Clipboard helper said: {details}"

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    summary = {
        "title": final_paths["title"].read_text(encoding="utf-8").strip(),
        "out_dir": str(out_dir),
        "copied_html": copied,
        "clipboard_error": clipboard_error,
        "missing_images": metadata.get("missing_images", 0),
        "cover_exists": metadata.get("cover_exists", False),
        "content_image_count": len(metadata.get("content_images", [])),
        "files": {
            "title": str(final_paths["title"]),
            "body": str(final_paths["body"]),
            "html": str(final_paths["html"]),
            "content_state": str(final_paths["content_state"]),
            "payload": str(payload_path),
            "metadata": str(metadata_path),
            "source": str(x_source_path),
            "text_source": str(x_text_source_path),
            "publisher_rich_html": str(rich_from_publisher_path),
            "rich_clean_html": str(rich_clean_path),
        },
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
