with open('/home/tis/Projects/discord-server-generator/src/validator.py', 'r') as f:
    content = f.read()

replacement_func = """def _validate_messages(messages: Any, errors: List[str]) -> None:
    if not isinstance(messages, list):
        errors.append("messages: must be a list")
        return
    for i, msg in enumerate(messages):
        path = f"messages[{i}]"
        if not isinstance(msg, dict):
            errors.append(f"{path}: must be an object")
            continue
        _check_str(msg.get("channel"), f"{path}.channel", errors)
        _check_str(msg.get("content"), f"{path}.content", errors)
        
        if "use_webhook" in msg:
            _check_bool(msg["use_webhook"], f"{path}.use_webhook", errors)
        if "webhook_name" in msg and not isinstance(msg["webhook_name"], str):
            errors.append(f"{path}.webhook_name: must be a string")
        if "webhook_avatar_url" in msg and msg["webhook_avatar_url"] is not None and not isinstance(msg["webhook_avatar_url"], str):
            errors.append(f"{path}.webhook_avatar_url: must be a string or null")"""

validation_call = """
    messages = blueprint.get("messages")
    if messages is not None:
        _validate_messages(messages, errors)

    return len(errors) == 0, errors"""

content = content.replace("def validate(", replacement_func + "\n\n\ndef validate(")
content = content.replace("    return len(errors) == 0, errors", validation_call)

with open('/home/tis/Projects/discord-server-generator/src/validator.py', 'w') as f:
    f.write(content)

