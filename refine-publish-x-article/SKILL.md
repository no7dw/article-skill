---
name: refine-publish-x-article
description: Format draft articles and help publish them as X Articles. Use when the user wants Codex to adapt Markdown/plain text into X Article formatting, replace or update content in x.com/compose/articles/edit, verify publish readiness, or replay the demonstrated article publishing workflow for X.
---

# Format Publish X Article

## Overview

Use this skill to turn a source draft into an X Article with correct formatting and operate the X Article composer with care. The default job is formatting, not rewriting: preserve the author's wording, structure, paragraph order, and level of detail unless the user explicitly asks for editorial refinement. The recorded workflows used local Markdown files in Sublime Text as the source, Brave Browser on `x.com/compose/articles/edit/...` as the destination, and direct editing plus preview checks in the X Article editor for final cleanup.

## Workflow

1. Collect the source draft.
   - Accept pasted text, a local file path, or the currently visible source document.
   - If the source is a file, read it directly from disk.
   - Preserve the author's point of view, examples, wording, and technical claims unless the user explicitly asks for rewriting.

2. Adapt the draft for X formatting only.
   - Preserve the author's expression, clarity level, structure, paragraph order, and length.
   - Do not shorten, rewrite, polish, reorganize, remove repeated ideas, or improve flow unless the user explicitly asks for that.
   - Convert Markdown syntax into text and editor operations that X will accept well.
   - Preserve inline code names, file names, function names, concrete technical terms, examples, claims, and wording.
   - Only change text when required to remove formatting residue, split title/body, make headings render correctly, repair lists, or prevent broken paste behavior.

3. Prepare for X Article formatting.
   - Preserve paragraph breaks unless X paste behavior creates accidental extra blank lines or broken list spacing.
   - Preserve heading text; only change heading markers or editor style so headings render correctly in X.
   - Preserve existing lists; only change their markup or editor formatting so they render as X-native lists.
   - Avoid fragile formatting that may not paste cleanly into X.
   - Preserve existing blockquotes; only change quote markers or editor formatting so they render correctly in X.
   - Split title and body before paste. Put the title in X's title field, and remove a leading Markdown `# Title` from the body.
   - Convert Markdown headings through X's formatting controls: turn `#` sections into headline style and `##` sections into subheadline style. Do not leave literal `#` or `##` markers in the published body.
   - Prepare list blocks for X as compact contiguous lines: a lead-in line, then list item lines with no blank lines between items. Do not insert blank paragraphs before every bullet.
   - Before applying X's list controls, remove Markdown list markers from list item text. For unordered lists, change `- user preferences` into `user preferences`; for ordered lists, change `1. first step` into `first step` unless the user explicitly wants literal numbering preserved. Then select the contiguous item lines and click X's itemized-list or numbered-list toolbar button. A correct X list has real bullet/number glyphs from the editor and no leftover leading `- ` / `1. ` text.
   - Prefer X-native itemized lists over plain hyphen paragraphs. After paste, select each contiguous list run and click the X editor list button so the items become page-native list items. Use the numbered-list button for ordered steps. Do not call a list done if it shows both an X bullet and a literal Markdown hyphen.
   - Collapse excessive empty lines before paste and after paste. Convert runs of two or more blank lines between paragraphs/list items into the smallest spacing that still reads as one visual paragraph break. Lists must be contiguous item lines with no blank paragraph between items; blank lines inside a list are a formatting bug.

4. Open or use the X Article composer.
   - Use the browser or Computer Use when the user wants live publishing help.
   - Target `x.com/compose/articles/edit/...` or the active X Article composer tab.
   - Identify the main article body as the large text area in the X article editor.
   - If replacing article content, click the article body, verify the caret/focus is inside body content rather than the title field, then select all, delete existing content, and paste the formatted draft. After paste, immediately check the draft card/title preview; if the title now contains pasted body text, undo or repair the title before doing anything else.
   - If updating only a section, select the relevant visible text and replace only that section.
   - If the draft came from a visible editor, copy all source text from the editor, switch to the X composer, then replace the destination content. Use stable targets such as the title field, Body editor, Preview link, Publish button, and Focus mode link.

