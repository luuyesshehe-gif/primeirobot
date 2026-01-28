import discord
from discord.ext import commands, tasks
from discord import app_commands
import os, json
from datetime import datetime

# ================= CONFIGURAÇÃO =================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1316931391430197268
ROLE_2X = 1317717808737419295
LOG_VERIFY = 1465942893209583838
LOG_REMOVE = 1465946692191785041
DATA_FILE = "booster_list.json"

# ================= INTENTS =================
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
GUILD_OBJ = discord.Object(id=GUILD_ID)

# ================= FUNÇÕES DE ARQUIVO =================
def load_booster_list():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_booster_list():
    with open(DATA_FILE, "w") as f:
        json.dump(list(booster_list), f, indent=4)

booster_list = load_booster_list()

# ================= FUNÇÕES AUXILIARES =================
def now():
    return datetime.now().strftime("%d/%m/%Y • %H:%M:%S")

async def send_log(channel_id, embed):
    guild = bot.get_guild(GUILD_ID)
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed)

# ================= EMBEDS PROFISSIONAIS =================
def embed_verify(member, origem="Automática"):
    embed = discord.Embed(
        title="🟢 Cargo 2x Booster Aplicado",
        description=f"O usuário {member.mention} recebeu o cargo **2x Booster**.",
        color=0x57F287,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID do Usuário", value=member.id, inline=True)
    embed.add_field(name="Origem", value=origem, inline=True)
    embed.set_footer(text="Sistema de Boosters • Oásis Server")
    return embed

def embed_remove(member, motivo="Removeu boost"):
    embed = discord.Embed(
        title="❌ Cargo 2x Booster Removido",
        description=f"O usuário {member.mention} perdeu o cargo **2x Booster**.",
        color=0xED4245,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ID do Usuário", value=member.id, inline=True)
    embed.add_field(name="Motivo", value=motivo, inline=True)
    embed.set_footer(text="Sistema de Boosters • Oásis Server")
    return embed

def embed_painel():
    embed = discord.Embed(
        title="✨ Painel de 2x Boosters",
        description=f"Gerencie os usuários com o cargo 2x Booster.\nTotal na lista: **{len(booster_list)}**",
        color=0x5865F2,
        timestamp=datetime.now()
    )
    embed.set_footer(text="Sistema de Boosters • Oásis Server")
    return embed

# ================= VERIFICAÇÃO AUTOMÁTICA =================
@tasks.loop(seconds=60)
async def verificar_boosters():
    guild = bot.get_guild(GUILD_ID)
    role = guild.get_role(ROLE_2X)
    to_remove = set()

    for uid in list(booster_list):
        member = guild.get_member(uid)
        if member:
            # Remove cargo se não tiver boost
            if not member.premium_since:
                to_remove.add(uid)
                if role in member.roles:
                    await member.remove_roles(role)
                    await send_log(LOG_REMOVE, embed_remove(member))
            # Adiciona cargo se tiver boost
            elif role not in member.roles:
                await member.add_roles(role)
                await send_log(LOG_VERIFY, embed_verify(member))

    if to_remove:
        booster_list.difference_update(to_remove)
        save_booster_list()

# ================= TEMPO REAL =================
@bot.event
async def on_member_update(before, after):
    role = after.guild.get_role(ROLE_2X)
    if before.premium_since is None and after.premium_since:
        if after.id in booster_list and role not in after.roles:
            await after.add_roles(role)
            await send_log(LOG_VERIFY, embed_verify(after, origem="Tempo real"))
    elif before.premium_since and after.premium_since is None:
        if after.id in booster_list and role in after.roles:
            await after.remove_roles(role)
            await send_log(LOG_REMOVE, embed_remove(after, motivo="Removeu boost"))

# ================= VIEWS E DROPDOWN =================
class BoosterSelect(discord.ui.Select):
    def __init__(self, members):
        options = [
            discord.SelectOption(
                label=f"{m.display_name}",
                description=f"ID: {m.id}",
                value=str(m.id)
            ) for m in members
        ]
        super().__init__(placeholder="Selecione um membro para remover", options=options)

    async def callback(self, interaction: discord.Interaction):
        uid = int(self.values[0])
        member = interaction.guild.get_member(uid)
        role = interaction.guild.get_role(ROLE_2X)

        if uid in booster_list:
            booster_list.discard(uid)
            save_booster_list()

        if member and role in member.roles:
            await member.remove_roles(role)
            await send_log(LOG_REMOVE, embed_remove(member, motivo="Removido via Painel"))

        await interaction.response.send_message(f"❌ {member.mention} removido da lista", ephemeral=True)

class AddMemberModal(discord.ui.Modal, title="Adicionar Membros à Lista"):
    membros = discord.ui.TextInput(label="IDs ou menções (separadas por vírgula)", style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        ids = [int(x.replace("<@", "").replace(">", "").strip()) for x in self.membros.value.split(",")]
        for uid in ids:
            booster_list.add(uid)
        save_booster_list()
        await interaction.response.send_message(f"✅ {len(ids)} membros adicionados à lista", ephemeral=True)

class BoosterPanelView(discord.ui.View):
    def __init__(self, members):
        super().__init__(timeout=None)
        self.add_item(BoosterSelect(members))
        self.add_item(AddMemberButton())

class AddMemberButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.green, label="➕ Adicionar Membro", emoji="➕")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddMemberModal())

# ================= SLASH COMMANDS =================
@tree.command(name="painelbooster", description="Painel de gerenciamento de 2x Boosters", guild=GUILD_OBJ)
async def painel(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    guild = interaction.guild
    members = [guild.get_member(uid) for uid in booster_list if guild.get_member(uid)]
    await interaction.response.send_message(embed=embed_painel(), view=BoosterPanelView(members), ephemeral=True)

# ================= READY =================
@bot.event
async def on_ready():
    print(f"🤖 Online como {bot.user}")
    await tree.sync(guild=GUILD_OBJ)
    if not verificar_boosters.is_running():
        verificar_boosters.start()
    print("✅ Sistema 2x Booster ativo")

bot.run(TOKEN)
