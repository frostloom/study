# Deleted-source cleanup and flexible daily tasks

Keep existing categories, themes, original full modules and study facts. No automatic backups or copies. Formal and preview data remain isolated.

1. RED tests for whole-source unindexed attachments, shared source folders and imported per-document metadata. Add managed cleanup helper invoked after deletion and at startup for past tombstones; never follow symlinks or touch an active source. One-time remove verified legacy duplicate materials after byte verification.
2. RED tests for manual create/add/remove/update task and per-day budgets. Add Store.edit_day + POST /api/plan/edit serialized by Learning.lock. Keep removed task snapshots/checks for truthful history. Added tasks may increase today's budget within 480min. Explicit minute/scope edits persist. Global profile unchanged. Completed scope edits require unchecking first. Removed pending tasks excluded from next3 planned days; manual re-add possible.
3. Review reconciliation: prune only unanswered questions no longer in completed scope; keep answered/graded history. New completed items available to supplement. Automatic next-day planning gets revised handoff and no removed carryover.
4. Add task picker respecting category -> source -> chapter, search; minute/scope fields, accessible dialogs, cancel/errors/busy. Adjust dialog supports per-task removal and current-day time. No arbitrary free-text tasks requested.
5. Run full Python and frontend suite, isolated browser exercises, independent review; fix findings. Release1.4.0 for Mac arm/x64 Windows; install both local apps without backups and check original book/progress intact. Remove known temporary build/test directories.