5. Verify before publishing.
   - Confirm the title, body, paragraph breaks, headings, and list formatting survived paste.
   - Check that the Publish button is enabled only after required fields/content are present.
   - Scan the top and bottom of the article for accidental duplicated text, missing first paragraph, or truncated ending.
   - Remove visible Markdown residue such as leading `#`, `##`, `-`, broken blockquote markers, or duplicated title text in the body.
   - Inspect every list that was pasted from Markdown. If each item appears as a standalone paragraph beginning with `-`, the list is not done: first remove the literal `- ` markers, then select the run and apply the X editor itemized-list button. If list items are separated by large blank gaps, collapse the gaps and apply list formatting again.
   - Treat list formatting as a publish-readiness gate. Do not call the article ready while subitems still look like manually typed hyphen paragraphs, or while X-native bullets contain leftover literal hyphens, especially after "It:", "such as:", "that means:", "That includes things like:", or similar lead-in lines.
   - Treat excessive vertical whitespace as a publish-readiness gate. Scan around every heading, lead-in sentence, list block, and paragraph transition for double blank paragraphs or giant gaps; collapse them before preview or publication.
   - Check headings after cleanup. Convert Markdown `#` or `##` text into headline or subheadline styling through the editor menu, then verify the heading hierarchy in preview.
   - Scan for too many empty lines between paragraphs, headings, and lists in the editor and in Preview. If the preview shows oversized gaps around list items, return to edit mode, collapse the gaps, and reapply the list button.
   - Open Preview before final approval when the user wants publishing help. Use the preview to confirm top-of-article title, body start, headings, X-native bullets or numbering, compact list spacing, and end-of-article content. If the Preview toolbar button is unreliable but the edit URL is known, navigate directly from `/compose/articles/edit/<id>` to `/compose/articles/edit/<id>/preview` and verify the preview there.
   - Do not click Publish unless the user explicitly asks to publish or confirms the final preview.

6. Publish or hand back.
   - If the user wants final approval, provide the formatted article text and a concise checklist of what to inspect in X.
   - If the user explicitly says to publish and the UI is ready, click Publish and report the outcome.
   - If publishing fails or the button stays disabled, report the visible blocker and the exact state of the composer.

## Formatting Defaults

- Treat the source draft as authoritative.
- Make the smallest text changes needed for X Article formatting.
- Do not edit tone, clarity, structure, length, or repetition by default.
- Do not invent sources, citations, metrics, or code references.
- For technical articles, keep concrete implementation names intact.

## Recorded Interaction Notes

- Source draft selection can happen in a local editor such as Sublime Text.
- The demonstrated X destination was Brave Browser with an article edit URL.
- Stable UI targets are the X Article title field, Body editor, Preview link, Focus mode link, and Publish button, not screen coordinates.
- The recorded replacement flow was: select all in the local Markdown source, copy, switch to Brave/X Article editor, select all in the body, delete, paste, then remove the duplicated Markdown title from the body.
- The recorded cleanup included removing excessive empty lines, converting `#`/`##` Markdown markers into headline/subheadline styling, selecting broken Markdown list runs, using the editor menu to make proper list items, and checking the preview route at `/preview`.
- A later correction showed that pasting list items with blank lines between every `-` item creates huge vertical gaps in X. Keep list lines contiguous in the paste text, then select the whole run and use X's itemized-list toolbar button. Verify this both in edit mode and Preview.
- A later run showed that rich paste can accidentally target the title field if the caret is not in the body. When using rich clipboard formats or replacing a whole draft, confirm body focus first and verify the title/draft card immediately after paste.
- The same run confirmed that direct preview navigation to `/compose/articles/edit/<id>/preview` is a reliable fallback when the Preview button cannot be activated through browser automation.
- Treat auto-save and the word count as useful state signals; report if Publish is disabled after edits or if the draft is still saving.

