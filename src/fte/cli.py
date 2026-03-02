"""CLI entry point for the Digital FTE system."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

DEFAULT_VAULT_PATH = "~/AI_Employee_Vault"


def _resolve_vault(raw_path: str) -> Path:
    return Path(raw_path).expanduser().resolve()


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> int:
    """Handle ``fte init``."""
    from fte.vault import init_vault

    vault_path = _resolve_vault(args.path)
    try:
        results = init_vault(vault_path)
    except PermissionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Vault initialized at {vault_path}/")
    for name, status in results:
        mark = "\u2713" if status == "exists" else "+"
        print(f"  {mark} {name}")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """Handle ``fte watch``."""
    from fte.watcher import run_watcher

    vault_path = _resolve_vault(args.path)
    if not vault_path.exists():
        print(f"Error: Vault not found at {vault_path}. Run 'fte init' first.", file=sys.stderr)
        return 1
    run_watcher(vault_path, interval=args.interval)
    return 0


def cmd_linkedin_auth(args: argparse.Namespace) -> int:
    """Handle ``fte linkedin-auth``."""
    from fte.linkedin_auth import main as linkedin_auth_main
    linkedin_auth_main()
    return 0


def cmd_gmail_watcher(args: argparse.Namespace) -> int:
    """Handle ``fte gmail-watcher``."""
    from fte.gmail_watcher import run_gmail_watcher

    vault_path = _resolve_vault(args.path)
    if not vault_path.exists():
        print(f"Error: Vault not found at {vault_path}. Run 'fte init' first.", file=sys.stderr)
        return 1
    run_gmail_watcher(vault_path, interval=args.interval)
    return 0


def cmd_execute(args: argparse.Namespace) -> int:
    """Handle ``fte execute``."""
    from fte.executor import run_executor

    vault_path = _resolve_vault(args.path)
    if not vault_path.exists():
        print(f"Error: Vault not found at {vault_path}. Run 'fte init' first.", file=sys.stderr)
        return 1
    run_executor(vault_path, interval=args.interval, dev_mode=args.dry_run)
    return 0


def cmd_orchestrate(args: argparse.Namespace) -> int:
    """Handle ``fte orchestrate``."""
    from fte.orchestrator import run_orchestrator

    vault_path = _resolve_vault(args.path)
    if not vault_path.exists():
        print(f"Error: Vault not found at {vault_path}. Run 'fte init' first.", file=sys.stderr)
        return 1
    run_orchestrator(vault_path, interval=args.interval, dry_run=args.dry_run)
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fte",
        description="Digital FTE — Personal AI Employee CLI",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # fte init
    p_init = sub.add_parser(
        "init",
        help="Initialize a new Obsidian vault with the required folder structure",
    )
    p_init.add_argument(
        "--path",
        default=DEFAULT_VAULT_PATH,
        help=f"Target directory for the vault (default: {DEFAULT_VAULT_PATH})",
    )

    # fte watch
    p_watch = sub.add_parser(
        "watch",
        help="Start the filesystem watcher (Inbox → Needs_Action)",
    )
    p_watch.add_argument(
        "--path",
        default=DEFAULT_VAULT_PATH,
        help=f"Vault directory (default: {DEFAULT_VAULT_PATH})",
    )
    p_watch.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Polling fallback interval in seconds (default: 5)",
    )

    # fte orchestrate
    p_orch = sub.add_parser(
        "orchestrate",
        help="Start the orchestrator (polls Needs_Action, invokes Claude)",
    )
    p_orch.add_argument(
        "--path",
        default=DEFAULT_VAULT_PATH,
        help=f"Vault directory (default: {DEFAULT_VAULT_PATH})",
    )
    p_orch.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Polling interval in seconds (default: 30)",
    )
    p_orch.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would happen without invoking Claude",
    )

    # fte linkedin-auth
    sub.add_parser(
        "linkedin-auth",
        help="One-time LinkedIn OAuth2 authorization flow",
    )

    # fte gmail-watcher
    p_gw = sub.add_parser(
        "gmail-watcher",
        help="Start the Gmail inbox watcher (polls Gmail API, writes to Inbox/)",
    )
    p_gw.add_argument(
        "--path",
        default=DEFAULT_VAULT_PATH,
        help=f"Vault directory (default: {DEFAULT_VAULT_PATH})",
    )
    p_gw.add_argument(
        "--interval",
        type=int,
        default=120,
        help="Poll interval in seconds (default: 120)",
    )

    # fte execute
    p_exec = sub.add_parser(
        "execute",
        help="Start the action executor (watches Approved/, dispatches actions)",
    )
    p_exec.add_argument(
        "--path",
        default=DEFAULT_VAULT_PATH,
        help=f"Vault directory (default: {DEFAULT_VAULT_PATH})",
    )
    p_exec.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Polling interval in seconds (default: 5)",
    )
    p_exec.add_argument(
        "--dry-run",
        action="store_true",
        help="DEV_MODE: log what would happen without dispatching real actions",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "init": cmd_init,
        "watch": cmd_watch,
        "orchestrate": cmd_orchestrate,
        "execute": cmd_execute,
        "gmail-watcher": cmd_gmail_watcher,
        "linkedin-auth": cmd_linkedin_auth,
    }

    handler = dispatch[args.command]
    sys.exit(handler(args))
