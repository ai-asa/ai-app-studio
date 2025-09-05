#!/usr/bin/env python3
"""
busctl - Message bus control utility for AI App Studio

This tool safely handles JSON encoding/decoding to avoid escape issues
that occur with the bash version when handling special characters.

Usage:
    busctl spawn --task T001 --cwd work/T001 --frame frames/impl/CLAUDE.md --goal "Create hello.txt"
    busctl send --to impl:T001 --type instruct --data '{"text": "Read task.json"}'
    busctl post --from impl:T001 --type log --task T001 --data '{"msg": "Task started"}'
    busctl post --from impl:T001 --type result --task T001 --data '{"is_error": false, "summary": "Done"}'
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
import random
import string


# Constants
DEFAULT_FROM = "pmai"
DEFAULT_TO_PMAI = "pmai"
DEFAULT_TO_BUS = "bus"
TIMESTAMP_FORMAT = "%Y%m%dT%H%M%S.%f"
RANDOM_ID_LENGTH = 12


def get_timestamp():
    """Generate timestamp in format: YYYYMMDDTHHMMSS.sssZ"""
    # Use timezone-aware UTC datetime to avoid deprecation warning
    from datetime import timezone
    return datetime.now(timezone.utc).strftime(TIMESTAMP_FORMAT)[:-3] + "Z"


def get_random_id():
    """Generate random hex string for unique IDs"""
    return ''.join(random.choices(string.hexdigits.lower(), k=RANDOM_ID_LENGTH))


def get_timestamp_ms():
    """Get current timestamp in milliseconds since epoch"""
    # Use timezone-aware UTC datetime to avoid deprecation warning
    from datetime import timezone
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def atomic_write_json(dest_dir, message):
    """Write JSON message atomically to destination directory"""
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)
    
    # Create temporary file
    ts = get_timestamp()
    rand = get_random_id()
    tmp_name = f".tmp-{ts}-{rand}.json"
    final_name = f"{ts}-{rand}.json"
    
    tmp_path = dest_path / tmp_name
    final_path = dest_path / final_name
    
    # Write to temp file
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(message, f, ensure_ascii=False, indent=2)
        f.write('\n')
    
    # Atomic rename
    tmp_path.rename(final_path)
    
    return final_path


def handle_spawn(args, root):
    """Handle spawn command"""
    # Build message
    message = {
        "id": f"{get_timestamp()}-{get_random_id()}",
        "ts": get_timestamp_ms(),
        "from": "pmai",
        "to": "bus",
        "type": "spawn",
        "task_id": args.task,
        "data": {
            "cwd": args.cwd or "",
            "frame": args.frame or "",
            "goal": args.goal or "",
            "branch": args.branch or f"feat/{args.task}"
        }
    }
    
    # Write to mailbox
    dest = Path(root) / "mbox" / "bus" / "in"
    atomic_write_json(dest, message)


def handle_send(args, root):
    """Handle send command"""
    # Parse JSON data
    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in --data: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Extract task_id from destination
    task_id = args.to.split(':', 1)[1] if ':' in args.to else args.to
    
    # Build message
    message = {
        "id": f"{get_timestamp()}-{get_random_id()}",
        "ts": get_timestamp_ms(),
        "from": "pmai",
        "to": args.to,
        "type": args.type,
        "task_id": task_id,
        "data": data
    }
    
    # Determine destination mailbox
    agent_name = args.to.replace(':', '-')
    dest = Path(root) / "mbox" / agent_name / "in"
    
    # Write to mailbox
    atomic_write_json(dest, message)


def handle_post(args, root):
    """Handle post command"""
    # Parse JSON data
    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in --data: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validate result type requires is_error field
    if args.type == "result" and "is_error" not in data:
        print("Error: 'result' type requires 'is_error' field in data", file=sys.stderr)
        sys.exit(1)
    
    # Build message
    message = {
        "id": f"{get_timestamp()}-{get_random_id()}",
        "ts": get_timestamp_ms(),
        "from": args.from_,
        "to": "pmai",
        "type": args.type,
        "task_id": args.task,
        "data": data
    }
    
    # Write to mailbox
    dest = Path(root) / "mbox" / "pmai" / "in"
    atomic_write_json(dest, message)


def create_parser():
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        description='Message bus control utility for AI App Studio',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Spawn a new agent task
  %(prog)s spawn --task T001 --cwd work/T001 --frame frames/impl/CLAUDE.md --goal "Create hello.txt"
  
  # Send instruction to an agent
  %(prog)s send --to impl:T001 --type instruct --data '{"text": "Read task.json"}'
  
  # Post log message from agent
  %(prog)s post --from impl:T001 --type log --task T001 --data '{"msg": "Task started"}'
  
  # Post result from agent
  %(prog)s post --from impl:T001 --type result --task T001 --data '{"is_error": false, "summary": "Done"}'
'''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Spawn command
    spawn_parser = subparsers.add_parser('spawn', help='Spawn a new agent')
    spawn_parser.add_argument('--task', required=True, help='Task ID')
    spawn_parser.add_argument('--cwd', help='Working directory for the task')
    spawn_parser.add_argument('--frame', help='Frame file path')
    spawn_parser.add_argument('--goal', help='Task goal description')
    spawn_parser.add_argument('--branch', help='Git branch name (default: feat/<task>)')
    
    # Send command
    send_parser = subparsers.add_parser('send', help='Send message to agent')
    send_parser.add_argument('--to', required=True, help='Destination agent (e.g., impl:T001)')
    send_parser.add_argument('--type', required=True, help='Message type (e.g., instruct)')
    send_parser.add_argument('--data', required=True, help='JSON data')
    
    # Post command
    post_parser = subparsers.add_parser('post', help='Post message from agent')
    post_parser.add_argument('--from', dest='from_', required=True, help='Source agent (e.g., impl:T001)')
    post_parser.add_argument('--type', required=True, help='Message type (log, result, error)')
    post_parser.add_argument('--task', required=True, help='Task ID')
    post_parser.add_argument('--data', required=True, help='JSON data (for result type, must include is_error)')
    
    return parser


def main():
    """Main entry point"""
    # Check for BUSCTL_ROOT environment variable, otherwise use current directory/.ai-app-studio
    if 'BUSCTL_ROOT' in os.environ:
        root = os.environ['BUSCTL_ROOT']
    else:
        root = os.path.join(os.getcwd(), ".ai-app-studio")
    
    # Create and configure parser
    parser = create_parser()
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Handle commands
    try:
        if args.command == 'spawn':
            handle_spawn(args, root)
        elif args.command == 'send':
            handle_send(args, root)
        elif args.command == 'post':
            handle_post(args, root)
    except Exception as e:
        import traceback
        print(f"Error: {e}", file=sys.stderr)
        print("Traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()