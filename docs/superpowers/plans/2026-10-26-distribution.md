# Cross-platform distribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task.

**Goal:** Publish GitHub Mac/Windows releases, isolate stable and preview, migrate web settings, automatically notify users of new stable releases.
**Architecture:** Frozen Python + HTML/JS UI, Swift/AppKit and C++/Win32/WebView2 shells. GitHub tag builds publish only after platform smoke tests pass.
**Tech Stack:** Python3.12, PyInstaller, Swift, C++/WebView2, JS/CSS, GitHubActions.
**Spec:** ../specs/2026-10-26-cross-platform-release-design.md

## Global Constraints
Preserve study facts and originals; never commit secrets or user materials. Separate app/data/browser identities for stable/preview. Mac arm64/x64 and Windows10/11x64. Check updates automatically at startup/every6h; update button only appears when newer stable version available. User authorizes publish. No silent installer execution. Signing credentials unavailable.

## Review Focus
Windows portability: fcntl/parentPID/ZoneInfo/PDF/encoding. Offline/malformed release data must not break learning. Preview must never migrate stable/timers. Migration must preserve newer records. Public artifacts must exclude all personal data.

### Task1 runtime isolation
Files: app_info.py,runtime_lock.py,runtime.py,backend_entry.py,native/main.swift,tools/preview.py,tests/test_distribution_runtime.py.
Interfaces: VERSION,default_data_root(channel,platform,home),FileLock(path),parent_alive(pid),--channel stable|preview.
- [ ] RED: separate roots, real process exclusive lock/release; implement portable runtime+channels; full suite GREEN.

### Task2 automatic update notices
Files: updates.py,server.py,static/updates.js,static/updates.css,static/index.html,tests/test_updates.py,docs/frontend-update-test.cjs.
Interfaces: GET/api/app,GET/api/updates,POST/api/updates/check,UpdateChecker.check(force=False); trusted DailyStudy-VERSION-PLATFORM-ARCH assets.
- [ ] RED: numeric semver, draft/prerelease skipping, URL/asset platform validation, offline; implement bounded cached latest-release fetch and auto UI startup/every6h; full suite+browser GREEN.

### Task3 platform packages/CI
Files: native/windows/main.cpp,CMakeLists.txt,tools/build_windows.ps1,tools/windows-smoke.ps1,tools/build_macos.sh,.github/workflows/release.yml,requirements-build.txt,README.md.
- [ ] Windows owned backend/native window/picker/navigation/runtime error; ZIP+installer; Mac x64/arm64 and preview separate identity.
- [ ] Tag jobs actual frozen/runtime+native smoke; publish all-green assets+SHA256. Local Mac build and GitHub runner checks.

### Task4 local migration/delivery
Files: tools/migrate_desktop.py,tools/import_browser_state.py,tests/test_desktop_migration.py,docs/usage.md.
- [ ] RED protecting newer desktop records/API+schedule migration; backup, merge/transfer allowlisted browser drafts/theme; GREEN.
- [ ] Check idle, stop exact web backend; backup old launch script and open desktop. Install stable; launch preview isolated; verify original files.

### Task5 review/publish
- [ ] Fresh independent review; fix important issues; full tests and staged-data audit.
- [ ] Push source/tag, wait actual Mac/Windows CI and resolve failures; GitHub release assets visible.
- [ ] Persistent development checkout follows published source, installed stable separate. Report tested scope and signing limits.
