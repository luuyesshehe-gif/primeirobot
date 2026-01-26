import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import asyncio
import time
from datetime import datetime, date

# ======================
# CONFIGURAÇÃO
# ======================
TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1316931391430197268
ROLE_ID = 1317717808737419295

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "boosts.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# ======================
# INTENTS
# ======================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="-", intents=intents)
tree = bot.tree
GUILD_OBJ = discord.Object(id=GUILD_ID)

# ======================
# JSON
# ======================
def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

boost_data = load_json(DATA_FILE)
config = load_json(CONFIG_FILE)

# ======================
# LOG
# ======================
async def send_log(msg):
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    channel_id = config.get("log_channel_id")
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(msg)

# ======================
# MENSAGEM POR INTERVALO
# ======================
@tasks.loop(minutes=1)
async def mensagem_intervalo():
    if "auto_message" not in config:
        return

    agora = time.time()
    ultimo = config.get("last_sent", 0)
    intervalo = config.get("auto_interval", 0)

    if agora - ultimo < intervalo:
        return

    guild = bot.get_guild(GUILD_ID)
    canal = guild.get_channel(config.get("auto_channel_id"))
    if canal:
        await canal.send(config["auto_message"])
        config["last_sent"] = agora
        save_json(CONFIG_FILE, config)

# ======================
# MENSAGEM HORÁRIO FIXO
# ======================
@tasks.loop(minutes=1)
async def mensagem_horario_fixo():
    if "fixed_message" not in config:
        return

    agora = datetime.now()
    hora = agora.strftime("%H:%M")
    hoje = date.today().isoformat()

    if config.get("last_fixed_date") == hoje:
        return

    if hora not in config.get("fixed_times", []):
        return

    guild = bot.get_guild(GUILD_ID)
    canal = guild.get_channel(config.get("fixed_channel_id"))
    if canal:
        await canal.send(config["fixed_message"])
        config["last_fixed_date"] = hoje
        save_json(CONFIG_FILE, config)

# ======================
# EVENTOS
# ======================
@bot.event
async def on_ready():
    print(f"🤖 Online como {bot.user}")

    await tree.sync(guild=GUILD_OBJ)

    if not mensagem_intervalo.is_running():
        mensagem_intervalo.start()
    if not mensagem_horario_fixo.is_running():
        mensagem_horario_fixo.start()

    guild = bot.get_guild(GUILD_ID)
    role = guild.get_role(ROLE_ID)

    for member in guild.members:
        if member.premium_since and role not in member.roles:
            await member.add_roles(role)

    print("✅ Bot pronto")

@bot.event
async def on_member_update(before, after):
    role = after.guild.get_role(ROLE_ID)
    user_id = str(after.id)

    if before.premium_since is None and after.premium_since:
        boost_data[user_id] = boost_data.get(user_id, 0) + 1
        save_json(DATA_FILE, boost_data)

        if boost_data[user_id] >= 2 and role not in after.roles:
            await after.add_roles(role)
            await send_log(f"🎉 {after} recebeu cargo")

    if before.premium_since and after.premium_since is None:
        if role in after.roles:
            await after.remove_roles(role)
            await send_log(f"❌ Cargo removido de {after}")

# ======================
# SLASH COMMANDS
# ======================
@tree.command(name="ping", description="Teste", guild=GUILD_OBJ)
async def ping(interaction):
    await interaction.response.send_message("🏓 Pong!")

