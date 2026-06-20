---
name: excalidraw-diagram-workflow
description: Iterative Excalidraw diagram design workflow. Build diagram JSON, upload it, verify with screenshots, and iterate using repo-local helper scripts.
---

# Excalidraw Diagram Design Workflow

Design, verify, and iterate on Excalidraw diagrams using a tight feedback loop with real browser screenshots.

This skill is written to be portable across Codex, Hermes, or any similar agent runner. Use the helper scripts bundled in this skill instead of referencing user-specific paths.

## Environment
- macOS with Chrome (for CDP screenshot)
- PinchTab Chrome extension (optional but preferred — no separate Chrome launch needed)
- Excalidraw web editor
- Python 3
- Optional: any agent or CLI that can inspect an image and comment on layout quality

## Skill-Local Setup

Run commands from the `excalidraw-diagram-workflow` directory, or set `SKILL_DIR` to that directory explicitly.

```bash
cd /path/to/excalidraw-diagram-workflow
mkdir -p tmp
python -m pip install cryptography websocket-client
```

Helper scripts shipped with this skill:

- `scripts/upload.py`
- `scripts/chrome_screenshot.py`

## Prerequisites (CHECK FIRST — before anything else)

Before attempting any screenshot, verify PinchTab is running:

```bash
# Health check — if this fails, PinchTab is not installed/running
curl -s --max-time 3 http://localhost:9867/health && echo "PinchTab: OK" || echo "PinchTab: NOT AVAILABLE"
```

**If PinchTab is NOT available**: use the bundled Chrome CDP fallback in Step 4 if your environment can launch a separate headless Chrome instance. If that is not possible, skip screenshot verification, deliver the Excalidraw URL directly to the user, and note "screenshot verification skipped — no PinchTab and no CDP Chrome available."

**If PinchTab IS available**: proceed with Steps 3-6 below.

---

### 1. Chrome with CDP debug port

**Option A — PinchTab (recommended, uses your real Chrome with extension):**
```bash
# Install extension from clawhub.ai, then run:
pinchtab &
# Default: http://localhost:9867
```

**Option B — Standalone Chrome instance:**
```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-screenshot &
```

### 2. Screenshot script

```bash
# Run from the skill directory
python scripts/chrome_screenshot.py <url> <output_path> [port]
```

---

## Workflow (6-Step Loop)

### Step 1 — Design the layout (BEFORE writing JSON)

**Read the Layout Rules in the `excalidraw` skill first.** Most bad diagrams fail before a single element is written, because the layout wasn't planned.

Rules to follow:
1. **Use a grid** — X positions at 0, 240, 480, 720; Y at 0, 120, 240, 360
2. **Consistent box sizing** — all boxes in same row = same `width` and `height`
3. **Meaningful colors** — pick Role A (flow) OR Role B (layers) OR Role C (comparison), never mix
4. **No crossing lines** — arrows flow one direction, stacked vertically with gaps
5. **Meaningful arrangement** — left→right for flow, background zones drawn first

### Step 2 — Build in Excalidraw JSON

1. Write elements following the Layout Rules above
2. Save as a local `.excalidraw` file
3. Upload for shareable link:

```bash
python scripts/upload.py ./tmp/my_diagram.excalidraw
```

### Step 3 — Screenshot via PinchTab (preferred)

```bash
# Navigate to the Excalidraw URL
curl -X POST http://localhost:9867/navigate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://excalidraw.com/#json=<FILE_ID>,<KEY>"}'

sleep 3

# Screenshot
curl -X POST http://localhost:9867/screenshot \
  -H "Content-Type: application/json" \
  -d '{"format": "jpeg", "quality": 85}' \
  --output ./tmp/diagram.jpg
```

### Step 4 — Screenshot via Chrome CDP (fallback)

```bash
python scripts/chrome_screenshot.py \
  "https://excalidraw.com/#json=<FILE_ID>,<KEY>" \
  ./tmp/diagram.png
```

### Step 5 — Analyze the screenshot

Attach the screenshot to the current conversation or inspect it with the image-capable tool available in your environment. Describe:
- Box sizes consistent? Any overflow or cramped text?
- Colors meaningful? Do they map to a concept?
- Lines crossing? Arrangement logical?
- Core content clearly visible?

### Step 6 — Iterate

Fix identified problems in the JSON, re-upload, re-screenshot. Repeat until satisfied.

---

## Scoring Guide

```bash
# Optional example if your local toolchain supports image scoring
<your-image-review-command> ./tmp/diagram.png
```

| Score | Meaning |
|-------|---------|
| 8-10/10 | Excellent — publish-ready |
| 6-7/10 | Good — minor polish needed |
| 4-5/10 | Needs significant work |
| 1-3/10 | Major structural problems — restart layout |

---

## Format Tips

- **Twitter/LinkedIn**: Vertical 4:5 format, bold headline 20px+, body 14-16px
- **PNG export 2x from Excalidraw** (not screenshot) for final output — removes UI chrome
- Consistent stroke widths 3-5px across all shapes
- Do NOT use emoji in text — they don't render in Excalidraw's font
- Light fills on dark backgrounds: use `#e5e5e5` text, not `#1e1e1e`

## Portability Notes

- Do not reference `~/.hermes/...`, `~/work/...`, or other user-specific absolute paths in commands or examples.
- Prefer skill-local relative paths such as `scripts/upload.py` and `./tmp/diagram.png`.
- If your host environment installs the skill elsewhere, only the initial `cd /path/to/excalidraw-diagram-workflow` changes; the rest of the workflow stays the same.

---

## Common Layout Problems & Fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| Boxes overlap | y-coordinates too close | Space elements 25px+ apart vertically |
| Text overflow | Box too narrow | Increase `width` or reduce `fontSize` |
| Crossing arrows | No planned route | Use L-shape `points: [[0,0],[dx,0],[dx,dy]]` |
| Inconsistent sizes | Ad-hoc placement | Use the standard size table from `excalidraw` skill |
| Colors random | No color role chosen | Pick Role A/B/C, apply consistently |
| Zone not visible | Drawn after nodes | Background zones MUST be first in elements array |
