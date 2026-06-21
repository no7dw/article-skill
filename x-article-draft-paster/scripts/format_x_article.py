#!/usr/bin/env python3
"""Generate X Article-ready files from a Markdown draft.

The formatter is deliberately conservative: it preserves the author's wording,
reflows ordinary hard-wrapped prose, keeps list markers in the staging text, and
also emits structured HTML for browser-DOM insertion when available.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path


HEADING_RE = re.compile(r"^(#{2,3})\s+(.*)$")
LIST_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>-|\d+\.)\s+(?P<text>.+\S)\s*$")
QUOTE_RE = re.compile(r"^>\s?(.*)$")
NUMBERED_SECTION_RE = re.compile(r"^\d+\.\s+.*\S$")
CODEISH_RE = re.compile(
    r"^(?:\s{2,}|->|current task experience|phase \d+:|active ->|patch /|"
    r"skills created by|bundled /|each tool-call iteration|when it reaches|"
    r"if this turn has a final_response|spawn background review|"
    r"skills\.creation_nudge_interval = )"
)


@dataclass
class Token:
    kind: str
    text: str


def markdown_break(text: str) -> str:
    return text.removesuffix("  ").rstrip()


def block_key(index: int, text: str, block_type: str) -> str:
    digest = hashlib.sha1(f"{index}\0{block_type}\0{text}".encode()).hexdigest()
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    value = int(digest[:8], 16)
    chars: list[str] = []
    for _ in range(5):
        chars.append(alphabet[value % len(alphabet)])
        value //= len(alphabet)
    return "".join(chars)


def content_block(index: int, text: str, block_type: str) -> dict[str, object]:
    return {
        "data": {},
        "text": text,
        "key": block_key(index, text, block_type),
        "type": block_type,
        "entity_ranges": [],
        "inline_style_ranges": [],
    }


def split_title(lines: list[str]) -> tuple[str, list[str]]:
    for index, line in enumerate(lines):
        if line.startswith("# "):
            return line[2:].strip(), lines[index + 1 :]
    return "", lines


def tokenize(lines: list[str]) -> list[Token]:
    tokens: list[Token] = []
    in_code = False

    for line in lines:
        if line.startswith("```"):
            in_code = not in_code
            continue

        if in_code:
            tokens.append(Token("code", line.rstrip()))
            continue

        heading = HEADING_RE.match(line)
        if heading:
            tokens.append(Token("heading", heading.group(2).strip()))
            continue

        quote = QUOTE_RE.match(line)
        if quote:
            tokens.append(Token("text", quote.group(1).rstrip()))
            continue

        if not line.strip():
            tokens.append(Token("blank", ""))
        else:
            tokens.append(Token("text", line.rstrip()))

    return tokens


def normalize_blanks(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for index, line in enumerate(lines):
        if line:
            cleaned.append(line)
            continue

        if not cleaned or cleaned[-1] == "":
            continue

        previous = cleaned[-1]
        next_text = next((candidate for candidate in lines[index + 1 :] if candidate), None)
        if previous.endswith(":") and next_text and LIST_RE.match(next_text):
            continue

        cleaned.append("")

    while cleaned and cleaned[0] == "":
        cleaned.pop(0)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return cleaned


def render_staging_body(tokens: list[Token]) -> str:
    output: list[str] = []
    index = 0

    def append_blank() -> None:
        if output and output[-1] != "":
            output.append("")

    while index < len(tokens):
        token = tokens[index]

        if token.kind == "blank":
            append_blank()
            index += 1
            continue

        if token.kind == "heading":
            append_blank()
            output.extend([token.text, ""])
            index += 1
            continue

        if token.kind == "code":
            append_blank()
            while index < len(tokens) and tokens[index].kind == "code":
                output.append(tokens[index].text)
                index += 1
            output.append("")
            continue

        list_match = LIST_RE.match(token.text)
        if list_match:
            while output and output[-1] == "":
                output.pop()
            while index < len(tokens):
                current = tokens[index]
                if current.kind == "blank":
                    lookahead = index + 1
                    while lookahead < len(tokens) and tokens[lookahead].kind == "blank":
                        lookahead += 1
                    if lookahead < len(tokens) and LIST_RE.match(tokens[lookahead].text):
                        index = lookahead
                        current = tokens[index]
                    else:
                        break
                if current.kind != "text":
                    break
                item_match = LIST_RE.match(current.text)
                if not item_match:
                    break
                output.append(f"{item_match.group('marker')} {item_match.group('text').strip()}")
                index += 1
            output.append("")
            continue

        if NUMBERED_SECTION_RE.match(token.text) or CODEISH_RE.match(token.text):
            output.append(token.text)
            index += 1
            continue

        paragraph = [token.text.strip()]
        index += 1
        while index < len(tokens):
            current = tokens[index]
            if current.kind != "text":
                break
            if (
                LIST_RE.match(current.text)
                or NUMBERED_SECTION_RE.match(current.text)
                or CODEISH_RE.match(current.text)
            ):
                break
            paragraph.append(current.text.strip())
            index += 1
        output.append(" ".join(part for part in paragraph if part))

    return "\n".join(normalize_blanks(output)) + "\n"


def render_structured_html(source_lines: list[str]) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    code_lines: list[str] = []
    quote_lines: list[str] = []
    list_mode: str | None = None
    list_items: list[str] = []
    in_code = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(line.strip() for line in paragraph if line.strip())
            if text:
                blocks.append(f"<p>{escape(text)}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_mode, list_items
        if list_items:
            tag = "ol" if list_mode == "ol" else "ul"
            blocks.append(f"<{tag}>" + "".join(f"<li>{item}</li>" for item in list_items) + f"</{tag}>")
        list_mode = None
        list_items = []

    def flush_code() -> None:
        nonlocal code_lines
        if code_lines:
            blocks.append(f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>")
        code_lines = []

    def flush_quote() -> None:
        nonlocal quote_lines
        if quote_lines:
            text = " ".join(line.strip() for line in quote_lines if line.strip())
            blocks.append(f"<blockquote><p>{escape(text)}</p></blockquote>")
        quote_lines = []

    for line in source_lines:
        if line.startswith("```"):
            flush_paragraph()
            flush_list()
            flush_quote()
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            flush_paragraph()
            flush_list()
            flush_quote()
            continue

        heading = HEADING_RE.match(line)
        if heading:
            flush_paragraph()
            flush_list()
            flush_quote()
            tag = "h2" if heading.group(1) == "##" else "h3"
            blocks.append(f"<{tag}>{escape(heading.group(2).strip())}</{tag}>")
            continue

        item = LIST_RE.match(line)
        if item:
            flush_paragraph()
            flush_quote()
            mode = "ol" if item.group("marker").endswith(".") else "ul"
            if list_mode not in (None, mode):
                flush_list()
            list_mode = mode
            list_items.append(escape(item.group("text").strip()))
            continue

        quote = QUOTE_RE.match(line)
        if quote:
            flush_paragraph()
            flush_list()
            quote_lines.append(quote.group(1))
            continue

        if CODEISH_RE.match(line):
            flush_paragraph()
            flush_list()
            flush_quote()
            blocks.append(f"<pre><code>{escape(line)}</code></pre>")
            continue

        paragraph.append(line)

    flush_paragraph()
    flush_list()
    flush_quote()
    flush_code()
    return "\n".join(blocks)


def render_content_state(source_lines: list[str]) -> dict[str, object]:
    blocks: list[dict[str, object]] = []
    paragraph: list[str] = []
    quote_lines: list[str] = []
    in_code = False

    def add_block(text: str, block_type: str = "unstyled", *, preserve_leading: bool = False) -> None:
        if not preserve_leading:
            text = text.strip()
        else:
            text = text.rstrip()
        if not text:
            return
        blocks.append(content_block(len(blocks), text, block_type))

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(markdown_break(line).strip() for line in paragraph if line.strip())
            add_block(text)
            paragraph = []

    def flush_quote() -> None:
        nonlocal quote_lines
        if quote_lines:
            text = " ".join(markdown_break(line).strip() for line in quote_lines if line.strip())
            add_block(text)
            quote_lines = []

    for line in source_lines:
        if line.startswith("```"):
            flush_paragraph()
            flush_quote()
            in_code = not in_code
            continue

        if in_code:
            add_block(line, preserve_leading=True)
            continue

        if not line.strip():
            flush_paragraph()
            flush_quote()
            continue

        heading = HEADING_RE.match(line)
        if heading:
            flush_paragraph()
            flush_quote()
            # X's longform editor exposes header-one/header-two, but in practice
            # the "Subheading" UI maps cleanly to header-two. Preserve both
            # Markdown ## and ### headings as X subheadings in saved state.
            block_type = "header-two"
            add_block(heading.group(2).strip(), block_type)
            continue

        item = LIST_RE.match(line)
        if item:
            flush_paragraph()
            flush_quote()
            block_type = "ordered-list-item" if item.group("marker").endswith(".") else "unordered-list-item"
            add_block(item.group("text"), block_type)
            continue

        quote = QUOTE_RE.match(line)
        if quote:
            flush_paragraph()
            quote_lines.append(quote.group(1))
            continue

        flush_quote()
        if CODEISH_RE.match(line):
            flush_paragraph()
            add_block(line, preserve_leading=True)
            continue

        paragraph.append(line)

    flush_paragraph()
    flush_quote()
    return {"blocks": blocks, "entity_map": []}


def render_update_payload(content_state: dict[str, object], article_id: str) -> dict[str, object]:
    return {
        "variables": {
            "content_state": content_state,
            "article_entity": article_id,
        }
    }


def write_outputs(source: Path, out_dir: Path, article_id: str | None = None) -> dict[str, Path]:
    lines = source.read_text().splitlines()
    title, body_lines = split_title(lines)
    tokens = tokenize(body_lines)
    content_state = render_content_state(body_lines)

    stem = source.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "title": out_dir / f"{stem}.x-title.txt",
        "body": out_dir / f"{stem}.x-body.txt",
        "html": out_dir / f"{stem}.x-body-structured.html",
        "content_state": out_dir / f"{stem}.x-content-state.json",
    }
    if article_id:
        paths["update_payload"] = out_dir / f"{stem}.x-update-content-payload.json"

    paths["title"].write_text(title + "\n")
    paths["body"].write_text(render_staging_body(tokens))
    paths["html"].write_text(render_structured_html(body_lines))
    paths["content_state"].write_text(json.dumps(content_state, indent=2, ensure_ascii=False) + "\n")
    if article_id:
        paths["update_payload"].write_text(
            json.dumps(render_update_payload(content_state, article_id), indent=2, ensure_ascii=False) + "\n"
        )
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    parser.add_argument("--article-id", help="Optional X Article entity id for a request-body skeleton.")
    args = parser.parse_args()

    paths = write_outputs(args.source, args.out_dir, args.article_id)
    for label, path in paths.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