@tree.command(name="identificarboosters", description="Corrige boosters", guild=GUILD_OBJ)
async def identificarboosters(interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    role = interaction.guild.get_role(ROLE_ID)
    count = 0

    for member in interaction.guild.members:
        if member.premium_since and role not in member.roles:
            await member.add_roles(role)
            count += 1

    await interaction.response.send_message(f"✅ {count} corrigidos")

@tree.command(name="setlogchannel", description="Define canal de logs", guild=GUILD_OBJ)
async def setlogchannel(interaction, canal: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    config["log_channel_id"] = canal.id
    save_json(CONFIG_FILE, config)
    await interaction.response.send_message("✅ Canal definido")

@tree.command(name="say", description="Repete mensagem", guild=GUILD_OBJ)
async def say(interaction, mensagem: str, canal: discord.TextChannel = None):
    if canal:
        await canal.send(mensagem)
        await interaction.response.send_message("✅ Enviado", ephemeral=True)
    else:
        await interaction.response.send_message(mensagem)

@tree.command(name="ban", description="Bane usuário", guild=GUILD_OBJ)
async def ban(interaction, usuario: discord.Member, motivo: str = None):
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    await usuario.ban(reason=motivo)
    await interaction.response.send_message("🔨 Usuário banido")

@tree.command(name="kick", description="Expulsa usuário", guild=GUILD_OBJ)
async def kick(interaction, usuario: discord.Member, motivo: str = None):
    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    await usuario.kick(reason=motivo)
    await interaction.response.send_message("👢 Usuário expulso")

@tree.command(name="mute", description="Silencia usuário", guild=GUILD_OBJ)
async def mute(interaction, usuario: discord.Member, tempo: int = None):
    if not interaction.user.guild_permissions.manage_roles:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    guild = interaction.guild
    mute_role = discord.utils.get(guild.roles, name="Muted")
    if not mute_role:
        mute_role = await guild.create_role(name="Muted")
        for ch in guild.channels:
            await ch.set_permissions(mute_role, send_messages=False, speak=False)

    await usuario.add_roles(mute_role)
    await interaction.response.send_message("🔇 Mutado")

    if tempo:
        await asyncio.sleep(tempo * 60)
        await usuario.remove_roles(mute_role)

# ======================
# MENSAGENS AUTOMÁTICAS
# ======================
@tree.command(name="setmensagemautomatica", description="Mensagem por intervalo", guild=GUILD_OBJ)
async def setmensagemautomatica(interaction, mensagem: str, horas: int, canal: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    config["auto_message"] = mensagem
    config["auto_interval"] = horas * 3600
    config["auto_channel_id"] = canal.id
    config["last_sent"] = 0
    save_json(CONFIG_FILE, config)

    await interaction.response.send_message("✅ Mensagem automática configurada")

@tree.command(name="setmensagemhorariofixo", description="Mensagem horário fixo", guild=GUILD_OBJ)
async def setmensagemhorariofixo(interaction, mensagem: str, horarios: str, canal: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    config["fixed_message"] = mensagem
    config["fixed_times"] = [h.strip() for h in horarios.split(",")]
    config["fixed_channel_id"] = canal.id
    config["last_fixed_date"] = ""
    save_json(CONFIG_FILE, config)

    await interaction.response.send_message("✅ Horário fixo configurado")

@tree.command(name="statusmensagens", description="Status das mensagens", guild=GUILD_OBJ)
async def statusmensagens(interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    msg = "📊 **Status**\n\n"

    msg += "⏱ Intervalo: ATIVO\n" if "auto_message" in config else "⏱ Intervalo: OFF\n"
    msg += "⏰ Horário fixo: ATIVO\n" if "fixed_message" in config else "⏰ Horário fixo: OFF\n"

    await interaction.response.send_message(msg, ephemeral=True)

@tree.command(name="desativarmensagem", description="Desativa mensagens", guild=GUILD_OBJ)
async def desativarmensagem(interaction, tipo: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    if tipo == "intervalo":
        for k in ["auto_message", "auto_interval", "auto_channel_id", "last_sent"]:
            config.pop(k, None)
    elif tipo == "horario":
        for k in ["fixed_message", "fixed_times", "fixed_channel_id", "last_fixed_date"]:
            config.pop(k, None)
    else:
        return await interaction.response.send_message("❌ Use intervalo ou horario", ephemeral=True)

    save_json(CONFIG_FILE, config)
    await interaction.response.send_message("⛔ Mensagem desativada")

@tree.command(name="editarmensagem", description="Edita mensagem automática", guild=GUILD_OBJ)
async def editarmensagem(interaction, tipo: str, mensagem: str = None, horas: int = None, horarios: str = None, canal: discord.TextChannel = None):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    if tipo == "intervalo":
        if mensagem: config["auto_message"] = mensagem
        if horas: config["auto_interval"] = horas * 3600
        if canal: config["auto_channel_id"] = canal.id

    elif tipo == "horario":
        if mensagem: config["fixed_message"] = mensagem
        if horarios: config["fixed_times"] = [h.strip() for h in horarios.split(",")]
        if canal: config["fixed_channel_id"] = canal.id
    else:
        return await interaction.response.send_message("❌ Tipo inválido", ephemeral=True)

    save_json(CONFIG_FILE, config)
    await interaction.response.send_message("✅ Atualizado")

# ======================
# START
# ======================
bot.run(TOKEN)
