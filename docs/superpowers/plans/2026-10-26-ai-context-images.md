# AI composer and source-image context

- Enter sends; Shift+Enter inserts newline; IME composition never submits. Cmd/Ctrl+Shift+Backspace clears only the question and its draft, preserving selected source and chat history. Visible clear button and shortcut help.
- Preserve current section (8000 chars) plus up to30 QA/40000 chars. Prepare context through a local API using server-resolved section, not the whole article. Report section/text/image/history counts per sent turn.
- Resolve only current section image references, bounded to4 images; support embedded SVG/PNG and managed local/public images. SVG rendered to PNG through the reader's browser canvas, never sent as unsupported SVG to the model. Limit sizes and validate image signatures at the backend.
- Send OpenAI-compatible multimodal content blocks. Never silently drop a failed image or silently retry as text; explicit text-only checkbox is available. Unsupported vision returns actionable error and keeps draft.
- Preserve session isolation, pending-request ownership, user typing during response, source retention, independent formal/preview data. No backups.
- Configure this repo only to frostloom/278895495+frostloom@users.noreply.github.com. Correct previously misattributed author/committer metadata with exact remote-ref leases; leave source trees and published assets unchanged.
- RED/GREEN unit and frontend behavior tests; isolated actual-model test with public book diagram; native UI verification; release and update both apps, preserving study facts.
