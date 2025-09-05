#!/usr/bin/env python3
"""
busctl - Message bus control utility for AI App Studio

This tool safely handles JSON encoding/decoding to avoid escape issues
that occur with the bash version when handling special characters.

Usage:
    busctl spawn                           # Spawn root unit (auto-detects everything)
    busctl send --to unit:root-api --type instruct --data '{"text": "status"}'
    busctl post --from unit:root --type log --task root --data '{"msg": "Task started"}'
    busctl post --from unit:root --type result --task root --data '{"is_error": false}'
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
import yaml


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


def detect_unit_context():
    """Detect unit context from current directory
    
    UNIT_ID generation rules:
    1. If no .parent_unit file exists -> "root"
    2. If .parent_unit exists -> "{parent_id}-{task_id}"
       where task_id is extracted from directory name or task-breakdown.yml
    """
    cwd = Path.cwd()
    
    # Check for requirements.yml
    if not (cwd / "requirements.yml").exists():
        print("Error: requirements.yml not found in current directory", file=sys.stderr)
        print("Please run this command from a project directory with requirements.yml", file=sys.stderr)
        sys.exit(1)
    
    # Check for parent unit marker
    parent_file = cwd / ".parent_unit"
    if not parent_file.exists():
        # No parent -> this is root
        return "root", None, str(cwd)
    
    # Read parent ID
    parent_id = parent_file.read_text().strip()
    
    # Try to determine task ID from directory name
    # Expected format: {project-name}-{unit-id}
    # e.g., test-project-root-api -> extract "api"
    dir_name = cwd.name
    
    # Try to read parent's task-breakdown.yml if it exists
    task_id_from_breakdown = None
    try:
        # Look for parent's worktree directory
        # Parent worktree pattern: {project}-{parent_id}
        parent_parts = parent_id.split('-')
        
        # Try to find parent worktree directory
        parent_candidates = []
        if cwd.parent:
            # Look for directories that end with parent_id
            for candidate in cwd.parent.iterdir():
                if candidate.is_dir() and candidate.name.endswith(f"-{parent_id}"):
                    parent_candidates.append(candidate)
        
        # Check each candidate for task-breakdown.yml
        for parent_dir in parent_candidates:
            breakdown_file = parent_dir / "task-breakdown.yml"
            if breakdown_file.exists():
                with open(breakdown_file, 'r') as f:
                    breakdown = yaml.safe_load(f)
                    if breakdown and 'tasks' in breakdown:
                        # Extract task IDs from breakdown
                        valid_task_ids = [task['id'] for task in breakdown['tasks'] if 'id' in task]
                        
                        # Check if directory name contains any valid task ID
                        for task_id in valid_task_ids:
                            if task_id in dir_name:
                                task_id_from_breakdown = task_id
                                break
                
                if task_id_from_breakdown:
                    break
    except Exception as e:
        # Silently ignore errors in reading task-breakdown.yml
        pass
    
    # If we found a task ID from breakdown, use it
    if task_id_from_breakdown:
        unit_id = f"{parent_id}-{task_id_from_breakdown}"
        return unit_id, parent_id, str(cwd)
    
    # First, try to extract based on parent ID pattern
    # If parent is "root", look for "root-{task}"
    # If parent is "root-api", look for "root-api-{task}"
    expected_prefix = f"{parent_id}-"
    
    # Check if directory name contains the expected pattern
    if expected_prefix in dir_name:
        # Find the task ID after the parent prefix
        idx = dir_name.rfind(expected_prefix)
        if idx != -1:
            task_suffix = dir_name[idx + len(expected_prefix):]
            if task_suffix:  # Ensure we have a valid suffix
                unit_id = f"{parent_id}-{task_suffix}"
                return unit_id, parent_id, str(cwd)
    
    # Fallback: try to extract the last component after splitting by '-'
    parts = dir_name.split('-')
    if len(parts) > 1:
        # Use the last part as task ID
        task_id = parts[-1]
        unit_id = f"{parent_id}-{task_id}"
        return unit_id, parent_id, str(cwd)
    
    # Last resort: generic child naming
    print(f"Warning: Could not determine task ID from directory name '{dir_name}'", file=sys.stderr)
    print(f"Using generic child ID", file=sys.stderr)
    unit_id = f"{parent_id}-child"
    return unit_id, parent_id, str(cwd)


def handle_spawn(args, root):
    """Handle spawn command"""
    # Check if --from-breakdown option is used
    if hasattr(args, 'from_breakdown') and args.from_breakdown:
        return handle_spawn_from_breakdown(args, root)
    
    # Auto-detect unit context
    unit_id, parent_id, target_repo = detect_unit_context()
    
    # Build environment variables
    env_dict = {
        "UNIT_ID": unit_id,
        "TARGET_REPO": target_repo
    }
    if parent_id:
        env_dict["PARENT_UNIT_ID"] = parent_id
    
    # Add any additional env vars from command line
    if args.env:
        for env_var in args.env:
            if '=' not in env_var:
                print(f"Warning: Invalid environment variable format: {env_var} (expected KEY=VALUE)")
                continue
            key, value = env_var.split('=', 1)
            if not key:
                print(f"Warning: Empty key in environment variable: {env_var}")
                continue
            env_dict[key] = value
    
    # Build message
    message = {
        "id": f"{get_timestamp()}-{get_random_id()}",
        "ts": get_timestamp_ms(),
        "from": "unit" if parent_id else "root",
        "to": "bus",
        "type": "spawn",
        "task_id": unit_id,
        "data": {
            "cwd": "",  # Let busd decide
            "frame": "",  # Empty so busd sends initial message
            "goal": "",  # No goal needed
            "branch": f"feat/{unit_id}",
            "env": env_dict
        }
    }
    
    # Write to mailbox
    dest = Path(root) / "mbox" / "bus" / "in"
    atomic_write_json(dest, message)
    
    print(f"Spawned unit: {unit_id}")
    if parent_id:
        print(f"Parent: {parent_id}")


def handle_spawn_from_breakdown(args, root):
    """Handle spawn --from-breakdown command"""
    # Auto-detect unit context
    unit_id, parent_id, target_repo = detect_unit_context()
    
    # DEBUG: Print context info
    print(f"[DEBUG] handle_spawn_from_breakdown called", file=sys.stderr)
    print(f"[DEBUG] unit_id: {unit_id}", file=sys.stderr)
    print(f"[DEBUG] parent_id: {parent_id}", file=sys.stderr)
    print(f"[DEBUG] target_repo: {target_repo}", file=sys.stderr)
    print(f"[DEBUG] root (mbox location): {root}", file=sys.stderr)
    
    # Check for task-breakdown.yml
    cwd = Path.cwd()
    breakdown_file = cwd / "task-breakdown.yml"
    if not breakdown_file.exists():
        print("Error: task-breakdown.yml not found in current directory", file=sys.stderr)
        print("Please create a task-breakdown.yml file first", file=sys.stderr)
        sys.exit(1)
    
    # Read task-breakdown.yml
    with open(breakdown_file, 'r') as f:
        breakdown = yaml.safe_load(f)
    
    if not breakdown or 'tasks' not in breakdown:
        print("Error: task-breakdown.yml must contain a 'tasks' list", file=sys.stderr)
        sys.exit(1)
    
    # Read existing children if children-status.yml exists
    existing_children = set()
    children_status_file = cwd / "children-status.yml"
    if children_status_file.exists():
        with open(children_status_file, 'r') as f:
            children_status = yaml.safe_load(f)
            if children_status and 'children' in children_status:
                existing_children = {child['unit_id'] for child in children_status['children']}
    
    # Spawn tasks that haven't been spawned yet
    spawned_count = 0
    for task in breakdown['tasks']:
        if 'id' not in task:
            print(f"Warning: Task missing 'id' field, skipping: {task}")
            continue
        
        # Generate child unit ID
        task_id = task['id']
        child_unit_id = f"{unit_id}-{task_id}"
        
        # Skip if already spawned
        if child_unit_id in existing_children:
            print(f"Skipping already spawned unit: {child_unit_id}")
            continue
        
        # Build environment variables for child
        env_dict = {
            "UNIT_ID": child_unit_id,
            "PARENT_UNIT_ID": unit_id,
            "TARGET_REPO": target_repo
        }
        
        # Add any additional env vars from command line
        if args.env:
            for env_var in args.env:
                if '=' not in env_var:
                    continue
                key, value = env_var.split('=', 1)
                if key:
                    env_dict[key] = value
        
        # Build spawn message
        message = {
            "id": f"{get_timestamp()}-{get_random_id()}",
            "ts": get_timestamp_ms(),
            "from": "unit" if unit_id != "root" else "root",
            "to": "bus",
            "type": "spawn",
            "task_id": child_unit_id,
            "data": {
                "cwd": "",  # Let busd decide
                "frame": "",  # Empty so busd sends initial message
                "goal": "",  # No goal needed
                "branch": f"feat/{child_unit_id}",
                "env": env_dict
            }
        }
        
        # Write to mailbox
        dest = Path(root) / "mbox" / "bus" / "in"
        print(f"[DEBUG] Writing spawn message for {child_unit_id} to {dest}", file=sys.stderr)
        print(f"[DEBUG] Message content: {json.dumps(message, indent=2)}", file=sys.stderr)
        final_path = atomic_write_json(dest, message)
        
        # Verify file was written
        if final_path.exists():
            print(f"[DEBUG] Successfully wrote file: {final_path}", file=sys.stderr)
        else:
            print(f"[DEBUG] WARNING: File not found after write: {final_path}", file=sys.stderr)
        
        print(f"Spawned unit: {child_unit_id}")
        spawned_count += 1
    
    if spawned_count == 0:
        print("No new units to spawn (all tasks already have units)")
    else:
        print(f"Spawned {spawned_count} new unit(s)")


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
  # Spawn root unit (from project directory with requirements.yml)
  %(prog)s spawn
  
  # Spawn with additional environment variables
  %(prog)s spawn --env "DEBUG=true" --env "CUSTOM_VAR=value"
  
  # Send instruction to an agent
  %(prog)s send --to impl:T001 --type instruct --data '{"text": "Read task.json"}'
  
  # Post log message from agent
  %(prog)s post --from impl:T001 --type log --task T001 --data '{"msg": "Task started"}'
  
  # Post result from agent
  %(prog)s post --from impl:T001 --type result --task T001 --data '{"is_error": false, "summary": "Done"}'
'''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Spawn command (simplified)
    spawn_parser = subparsers.add_parser('spawn', help='Spawn a new unit (auto-detects context)')
    spawn_parser.add_argument('--env', action='append', help='Additional environment variable in KEY=VALUE format (can be used multiple times)')
    spawn_parser.add_argument('--from-breakdown', action='store_true', help='Spawn all tasks from task-breakdown.yml')
    
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