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
ROLE_2X = 1317717808737419295

LOG_VERIFY = 1465942893209583838
LOG_REMOVE = 1465946692191785041

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "booster_list.json")

# ======================
# INTENTS
# ======================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
GUILD_OBJ = discord.Object(id=GUILD_ID)

# ======================
# DADOS
# ======================
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

booster_list = set(load_data())

# ======================
# UTILS
# ======================
def now():
    return datetime.now().strftime("%d/%m/%Y • %H:%M:%S")

async def send_log(channel_id: int, embed: discord.Embed):
    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed)

# ======================
# VERIFICAÇÃO AUTOMÁTICA (5 EM 5)
# ======================
@tasks.loop(minutes=5)
async def verificar_2x():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    role = guild.get_role(ROLE_2X)

    for uid in list(booster_list):
        member = guild.get_member(uid)

        if not member or not member.premium_since:
            booster_list.discard(uid)
            save_data(list(booster_list))

            if member and role in member.roles:
                await member.remove_roles(role)

            embed = discord.Embed(
                title="❌ 2X BOOSTER REMOVIDO",
                description=(
                    f"👤 **Usuário:** <@{uid}>\n"
                    f"📝 **Motivo:** Removeu o boost\n"
                    f"🕒 **Hora:** {now()}"
                ),
                color=0xED4245
            )
            await send_log(LOG_REMOVE, embed)

        else:
            if role not in member.roles:
                await member.add_roles(role)

                embed = discord.Embed(
                    title="✅ VERIFICAÇÃO 2X BOOSTER",
                    description=(
                        f"👤 **Usuário:** <@{uid}>\n"
                        f"🎖 **Ação:** Cargo concedido\n"
                        f"🕒 **Hora:** {now()}"
                    ),
                    color=0x57F287
                )
                await send_log(LOG_VERIFY, embed)

# ======================
# BOOST EM TEMPO REAL
# ======================
@bot.event
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since:
        if after.id in booster_list:
            role = after.guild.get_role(ROLE_2X)
            if role not in after.roles:
                await after.add_roles(role)

            embed = discord.Embed(
                title="🚀 DEU BOOST (TEMPO REAL)",
                description=(
                    f"👤 **Usuário:** <@{after.id}>\n"
                    f"🎖 **Ação:** Cargo 2x concedido\n"
                    f"🕒 **Hora:** {now()}"
                ),
                color=0x5865F2
            )
            await send_log(LOG_VERIFY, embed)

# ======================
# DROPDOWN
# ======================
class RemoveDropdown(discord.ui.Select):
    def __init__(self, members):
        options = [
            discord.SelectOption(
                label=f"{member.name}",
                value=str(member.id),
                description=f"ID: {member.id}"
            )
            for member in members[:25]
        ]

        super().__init__(
            placeholder="Selecione um membro para remover",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        uid = int(self.values[0])
        booster_list.discard(uid)
        save_data(list(booster_list))

        guild = interaction.guild
        member = guild.get_member(uid)
        role = guild.get_role(ROLE_2X)

        if member and role in member.roles:
            await member.remove_roles(role)

        await interaction.response.send_message(
            f"❌ <@{uid}> removido da lista 2x booster.",
            ephemeral=True
        )

class BoosterListView(discord.ui.View):
    def __init__(self, members):
        super().__init__(timeout=180)
        self.add_item(RemoveDropdown(members))

# ======================
# SLASH COMMANDS
# ======================
@tree.command(name="addmemberlist", description="Adicionar membros à lista 2x booster", guild=GUILD_OBJ)
async def addmemberlist(interaction: discord.Interaction, membros: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    ids = []
    for m in membros.split(","):
        m = m.strip().replace("<@", "").replace(">", "")
        if m.isdigit():
            ids.append(int(m))

    for uid in ids:
        booster_list.add(uid)

    save_data(list(booster_list))
    await interaction.response.send_message("✅ Membros adicionados à lista.", ephemeral=True)

@tree.command(name="checkboosterlist", description="Ver lista de 2x boosters", guild=GUILD_OBJ)
async def checkboosterlist(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    guild = interaction.guild
    members = [guild.get_member(uid) for uid in booster_list if guild.get_member(uid)]

    desc = ""
    for m in members:
        desc += f"👤 <@{m.id}> ︱ `{m.id}`\n"

    embed = discord.Embed(
        title="✨ | Lista 2x Boosters",
        description=desc or "Nenhum membro na lista.",
        color=0x5865F2
    )

    view = BoosterListView(members)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@tree.command(name="forcarverificacao", description="Forçar verificação agora", guild=GUILD_OBJ)
async def forcarverificacao(interaction: discord.Interaction):
    await verificar_2x.callback()
    await interaction.response.send_message("🔄 Verificação executada.", ephemeral=True)

# ======================
# READY
# ======================
@bot.event
async def on_ready():
    print(f"🤖 Online como {bot.user}")
    await tree.sync(guild=GUILD_OBJ)

    if not verificar_2x.is_running():
        verificar_2x.start()

    print("✅ Sistema 2x Booster ativo")

# ======================
# START
# ======================
bot.run(TOKEN)
