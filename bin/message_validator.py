#!/usr/bin/env python3
"""
Message validator module - minimal implementation to make tests pass (GREEN phase)
Following TDD principles from CLAUDE.md
"""


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_message(msg):
    """
    Validate message structure according to the message bus schema.
    
    Args:
        msg: Dictionary containing the message
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If message is invalid
    """
    # Check required fields
    required_fields = ['id', 'ts', 'from', 'to', 'type', 'data']
    for field in required_fields:
        if field not in msg:
            raise ValidationError(f"Missing required field: {field}")
    
    # Check valid message types
    valid_types = ['spawn', 'send', 'post', 'log', 'result', 'error', 'instruct']
    if msg['type'] not in valid_types:
        raise ValidationError(f"Invalid message type: {msg['type']}")
    
    # Special validation for spawn messages
    if msg['type'] == 'spawn':
        if 'task_id' not in msg:
            raise ValidationError("Spawn messages must include task_id")
    
    # Special validation for result messages
    if msg['type'] == 'result':
        if 'data' not in msg or 'is_error' not in msg['data']:
            raise ValidationError("Result messages must include is_error in data")
    
    return True