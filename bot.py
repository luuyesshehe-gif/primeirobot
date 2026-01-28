import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import asyncio
import re

# ======================
# CONFIGURAÇÃO
# ======================
TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1316931391430197268
ROLE_2X = 1317717808737419295

LOG_VERIFY = 1465942893209583838
LOG_REMOVE = 1465946692191785041

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LIST_FILE = os.path.join(BASE_DIR, "booster_list.json")

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
def load_list():
    if not os.path.exists(LIST_FILE):
        return []
    with open(LIST_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_list(data):
    with open(LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

booster_list = load_list()

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
# VERIFICAÇÃO AUTOMÁTICA
# ======================
@tasks.loop(minutes=5)
async def verificar_boosters():
    guild = bot.get_guild(GUILD_ID)
    role = guild.get_role(ROLE_2X)

    for user_id in booster_list.copy():
        member = guild.get_member(user_id)
        if not member or member.premium_since is None:
            if member and role in member.roles:
                await member.remove_roles(role)

            booster_list.remove(user_id)
            save_list(booster_list)

            await send_log(
                LOG_REMOVE,
                f"```2X BOOSTER REMOVIDO\n\n<{user_id}> teve seu cargo removido por parar de boostar```"
            )

# ======================
# EVENTOS
# ======================
@bot.event
async def on_ready():
    print(f"🤖 Online como {bot.user}")
    await tree.sync(guild=GUILD_OBJ)

    if not verificar_boosters.is_running():
        verificar_boosters.start()

@bot.event
async def on_member_update(before, after):
    if before.premium_since and after.premium_since is None:
        if after.id in booster_list:
            role = after.guild.get_role(ROLE_2X)
            if role in after.roles:
                await after.remove_roles(role)

            booster_list.remove(after.id)
            save_list(booster_list)

            await send_log(
                LOG_REMOVE,
                f"```2X BOOSTER REMOVIDO\n\n<{after.id}> removeu seus boosters```"
            )

# ======================
# SLASH COMMANDS
# ======================
def extract_ids(text):
    return [int(x) for x in re.findall(r"\d{17,20}", text)]

@tree.command(name="addmemberlist", description="Adiciona membros 2x booster", guild=GUILD_OBJ)
async def addmemberlist(interaction, membros: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    ids = extract_ids(membros)
    guild = interaction.guild
    role = guild.get_role(ROLE_2X)

    adicionados = []

    for uid in ids:
        member = guild.get_member(uid)
        if not member or uid in booster_list:
            continue

        booster_list.append(uid)
        if role not in member.roles:
            await member.add_roles(role)

        adicionados.append(member)

        await send_log(
            LOG_VERIFY,
            f"```DEU SEU 2X BOOSTERS\n\n<{uid}> recebeu o cargo de 2x booster```"
        )

    save_list(booster_list)
    await interaction.response.send_message(f"✅ {len(adicionados)} membros adicionados", ephemeral=True)

@tree.command(name="removememberlist", description="Remove membros da lista 2x", guild=GUILD_OBJ)
async def removememberlist(interaction, membros: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    ids = extract_ids(membros)
    guild = interaction.guild
    role = guild.get_role(ROLE_2X)

    removidos = []

    for uid in ids:
        if uid not in booster_list:
            continue

        member = guild.get_member(uid)
        booster_list.remove(uid)

        if member and role in member.roles:
            await member.remove_roles(role)

        removidos.append(uid)

        await send_log(
            LOG_REMOVE,
            f"```2X BOOSTER REMOVIDO\n\n<{uid}> removido manualmente```"
        )

    save_list(booster_list)
    await interaction.response.send_message(f"✅ {len(removidos)} membros removidos", ephemeral=True)

@tree.command(name="checkboosterlist", description="Ver lista 2x boosters", guild=GUILD_OBJ)
async def checkboosterlist(interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    if not booster_list:
        return await interaction.response.send_message("📭 Lista vazia", ephemeral=True)

    guild = interaction.guild
    msg = "✨︱ **Lista 2x Boosters:**\n\n"

    for uid in booster_list:
        member = guild.get_member(uid)
        if member:
            msg += f"Member: {member.name} ︱ ID: <@{uid}>\n"
        else:
            msg += f"Member: Desconhecido ︱ ID: <@{uid}>\n"

    await interaction.response.send_message(msg, ephemeral=True)

# ======================
# START
# ======================
bot.run(TOKEN)
