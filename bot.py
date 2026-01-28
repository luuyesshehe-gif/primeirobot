import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
from datetime import datetime

# ======================
# CONFIGURAÇÃO
# ======================
TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1316931391430197268
ROLE_ID = 1317717808737419295

LOG_VERIFICACAO = 1465942893209583838
LOG_REMOVIDO = 1465946692191785041

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "boosts.json")

# ======================
# INTENTS
# ======================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="-", intents=intents)
tree = bot.tree
GUILD_OBJ = discord.Object(id=GUILD_ID)

# ======================
# JSON
# ======================
def load_json():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

boost_data = load_json()

# ======================
# LOGS
# ======================
async def send_log(channel_id, message):
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(message)

# ======================
# EVENTO BOOST
# ======================
@bot.event
async def on_member_update(before, after):
    role = after.guild.get_role(ROLE_ID)
    user_id = str(after.id)

    # Ganhou boost
    if before.premium_since is None and after.premium_since:
        boost_data[user_id] = boost_data.get(user_id, 0) + 1
        save_json(boost_data)

    # Perdeu boost
    if before.premium_since and after.premium_since is None:
        boost_data[user_id] = max(boost_data.get(user_id, 1) - 1, 0)
        save_json(boost_data)

        if boost_data[user_id] < 2 and role in after.roles:
            await after.remove_roles(role)
            await send_log(
                LOG_REMOVIDO,
                f"""2X BOOSTER REMOVIDO

"{after.id}" removeu seu 2x booster do servidor!"""
            )

# ======================
# VERIFICAÇÃO A CADA 10 MIN
# ======================
@tasks.loop(minutes=10)
async def verificar_2x_boosters():
    guild = bot.get_guild(GUILD_ID)
    role = guild.get_role(ROLE_ID)

    corrigidos = []

    for member in guild.members:
        user_id = str(member.id)
        boosts = boost_data.get(user_id, 0)

        if boosts >= 2 and role not in member.roles:
            await member.add_roles(role)
            corrigidos.append(member.id)

    if corrigidos:
        for uid in corrigidos:
            await send_log(
                LOG_VERIFICACAO,
                f"""VERIFICAÇÃO DE 2X BOOSTERS

<{uid}> recebeu seu cargo de 2x booster!"""
            )

# ======================
# SLASH COMMAND (PING)
# ======================
@tree.command(name="ping", description="Teste", guild=GUILD_OBJ)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

# ======================
# READY
# ======================
@bot.event
async def on_ready():
    print(f"🤖 Online como {bot.user}")
    await tree.sync(guild=GUILD_OBJ)

    if not verificar_2x_boosters.is_running():
        verificar_2x_boosters.start()

    print("✅ Sistema de 2x booster ativo")

# ======================
# START
# ======================
bot.run(TOKEN)
