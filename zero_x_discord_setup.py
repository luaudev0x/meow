"""ZERO X server setup (safe by default).

Install: python -m pip install -U discord.py
Set token locally: export DISCORD_BOT_TOKEN='your bot token'
Preview: python zero_x_discord_setup.py
Apply: python zero_x_discord_setup.py --apply

Only creates missing categories/channels/roles in the specified guild.
Does not delete, rename, reorder, or edit existing server resources.
"""
import argparse
import asyncio
import os
import sys
import discord

GUILD_ID = 1571518695627563040
STRUCTURE = {
    "ZERO X | INFORMATION": ["announcements", "rules", "download-zero-x", "how-to-use"],
    "ZERO X | KEYS": ["get-key", "key-help", "key-status"],
    "ZERO X | COMMUNITY": ["general", "roblox-chat", "screenshots", "suggestions"],
    "ZERO X | SUPPORT": ["support", "bug-reports", "faq"],
    "ZERO X | STAFF": ["staff-chat", "bot-logs"],
}
ROLES = ("ZERO X Admin", "ZERO X Moderator", "ZERO X Member")
PRIVATE_CATEGORY = "ZERO X | STAFF"

parser = argparse.ArgumentParser(description="Preview or create ZERO X Discord server channels safely")
parser.add_argument("--apply", action="store_true", help="Actually create missing resources")
args = parser.parse_args()
token = os.environ.get("DISCORD_BOT_TOKEN")
if not token:
    sys.exit("DISCORD_BOT_TOKEN is missing. Set it in your own terminal; don't share it.")

intents = discord.Intents.none()
intents.guilds = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    try:
        guild = client.get_guild(GUILD_ID)
        if guild is None:
            guild = await client.fetch_guild(GUILD_ID)
        # fetch_guild is limited for resource listing; prefer cached full Guild.
        if not isinstance(guild, discord.Guild):
            print("Bot is not connected to this server. Invite it first with Manage Channels and Manage Roles.")
            return
        print(f"Server: {guild.name} ({guild.id})")
        me = guild.me
        if args.apply and (me is None or not (me.guild_permissions.manage_channels and me.guild_permissions.manage_roles)):
            print("Missing Manage Channels or Manage Roles. No changes made.")
            return
        roles = {}
        for name in ROLES:
            role = discord.utils.get(guild.roles, name=name)
            if role is None:
                print(f"[{'CREATE' if args.apply else 'PREVIEW'}] role: {name}")
                if args.apply:
                    role = await guild.create_role(name=name, permissions=discord.Permissions.none(),
                                                   mentionable=False, reason="ZERO X initial server setup")
            else:
                print(f"[KEEP] role: {name}")
            roles[name] = role

        for category_name, channels in STRUCTURE.items():
            category = discord.utils.get(guild.categories, name=category_name)
            is_private = category_name == PRIVATE_CATEGORY
            if category is None:
                print(f"[{'CREATE' if args.apply else 'PREVIEW'}] category: {category_name}")
                if args.apply:
                    perms = None
                    if is_private:
                        perms = {
                            guild.default_role: discord.PermissionOverwrite(view_channel=False),
                            roles["ZERO X Admin"]: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                            roles["ZERO X Moderator"]: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                            me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                        }
                    category = await guild.create_category(category_name, overwrites=perms,
                                                           reason="ZERO X initial server setup")
            else:
                print(f"[KEEP] category: {category_name}")
            for channel_name in channels:
                # Avoid duplicate names anywhere, including channels outside chosen category.
                existing = discord.utils.get(guild.text_channels, name=channel_name)
                if existing is not None:
                    print(f"  [KEEP] #{channel_name} (existing in {existing.category})")
                    continue
                print(f"  [{'CREATE' if args.apply else 'PREVIEW'}] #{channel_name}")
                if args.apply:
                    overrides = None
                    if is_private:
                        overrides = {
                            guild.default_role: discord.PermissionOverwrite(view_channel=False),
                            roles["ZERO X Admin"]: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                            roles["ZERO X Moderator"]: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                            me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                        }
                    await guild.create_text_channel(channel_name, category=category, overwrites=overrides,
                                                    reason="ZERO X initial server setup")
                    await asyncio.sleep(0.35)
        print("\nCompleted." if args.apply else "\nPreview only. Add --apply to create these resources.")
        print("No existing channels, categories, roles, or permissions were edited.")
        print("Invite your ZERO X key bot separately and configure commands if needed.")
    except discord.Forbidden:
        print("Discord denied a permission. Check the setup bot role and category overwrites.")
    except discord.HTTPException as e:
        print(f"Discord API error: HTTP {e.status} ({e.code}).")
    finally:
        await client.close()

client.run(token, log_handler=None)
