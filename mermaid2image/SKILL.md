---
name: mermaid2image
description: Render Mermaid diagrams in Markdown or .mmd files into PNG images, replace Mermaid code blocks with image links, and optionally upload generated images to ImageKit. Use when Codex needs to convert ```mermaid blocks to local image files, CDN URLs, blog-ready Markdown image links, or ImageKit-hosted diagrams.
---

# Mermaid to Image

Use this skill when a Markdown article contains Mermaid diagrams that should be shown as image links instead of inline Mermaid code blocks.

## Workflow

1. Keep the source Markdown unchanged until rendering succeeds.
2. Run `scripts/mermaid2image.py` against the Markdown file.
3. Inspect generated PNGs when layout quality matters.
4. Replace Mermaid blocks with image links only after rendering succeeds.
5. If ImageKit credentials are available, upload images and use CDN URLs.

## Script

Run from any directory:

```bash
python ~/.codex/skills/mermaid2image/scripts/mermaid2image.py ARTICLE.md
```

Default behavior:

- Extracts every fenced `mermaid` block from `ARTICLE.md`.
- Writes `.mmd` sources and `.png` images into `ARTICLE_DIR/images/`.
- Replaces Mermaid blocks with relative Markdown image links.
- Uses deterministic names like `01-diagram.png`, unless headings can provide better labels.

Use ImageKit:

```bash
export IMAGEKIT_PRIVATE_KEY
python ~/.codex/skills/mermaid2image/scripts/mermaid2image.py ARTICLE.md \
  --imagekit-folder /blog/my-article \
  --imagekit-url-endpoint https://ik.imagekit.io/7zrdm7joj
```

Set `IMAGEKIT_PRIVATE_KEY` from your shell, password manager, or CI secret store before running the command. The ImageKit public key is not required for server-side upload. Prefer passing the private key via `IMAGEKIT_PRIVATE_KEY`; do not echo it in logs or write it into article diagrams.

Useful options:

```bash
--output-dir DIR              Write generated files somewhere else
--image-prefix NAME           Use NAME-01.png instead of 01-diagram.png
--imagekit-folder /path       Upload images to this ImageKit folder
--imagekit-url-endpoint URL   Public ImageKit endpoint for final links
--no-replace                  Render/upload only; do not edit Markdown
--keep-local-links            Upload but keep Markdown as local image links
--width 1600                  Mermaid viewport width
--scale 2                     Mermaid render scale
```

## Rendering Notes

- The script uses `npx --yes @mermaid-js/mermaid-cli@latest`, so Node/npm must be available.
- If a diagram renders too wide or too tall, edit the Mermaid graph layout first, then rerun the script.
- For blog articles, prefer PNG links over raw Mermaid blocks because many publishing platforms do not render Mermaid.
- Keep generated `.mmd` files beside PNGs so diagrams can be edited later.

## Validation

After conversion, check:

```bash
rg -n '^```mermaid|!\[' ARTICLE.md
file ARTICLE_DIR/images/*.png
```

If ImageKit was used, verify URLs with `HEAD` requests or browser access before finalizing.
