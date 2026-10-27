import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os

# ── Config ───────────────────────────────────────────────────────────────────
RENDER_URL = "https://meow-1-k118.onrender.com"
BOT_TOKEN = os.environ.get("BOT_TOKEN")   # Set this in Render env vars, NOT hardcoded

# ── Bot setup ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user} | Slash commands synced")


# ── /getkey ──────────────────────────────────────────────────────────────────
@tree.command(name="getkey", description="Get your ZERO X key via LootLabs")
async def getkey(interaction: discord.Interaction):
    discord_id = str(interaction.user.id)
    link = f"{RENDER_URL}/start?discord_id={discord_id}"

    embed = discord.Embed(
        title="🔑 ZERO X Key System",
        description=(
            f"Click the link below to complete the ad and receive your key.\n\n"
            f"**[➡️ Get Your Key]({link})**\n\n"
            f"After completing the ad, you'll see your key on-screen.\n"
            f"Then use `/redeem <key>` here to activate it.\n\n"
            f"Keys are valid for **12 hours**."
        ),
        color=0x00ff88
    )
    embed.set_footer(text="ZERO X Auto-Rejoiner")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ── /redeem ──────────────────────────────────────────────────────────────────
@tree.command(name="redeem", description="Redeem your ZERO X key")
@app_commands.describe(key="The key you received after completing the ad")
async def redeem(interaction: discord.Interaction, key: str):
    await interaction.response.defer(ephemeral=True)

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{RENDER_URL}/checkkey?key={key}") as resp:
            data = await resp.json()

    if not data.get("valid"):
        reason = data.get("reason", "Invalid key")
        await interaction.followup.send(
            f"❌ **Key invalid:** {reason}\nRun `/getkey` to get a new one.",
            ephemeral=True
        )
        return

    # Make sure key belongs to this user
    if data.get("discord_id") != str(interaction.user.id):
        await interaction.followup.send(
            "❌ This key doesn't belong to your account.",
            ephemeral=True
        )
        return

    expires_in = data.get("expires_in", "unknown")
    await interaction.followup.send(
        f"✅ **Key redeemed!**\nYour key is active for **{expires_in}**.\n"
        f"Use it in the rejoiner tool when prompted.",
        ephemeral=True
    )


# ── /checkkey ────────────────────────────────────────────────────────────────
@tree.command(name="checkkey", description="Check if your key is still valid")
@app_commands.describe(key="The key to check")
async def checkkey(interaction: discord.Interaction, key: str):
    await interaction.response.defer(ephemeral=True)

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{RENDER_URL}/checkkey?key={key}") as resp:
            data = await resp.json()

    if data.get("valid"):
        expires_in = data.get("expires_in", "unknown")
        await interaction.followup.send(
            f"✅ Key is **valid** — expires in **{expires_in}**.",
            ephemeral=True
        )
    else:
        reason = data.get("reason", "Unknown")
        await interaction.followup.send(
            f"❌ Key is **invalid**: {reason}",
            ephemeral=True
        )


# ── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set!")
    bot.run(BOT_TOKEN)
