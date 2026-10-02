with open('/home/tis/Projects/discord-server-generator/src/commands.py', 'r') as f:
    content = f.read()

content = content.replace("`{guild_id_int}`, or that ID is wrong.\\n\"\n", "`{guild_id_int}`, or that ID is wrong.\\n\"\n")
content = content.replace('wrong.\\n"', 'wrong.\\n" \\\n')
content = content.replace('JSON file: `{exc}`\\nPlease', 'JSON file: `{exc}`\\n" \\\n                    "Please')
content = content.replace('validation failed:\\n{error_list}"', 'validation failed:\\n" \\\n                    f"{error_list}"')
content = content.replace('guild {target_guild.id}`)\\n\\n"\n', 'guild {target_guild.id}`)\\n\\n" \\\n')
content = content.replace('Name:** {server_name}\\n"\n', 'Name:** {server_name}\\n" \\\n')
content = content.replace("or '—'}\\n\\n\"\n", "or '—'}\\n\\n\" \\\n")
content = content.replace('Roles:** {num_roles}\\n"\n', 'Roles:** {num_roles}\\n" \\\n')
content = content.replace('Categories:** {num_cats}\\n"\n', 'Categories:** {num_cats}\\n" \\\n')
content = content.replace('Channels:** {num_channels}\\n"\n', 'Channels:** {num_channels}\\n" \\\n')
content = content.replace('summary[:1900] + "\\n…(truncated)"', 'summary[:1900] + "\\n…(truncated)"')
content = content.replace('complete for {server_name}**\\n\\n{summary}"', 'complete for {server_name}**\\n\\n" \\\n                    f"{summary}"')

with open('/home/tis/Projects/discord-server-generator/src/commands.py', 'w') as f:
    f.write(content)
