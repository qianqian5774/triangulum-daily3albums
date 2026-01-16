from __future__ import annotations

import argparse
from pathlib import Path

from daily3albums.config import load_config, load_env


def cmd_doctor(repo_root: Path) -> int:
    env = load_env(repo_root)
    cfg = load_config(repo_root)

    missing = []
    if not env.lastfm_api_key:
        missing.append("LASTFM_API_KEY")
    if not env.mb_user_agent:
        missing.append("MB_USER_AGENT")

    print("DOCTOR")
    print(f"timezone={cfg.timezone}")
    print("config=OK")

    if missing:
        print("env=MISSING " + ", ".join(missing))
        return 2

    print("env=OK")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(prog="daily3albums")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="Check local env/config")

    args = p.parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    if args.cmd == "doctor":
        raise SystemExit(cmd_doctor(repo_root))


if __name__ == "__main__":
    main()
