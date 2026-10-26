import discord
from discord.ext import commands
import requests

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # paste your token here
SERVER_URL = "https://YOUR_TUNNEL_URL"  # updated each time tunnel starts

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    await bot.tree.sync()
    print("✅ Synced 3 slash commands")

@bot.tree.command(name="getkey", description="Get your verification link to obtain a key")
async def getkey(interaction: discord.Interaction):
    did = str(interaction.user.id)
    url = f"{SERVER_URL}/getkey?id={did}"
    embed = discord.Embed(
        title="🔑 Get Your Key - ZERO X",
        description=(
            f"**Step 1:** Click the link below\n"
            f"**Step 2:** Watch the ads on LootLabs\n"
            f"**Step 3:** Enter your Discord ID on the page\n"
            f"**Step 4:** Come back and use `/redeem`\n\n"
            f"🔗 [Click here to verify]({url})\n\n"
            f"⏳ Keys expire every **12 hours**"
        ),
        color=0x7289da
    )
    embed.set_footer(text="ZERO X Rejoiner Tool")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="redeem", description="Redeem your key after verification")
async def redeem(interaction: discord.Interaction):
    did = str(interaction.user.id)
    await interaction.response.defer(ephemeral=True)
    try:
        res = requests.get(f"{SERVER_URL}/getkey_for_discord?id={did}", timeout=10)
        data = res.json()
        if res.status_code == 200 and "key" in data:
            embed = discord.Embed(
                title="✅ Key Redeemed!",
                description=(
                    f"Your key:\n```\n{data['key']}\n```\n"
                    f"Paste this in the ZERO X Rejoiner tool!\n\n"
                    f"⏳ Expires: `{data['expires_at']} UTC`\n\n"
                    f"⚠️ Keep this private!"
                ),
                color=0x00ff00
            )
        else:
            url = f"{SERVER_URL}/getkey?id={did}"
            embed = discord.Embed(
                title="❌ No Key Found",
                description=f"{data.get('error','Unknown error')}\n\n👉 [Verify here]({url})",
                color=0xff0000
            )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Server error: {e}", ephemeral=True)

@bot.tree.command(name="checkkey", description="Check if your key is still valid")
async def checkkey(interaction: discord.Interaction, key: str):
    await interaction.response.defer(ephemeral=True)
    try:
        data = requests.get(f"{SERVER_URL}/validate?key={key}", timeout=10).json()
        if data.get("valid"):
            embed = discord.Embed(title="✅ Key Valid!", description=f"Expires: `{data['expires_at']} UTC`", color=0x00ff00)
        else:
            embed = discord.Embed(title="❌ Invalid Key", description=data.get("reason", "Unknown"), color=0xff0000)
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

bot.run(BOT_TOKEN)
