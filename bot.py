import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import asyncio

# ======================
# CONFIGURAÇÃO
# ======================
TOKEN = os.getenv("DISCORD_TOKEN")  # ou coloque direto como string

GUILD_ID = 1316931391430197268
ROLE_2X = 1317717808737419295

LOG_VERIFICACAO = 1465942893209583838
LOG_REMOCAO = 1465946692191785041

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
def load_boosts():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_boosts(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

boosts = load_boosts()

# ======================
# LOG
# ======================
async def send_log(channel_id: int, message: str):
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(message)

# ======================
# VERIFICAÇÃO PRINCIPAL
# ======================
async def executar_verificacao():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    await guild.chunk()
    role = guild.get_role(ROLE_2X)

    for member in guild.members:
        uid = str(member.id)
        total = boosts.get(uid, 0)

        if total >= 2 and role not in member.roles:
            await member.add_roles(role)

            await send_log(
                LOG_VERIFICACAO,
                f"""```VERIFICAÇÃO DE 2X BOOSTERS

<{member.id}> recebeu seu cargo de 2x booster!```"""
            )

# ======================
# TASK 5 EM 5 MINUTOS
# ======================
@tasks.loop(minutes=5)
async def verificar_automatico():
    await executar_verificacao()

# ======================
# EVENTOS
# ======================
@bot.event
async def on_ready():
    print(f"🤖 Online como {bot.user}")

    await tree.sync(guild=GUILD_OBJ)

    guild = bot.get_guild(GUILD_ID)
    await guild.chunk()

    # 🔥 VERIFICA NA HORA
    await executar_verificacao()

    if not verificar_automatico.is_running():
        verificar_automatico.start()

    print("✅ Bot iniciado + verificação imediata executada")

# ======================
# BOOST EVENTOS
# ======================
@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    role = after.guild.get_role(ROLE_2X)
    uid = str(after.id)

    # DEU BOOST
    if before.premium_since is None and after.premium_since is not None:
        boosts[uid] = boosts.get(uid, 0) + 1
        save_boosts(boosts)

        if boosts[uid] >= 2 and role not in after.roles:
            await after.add_roles(role)

            await send_log(
                LOG_VERIFICACAO,
                f"""```DEU SEU 2X BOOSTERS

<{after.id}> recebeu seu cargo de 2x booster!```"""
            )

    # TIROU BOOST
    if before.premium_since is not None and after.premium_since is None:
        boosts[uid] = max(boosts.get(uid, 1) - 1, 0)
        save_boosts(boosts)

        if boosts[uid] < 2 and role in after.roles:
            await after.remove_roles(role)

            await send_log(
                LOG_REMOCAO,
                f"""```2X BOOSTER REMOVIDO

<{after.id}> teve seu cargo de 2x booster removido por retirar seu 2x booster!```"""
            )

# ======================
# SLASH COMMAND
# ======================
@tree.command(name="forcarverificacao", description="Força verificação de 2x boosters", guild=GUILD_OBJ)
async def forcarverificacao(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    await executar_verificacao()
    await interaction.response.send_message("✅ Verificação forçada executada", ephemeral=True)

# ======================
# START
# ======================
bot.run(TOKEN)
