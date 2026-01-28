import discord
from discord.ext import commands, tasks
import os
import json

# ======================
# CONFIG
# ======================
TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1316931391430197268
ROLE_2X = 1317717808737419295

LOG_ADD_IMEDIATO = 1465942893209583838
LOG_VERIFICACAO = 146594289320958383
LOG_REMOVIDO = 1465946692191785041

DATA_FILE = "boosts.json"

# ======================
# INTENTS
# ======================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

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
async def send_log(channel_id, msg):
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(msg)

# ======================
# EVENTO BOOST (IMEDIATO)
# ======================
@bot.event
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since:
        uid = str(after.id)
        boosts[uid] = boosts.get(uid, 0) + 1
        save_boosts(boosts)

        if boosts[uid] >= 2:
            role = after.guild.get_role(ROLE_2X)
            if role not in after.roles:
                await after.add_roles(role)
                await send_log(
                    LOG_ADD_IMEDIATO,
                    f"""DEU SEU 2X BOOSTERS

<{after.id}> recebeu seu cargo de 2x booster!"""
                )

# ======================
# VERIFICAÇÃO 10 MIN
# ======================
@tasks.loop(minutes=10)
async def verificar_2x():
    guild = bot.get_guild(GUILD_ID)
    role = guild.get_role(ROLE_2X)

    for member in guild.members:
        uid = str(member.id)
        if boosts.get(uid, 0) >= 2 and role not in member.roles:
            await member.add_roles(role)
            await send_log(
                LOG_VERIFICACAO,
                f"""VERIFICAÇÃO DE 2X BOOSTERS

<{member.id}> recebeu seu cargo de 2x booster!"""
            )

# ======================
# REMOÇÃO 15 MIN
# ======================
@tasks.loop(minutes=15)
async def remover_2x():
    guild = bot.get_guild(GUILD_ID)
    role = guild.get_role(ROLE_2X)

    for member in guild.members:
        uid = str(member.id)
        if boosts.get(uid, 0) < 2 and role in member.roles:
            await member.remove_roles(role)
            await send_log(
                LOG_REMOVIDO,
                f"""2X BOOSTER REMOVIDO

<{member.id}> teve seu cargo de 2x booster removido por retirar seu 2x booster!"""
            )

# ======================
# READY
# ======================
@bot.event
async def on_ready():
    print(f"🤖 Online como {bot.user}")
    if not verificar_2x.is_running():
        verificar_2x.start()
    if not remover_2x.is_running():
        remover_2x.start()

# ======================
# START
# ======================
bot.run(TOKEN)
