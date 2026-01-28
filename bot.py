import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
from datetime import datetime

# ======================
# CONFIG
# ======================
TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1316931391430197268
ROLE_2X = 1317717808737419295

LOG_VERIFY = 1465942893209583838
LOG_REMOVE = 1465946692191785041

DATA_FILE = "booster_list.json"

# ======================
# INTENTS
# ======================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
GUILD_OBJ = discord.Object(id=GUILD_ID)

# ======================
# DATA
# ======================
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

booster_list = set(load_data())

# ======================
# UTILS
# ======================
def now():
    return datetime.now().strftime("%d/%m/%Y • %H:%M:%S")

async def send_embed_log(channel_id, embed):
    guild = bot.get_guild(GUILD_ID)
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed)

# ======================
# VERIFICAÇÃO AUTOMÁTICA
# ======================
@tasks.loop(minutes=5)
async def verificar_2x():
    guild = bot.get_guild(GUILD_ID)
    role = guild.get_role(ROLE_2X)

    for uid in list(booster_list):
        member = guild.get_member(uid)

        if not member:
            booster_list.discard(uid)
            save_data(list(booster_list))
            continue

        # Remove se não estiver mais boostando
        if not member.premium_since:
            booster_list.discard(uid)
            save_data(list(booster_list))

            if role in member.roles:
                await member.remove_roles(role)

            embed = discord.Embed(
                title="❌ 2X BOOSTER REMOVIDO",
                color=0xE74C3C,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Membro", value=f"{member.mention}\nID: `{uid}`", inline=False)
            embed.add_field(name="Motivo", value="Removeu o boost do servidor", inline=False)
            embed.set_footer(text="Sistema Automático 2x Booster")

            await send_embed_log(LOG_REMOVE, embed)

        # Dá cargo se ainda boosta
        else:
            if role not in member.roles:
                await member.add_roles(role)

                embed = discord.Embed(
                    title="✅ VERIFICAÇÃO 2X BOOSTER",
                    color=0x2ECC71,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Membro", value=f"{member.mention}\nID: `{uid}`", inline=False)
                embed.add_field(name="Ação", value="Cargo de 2x Booster concedido", inline=False)
                embed.set_footer(text="Verificação automática (5 min)")

                await send_embed_log(LOG_VERIFY, embed)

# ======================
# BOOST EM TEMPO REAL
# ======================
@bot.event
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since:
        if after.id in booster_list:
            role = after.guild.get_role(ROLE_2X)
            await after.add_roles(role)

            embed = discord.Embed(
                title="🚀 DEU BOOST (TEMPO REAL)",
                color=0x9B59B6,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Membro", value=f"{after.mention}\nID: `{after.id}`", inline=False)
            embed.add_field(name="Ação", value="Cargo 2x Booster concedido imediatamente", inline=False)
            embed.set_footer(text="Evento em tempo real")

            await send_embed_log(LOG_VERIFY, embed)

# ======================
# DROPDOWN
# ======================
class RemoveDropdown(discord.ui.Select):
    def __init__(self, members):
        options = [
            discord.SelectOption(
                label=f"{member.display_name}",
                value=str(member.id),
                description=f"ID: {member.id}"
            )
            for member in members
        ]

        super().__init__(
            placeholder="Remover membro da lista 2x Booster",
            min_values=1,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Sem permissão", ephemeral=True)

        guild = interaction.guild
        role = guild.get_role(ROLE_2X)

        removed = []
        for uid in self.values:
            uid = int(uid)
            booster_list.discard(uid)
            member = guild.get_member(uid)

            if member and role in member.roles:
                await member.remove_roles(role)

            removed.append(f"<@{uid}>")

        save_data(list(booster_list))

        await interaction.response.send_message(
            "❌ Removidos da lista:\n" + "\n".join(removed),
            ephemeral=True
        )

class RemoveView(discord.ui.View):
    def __init__(self, members):
        super().__init__(timeout=120)
        self.add_item(RemoveDropdown(members))

# ======================
# SLASH COMMANDS
# ======================
@tree.command(name="addmemberlist", description="Adicionar membros à lista 2x", guild=GUILD_OBJ)
async def addmemberlist(interaction: discord.Interaction, membros: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Sem permissão", ephemeral=True)

    ids = [int(m.replace("<@", "").replace(">", "").strip()) for m in membros.split(",")]
    for uid in ids:
        booster_list.add(uid)

    save_data(list(booster_list))
    await interaction.response.send_message("✅ Membros adicionados à lista", ephemeral=True)

@tree.command(name="checkboosterlist", description="Ver lista 2x Boosters", guild=GUILD_OBJ)
async def checkboosterlist(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Sem permissão", ephemeral=True)

    if not booster_list:
        return await interaction.response.send_message("📭 Lista vazia", ephemeral=True)

    members = [interaction.guild.get_member(uid) for uid in booster_list if interaction.guild.get_member(uid)]

    embed = discord.Embed(
        title="✨ | Lista 2x Boosters",
        color=0x5865F2
    )

    for m in members:
        embed.add_field(
            name="Membro",
            value=f"{m.mention} ︱ ID: `{m.id}`",
            inline=False
        )

    embed.set_footer(text=f"Total: {len(members)} membros")

    await interaction.response.send_message(
        embed=embed,
        view=RemoveView(members),
        ephemeral=True
    )

@tree.command(name="forcarverificacao", description="Força verificação agora", guild=GUILD_OBJ)
async def forcarverificacao(interaction: discord.Interaction):
    await verificar_2x()
    await interaction.response.send_message("🔄 Verificação executada", ephemeral=True)

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
