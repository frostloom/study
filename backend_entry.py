"""Frozen desktop backend entry point. No personal data is included in this module."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    # Frozen PDF worker runs in its own bounded child process, without starting HTTP.
    if len(sys.argv) > 1 and sys.argv[1] == "--extract-pdf":
        import pdf_worker
        if len(sys.argv) != 4:
            raise SystemExit("usage: --extract-pdf INPUT OUTPUT")
        raise SystemExit(pdf_worker.main(*sys.argv[2:4]))
    parser = argparse.ArgumentParser(description="日常学习 local desktop backend")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--channel", choices=['stable','preview'], default='stable')
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--legacy-root", type=Path)
    parser.add_argument("--parent-pid", type=int)
    parser.add_argument("--no-legacy", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    from runtime import start
    from app_info import default_data_root
    start(root=(args.root or default_data_root(args.channel)).expanduser(), port=args.port,
          legacy_root=None if args.no_legacy else args.legacy_root,
          parent_pid=args.parent_pid,channel=args.channel)


if __name__ == "__main__":
    main()
