import re
with open('/home/tis/Projects/discord-server-generator/src/views.py', 'r') as f:
    content = f.read()

modal_pattern = r'class BlueprintModal\(discord\.ui\.Modal, title="Paste AI Blueprint JSON"\):.*?class BuildConfirmView\(discord\.ui\.View\):'
content = re.sub(modal_pattern, 'class BuildConfirmView(discord.ui.View):', content, flags=re.DOTALL)

with open('/home/tis/Projects/discord-server-generator/src/views.py', 'w') as f:
    f.write(content)
