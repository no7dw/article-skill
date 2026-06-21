---
name: x-article-draft-paster
description: Prepare Markdown or plain-text articles for X Articles and paste them into an empty X Article draft. Use when the user wants one workflow that accepts a filepath or content, splits title/body, converts Markdown to rich X-friendly HTML, copies the rich body to the clipboard, fills an empty X Article editor title/content, handles cover/content image metadata, and verifies formatting without publishing.
---

# X Article Draft Paster

## Purpose

Use this skill to take a local article file or supplied content and place it into an empty X Article draft with the title and body in the correct fields. The default job is formatting and transfer, not rewriting. Preserve the author's wording unless the user explicitly asks for editorial changes.

This skill merges two reliable patterns:

- `x-article-publisher`: rich HTML clipboard paste, cover/content image metadata, image upload later, dividers via X's Insert menu.
- `refine-publish-x-article`: conservative Markdown cleanup, title/body separation, compact list handling, X content-state generation, preview-first verification.

Never click Publish unless the user explicitly asks and confirms the preview.

## Quick Start

Prepare files from a Markdown file:

```bash
python ~/.codex/skills/x-article-draft-paster/scripts/prepare_x_article.py \
  --file /absolute/path/article.md \
  --copy-html
```

Prepare from already-saved content:

```bash
python ~/.codex/skills/x-article-draft-paster/scripts/prepare_x_article.py \
  --content-file /absolute/path/content.txt \
  --out-dir /tmp/x-article \
  --copy-html
```

The script prints a JSON summary and writes:

- `<stem>.x-title.txt`
- `<stem>.x-body.txt`
- `<stem>.x-body-structured.html`
- `<stem>.x-rich-clean.html`
- `<stem>.x-content-state.json`
- `<stem>.x-update-content-payload.json`
- `<stem>.x-publisher-metadata.json`
- `<stem>.x-source.md`
- `<stem>.x-text-source.md`

Use `<stem>.x-body-structured.html` as the main rich paste source.

## Workflow

1. **Collect source**
   - Accept a local file path, pasted content saved to a temp file, or visible current draft content.
   - If content does not have a title field, use the first Markdown `# Heading` as the X title. If no `#` exists, infer a short title from the first non-empty line.

2. **Prepare rich body**
   - Run `scripts/prepare_x_article.py`.
   - Let it reflow ordinary hard-wrapped prose, preserve headings, convert lists to real `<ul>` / `<ol>` HTML, preserve inline bold/code/links, and convert simple Markdown tables to compact bullets by default.
   - Keep images out of the initial body paste. The text comes first; images are uploaded later using metadata positions.

3. **Open an empty X Article draft**
   - Navigate to `https://x.com/compose/articles`.
   - If a draft list appears, click Create/New Article before looking for title/body fields.
   - If the user already has an empty draft open, use that tab.
   - Do not use the workflow to overwrite non-empty drafts unless the user explicitly asks.

4. **Fill title**
   - Read `<stem>.x-title.txt`.
   - Click the title field (`Add a title` / localized equivalent).
   - Select existing title text only if replacing is explicitly intended.
   - Type or paste the title.

5. **Fill body**
   - Copy the generated rich HTML to the clipboard with either `--copy-html` or:
     ```bash
     python ~/.codex/skills/x-article-draft-paster/scripts/copy_to_clipboard.py \
       html --file /path/to/<stem>.x-body-structured.html
     ```
   - If `--copy-html` reports a missing `AppKit` / `pyobjc-framework-Cocoa` dependency on macOS, open `<stem>.x-body-structured.html` in a browser, select the rendered article content, copy it, and then paste into X. Browser selection copy also places rich HTML on the clipboard, which is why the rendered HTML page is directly useful.
   - Click the body editor (`Start writing` / localized equivalent).
   - Confirm the caret is in the body, not the title.
   - Paste with Cmd+V.
   - Immediately check that the draft card/title did not receive the whole body. If body text landed in the title, undo and retry after focusing the body.

6. **Insert media and dividers after text**
   - Read `<stem>.x-publisher-metadata.json`.
   - Upload `cover_image` first when present and `cover_exists` is true.
   - Insert `content_images` after the recorded `block_index` positions. Use `after_text` only as a human clue, not as the primary coordinate.
   - Insert dividers via X's Insert > Divider UI. Raw `<hr>` is ignored by X.

7. **Verify before handoff**
   - Confirm title, first paragraph, headings, compact lists, links, bold/code text, and final paragraph.
   - Confirm no literal Markdown artifacts remain in the editor: `#`, `##`, leading `-`, `1.`, image Markdown, code fences, or pipe tables.
   - Open Preview when possible. If a preview button is unreliable and an edit URL is known, try the `/preview` route.
   - Report whether Publish is enabled, but do not publish without explicit confirmation.

## Important Rules

- Use rich HTML paste for the body because X reads clipboard HTML and converts it into native editor blocks.
- Use simple HTML only: `<p>`, `<h2>`, `<ul>`, `<ol>`, `<li>`, `<blockquote>`, `<strong>`, `<code>`, and `<a>`.
- Keep title and body separate. A duplicated title at the top of the body is a bug.
- Keep list items contiguous. Blank lines inside a list often create large X spacing gaps.
- Prefer text first, images second, dividers last.
- Treat image URLs as metadata problems: resolve local files by basename when possible. If an image is missing, report it rather than pretending it uploaded.
- Treat empty-draft fill as the default. Replacement of existing drafts requires explicit user intent.

## Script Notes

- `prepare_x_article.py` is the preferred entrypoint.
- `format_x_article.py` is bundled from `refine-publish-x-article` for content-state and staging text generation.
- `parse_markdown.py`, `copy_to_clipboard.py`, and `table_to_image.py` are bundled from `x-article-publisher`.
- `copy_to_clipboard.py` requires `pyobjc-framework-Cocoa` on macOS for script-driven rich HTML clipboard support. Without it, use browser-rendered HTML selection/copy as the fallback.
