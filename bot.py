import discord
from discord.ext import commands, tasks
from discord import app_commands
import os, json
from datetime import datetime

# ================= CONFIG =================
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

# ================= DATA =================
def load():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE) as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

booster_list = set(load())

# ================= UTILS =================
def now():
    return datetime.now().strftime("%d/%m/%Y • %H:%M:%S")

async def send_embed_log(channel_id, embed):
    guild = bot.get_guild(GUILD_ID)
    ch = guild.get_channel(channel_id)
    if ch:
        await ch.send(embed=embed)

# ================= EMBEDS =================
def embed_verify(member, origem):
    e = discord.Embed(
        title="🛡️ Verificação 2x Booster",
        color=0x57F287
    )
    e.add_field(name="Usuário", value=member.mention, inline=False)
    e.add_field(name="ID", value=member.id)
    e.add_field(name="Ação", value="Cargo aplicado")
    e.add_field(name="Origem", value=origem)
    e.set_footer(text=now())
    return e

def embed_remove(member):
    e = discord.Embed(
        title="❌ 2x Booster Removido",
        color=0xED4245
    )
    e.add_field(name="Usuário", value=member.mention)
    e.add_field(name="ID", value=member.id)
    e.add_field(name="Motivo", value="Removeu boost")
    e.set_footer(text=now())
    return e

# ================= VERIFICAÇÃO =================
@tasks.loop(minutes=5)
async def verificar():
    guild = bot.get_guild(GUILD_ID)
    role = guild.get_role(ROLE_2X)

    for uid in list(booster_list):
        member = guild.get_member(uid)

        if not member or not member.premium_since:
            booster_list.discard(uid)
            save(list(booster_list))

            if member and role in member.roles:
                await member.remove_roles(role)
                await send_embed_log(LOG_REMOVE, embed_remove(member))
        else:
            if role not in member.roles:
                await member.add_roles(role)
                await send_embed_log(LOG_VERIFY, embed_verify(member, "Automática"))

# ================= TEMPO REAL =================
@bot.event
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since:
        if after.id in booster_list:
            role = after.guild.get_role(ROLE_2X)
            await after.add_roles(role)
            await send_embed_log(LOG_VERIFY, embed_verify(after, "Tempo real"))

# ================= DROPDOWN VIEW =================
class BoosterPanel(discord.ui.View):
    def __init__(self, members):
        super().__init__(timeout=120)
        self.members = members[:25]
        self.add_item(BoosterSelect(self.members))

class BoosterSelect(discord.ui.Select):
    def __init__(self, members):
        options = [
            discord.SelectOption(
                label=str(m),
                value=str(m),
                description="Remover da lista"
            ) for m in members
        ]
        super().__init__(
            placeholder="Selecione um membro para remover",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        uid = int(self.values[0])
        booster_list.discard(uid)
        save(list(booster_list))

        member = interaction.guild.get_member(uid)
        role = interaction.guild.get_role(ROLE_2X)

        if member and role in member.roles:
            await member.remove_roles(role)
            await send_embed_log(LOG_REMOVE, embed_remove(member))

        await interaction.response.send_message(
            f"❌ <@{uid}> removido da lista",
            ephemeral=True
        )

# ================= SLASH COMMANDS (GUILD ONLY) =================
@tree.command(name="painel2x", description="Painel 2x Booster", guild=GUILD_OBJ)
async def painel(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Sem permissão", ephemeral=True)

    embed = discord.Embed(
        title="✨ Painel 2x Boosters",
        description=f"Total na lista: **{len(booster_list)}**",
        color=0x5865F2
    )
    await interaction.response.send_message(
        embed=embed,
        view=BoosterPanel(list(booster_list)),
        ephemeral=True
    )

@tree.command(name="addmemberlist", description="Adicionar membros (IDs ou menções)", guild=GUILD_OBJ)
async def addmember(interaction: discord.Interaction, membros: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Sem permissão", ephemeral=True)

    ids = [int(x.replace("<@", "").replace(">", "").strip()) for x in membros.split(",")]
    for uid in ids:
        booster_list.add(uid)
    save(list(booster_list))
    await interaction.response.send_message("✅ Adicionados", ephemeral=True)

@tree.command(name="forcarverificacao", description="Força verificação agora", guild=GUILD_OBJ)
async def forcar(interaction: discord.Interaction):
    await verificar()
    await interaction.response.send_message("🔄 Verificação executada", ephemeral=True)

# ================= READY =================
@bot.event
async def on_ready():
    print(f"🤖 Online como {bot.user}")
    await tree.sync(guild=GUILD_OBJ)  # só guild, sem global

    if not verificar.is_running():
        verificar.start()

    print("✅ Sistema 2x Booster ativo")

bot.run(TOKEN)
