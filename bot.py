import discord
from discord.ext import commands, tasks
import os, json

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1316931391430197268
ROLE_2X = 1317717808737419295

LOG_VERIFICACAO = 1465942893209583838
LOG_REMOCAO = 1465946692191785041

DATA_FILE = "boosts.json"

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
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(msg)

# ======================
# EVENTOS
# ======================
@bot.event
async def on_ready():
    print(f"🤖 Online como {bot.user}")
    verificar_2x.start()

@bot.event
async def on_member_update(before, after):
    uid = str(after.id)
    role = after.guild.get_role(ROLE_2X)

    # GANHOU BOOST
    if before.premium_since is None and after.premium_since:
        boosts[uid] = boosts.get(uid, 0) + 1
        save_boosts(boosts)

        if boosts[uid] >= 2 and role not in after.roles:
            await after.add_roles(role)
            await send_log(
                LOG_VERIFICACAO,
                f"""VERIFICAÇÃO DE 2X BOOSTERS

<{after.id}> recebeu seu cargo de 2x booster!"""
            )

    # PERDEU BOOST
    if before.premium_since and after.premium_since is None:
        boosts[uid] = max(boosts.get(uid, 0) - 1, 0)
        save_boosts(boosts)

        if boosts[uid] < 2 and role in after.roles:
            await after.remove_roles(role)
            await send_log(
                LOG_REMOCAO,
                f"""2X BOOSTER REMOVIDO

<{after.id}> teve seu cargo de 2x booster removido por retirar seu 2x booster!"""
            )

# ======================
# VERIFICAÇÃO AUTOMÁTICA (SÓ ADD)
# ======================
@tasks.loop(minutes=5)
async def verificar_2x():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

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
# START
# ======================
bot.run(TOKEN)
