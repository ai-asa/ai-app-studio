#!/usr/bin/env python3
"""
TDD Example: Message validation tests
Following the Red-Green-Refactor cycle as required by CLAUDE.md
"""

import json
import unittest
import sys
from pathlib import Path

# Add the bin directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "bin"))


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


# This will fail initially (RED phase)
try:
    from message_validator import validate_message, ValidationError
except ImportError:
    # Expected to fail in RED phase - define dummy for tests to run
    def validate_message(msg):
        raise NotImplementedError("validate_message not implemented yet")


class TestMessageValidation(unittest.TestCase):
    """Test cases for message validation following TDD approach"""

    def test_valid_spawn_message(self):
        """Test that a valid spawn message passes validation"""
        msg = {
            "id": "20231101T123456.789Z-abc123",
            "ts": 1698842096789,
            "from": "pmai",
            "to": "bus",
            "type": "spawn",
            "task_id": "T001",
            "data": {
                "cwd": "work/T001",
                "frame": "frames/impl/CLAUDE.md",
                "goal": "Create hello.txt",
                "branch": "feat/T001"
            }
        }
        
        # This should pass validation
        self.assertTrue(validate_message(msg))

    def test_missing_required_field(self):
        """Test that missing required fields raise ValidationError"""
        msg = {
            "id": "20231101T123456.789Z-abc123",
            "ts": 1698842096789,
            "from": "pmai",
            "to": "bus",
            # Missing 'type' field
            "task_id": "T001",
            "data": {}
        }
        
        with self.assertRaises(ValidationError) as cm:
            validate_message(msg)
        self.assertIn("Missing required field: type", str(cm.exception))

    def test_invalid_message_type(self):
        """Test that invalid message types are rejected"""
        msg = {
            "id": "20231101T123456.789Z-abc123",
            "ts": 1698842096789,
            "from": "pmai",
            "to": "bus",
            "type": "invalid_type",  # Invalid type
            "task_id": "T001",
            "data": {}
        }
        
        with self.assertRaises(ValidationError) as cm:
            validate_message(msg)
        self.assertIn("Invalid message type", str(cm.exception))

    def test_result_message_requires_is_error(self):
        """Test that result messages must have is_error in data"""
        msg = {
            "id": "20231101T123456.789Z-abc123",
            "ts": 1698842096789,
            "from": "impl:T001",
            "to": "pmai",
            "type": "result",
            "task_id": "T001",
            "data": {
                "summary": "Task completed"
                # Missing is_error field
            }
        }
        
        with self.assertRaises(ValidationError) as cm:
            validate_message(msg)
        self.assertIn("Result messages must include is_error", str(cm.exception))

    def test_spawn_message_requires_task_id(self):
        """Test that spawn messages must have task_id"""
        msg = {
            "id": "20231101T123456.789Z-abc123",
            "ts": 1698842096789,
            "from": "pmai",
            "to": "bus",
            "type": "spawn",
            # Missing task_id
            "data": {
                "cwd": "work/T001",
                "frame": "frames/impl/CLAUDE.md"
            }
        }
        
        with self.assertRaises(ValidationError) as cm:
            validate_message(msg)
        self.assertIn("Spawn messages must include task_id", str(cm.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)