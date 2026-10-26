import discord
from discord.ext import commands
import requests

# ── Config ───────────────────────────────────────────────────
BOT_TOKEN = "MTU2NDMzODk4MTA3ODgzMTE1NA.GYpwpX.1d13A0lLbPR4MhnwapLGZmTQoYslBB2qyBrbvY"
SERVER_URL = "http://YOUR_CLOUD_PHONE_IP:5000"  # Change this to your cloud phone IP
LOOTLABS_LINK = "https://lootdest.org/s?xe29pTXR"

# ── Bot setup ────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Sync error: {e}")

# ── /getkey command ──────────────────────────────────────────
@bot.tree.command(name="getkey", description="Get your verification link to obtain a key")
async def getkey(interaction: discord.Interaction):
    discord_id = str(interaction.user.id)
    verify_url = f"{SERVER_URL}/getkey?id={discord_id}"

    embed = discord.Embed(
        title="🔑 Get Your Key - ZERO X",
        description=(
            f"To get your key, you need to complete the verification:\n\n"
            f"**Step 1:** Click the link below\n"
            f"**Step 2:** Watch the ads on LootLabs\n"
            f"**Step 3:** You'll be redirected back automatically\n"
            f"**Step 4:** Come back and use `/redeem` to get your key\n\n"
            f"🔗 [Click here to verify]({verify_url})\n\n"
            f"⏳ Keys expire every **12 hours**"
        ),
        color=0x7289da
    )
    embed.set_footer(text="ZERO X Rejoiner Tool")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ── /redeem command ──────────────────────────────────────────
@bot.tree.command(name="redeem", description="Redeem your key after completing verification")
async def redeem(interaction: discord.Interaction):
    discord_id = str(interaction.user.id)
    await interaction.response.defer(ephemeral=True)

    try:
        res = requests.get(f"{SERVER_URL}/getkey_for_discord?id={discord_id}", timeout=10)
        data = res.json()

        if res.status_code == 200 and "key" in data:
            embed = discord.Embed(
                title="✅ Key Redeemed Successfully!",
                description=(
                    f"Here is your key:\n\n"
                    f"```\n{data['key']}\n```\n"
                    f"Use this key in the ZERO X Rejoiner tool in Termux.\n\n"
                    f"⏳ Expires at: `{data['expires_at']} UTC`\n\n"
                    f"⚠️ **Keep this key private! Do not share it.**"
                ),
                color=0x00ff00
            )
            embed.set_footer(text="ZERO X Rejoiner Tool")
            await interaction.followup.send(embed=embed, ephemeral=True)

        else:
            error_msg = data.get("error", "Unknown error")
            verify_url = f"{SERVER_URL}/getkey?id={discord_id}"
            embed = discord.Embed(
                title="❌ No Key Found",
                description=(
                    f"{error_msg}\n\n"
                    f"👉 [Click here to verify first]({verify_url})"
                ),
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Server error: {str(e)}", ephemeral=True)

# ── /checkkey command ────────────────────────────────────────
@bot.tree.command(name="checkkey", description="Check if your key is still valid")
async def checkkey(interaction: discord.Interaction, key: str):
    await interaction.response.defer(ephemeral=True)

    try:
        res = requests.get(f"{SERVER_URL}/validate?key={key}", timeout=10)
        data = res.json()

        if data.get("valid"):
            embed = discord.Embed(
                title="✅ Key is Valid!",
                description=f"⏳ Expires at: `{data['expires_at']} UTC`",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="❌ Key Invalid",
                description=f"Reason: {data.get('reason', 'Unknown')}",
                color=0xff0000
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Server error: {str(e)}", ephemeral=True)

bot.run(BOT_TOKEN)
