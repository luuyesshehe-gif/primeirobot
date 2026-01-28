import discord
from discord.ext import commands
from discord import app_commands
import os
import json

# ======================
# CONFIGURAÇÕES
# ======================
TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1316931391430197268
GUILD_OBJ = discord.Object(id=GUILD_ID)

DATA_FILE = "booster_list.json"

# ======================
# INTENTS
# ======================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ======================
# JSON HELPERS
# ======================
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

booster_list = load_data()

# ======================
# VIEW (DROPDOWN)
# ======================
class RemoveDropdown(discord.ui.Select):
    def __init__(self, members):
        options = [
            discord.SelectOption(
                label=f"{m['name']}",
                description=f"ID: {m['id']}",
                value=str(m['id'])
            )
            for m in members
        ]

        super().__init__(
            placeholder="Remover membro da lista",
            min_values=1,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        global booster_list
        removed = []

        for value in self.values:
            booster_list = [m for m in booster_list if str(m["id"]) != value]
            removed.append(f"<@{value}>")

        save_data(booster_list)

        await interaction.response.send_message(
            f"❌ Removidos da lista:\n" + "\n".join(removed),
            ephemeral=True
        )

class RemoveView(discord.ui.View):
    def __init__(self, members):
        super().__init__(timeout=120)
        self.add_item(RemoveDropdown(members))

# ======================
# EVENTO
# ======================
@bot.event
async def on_ready():
    await tree.sync(guild=GUILD_OBJ)
    print(f"🤖 Bot online como {bot.user}")
    print("✅ Slash commands sincronizados")

# ======================
# SLASH COMMANDS
# ======================
@tree.command(name="addmemberlist", description="Adiciona membros à lista 2x booster", guild=GUILD_OBJ)
async def addmemberlist(interaction: discord.Interaction, membros: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    added = []
    for m in membros.replace(" ", "").split(","):
        user_id = int(m.replace("<@", "").replace(">", ""))

        if any(x["id"] == user_id for x in booster_list):
            continue

        user = interaction.guild.get_member(user_id)
        booster_list.append({
            "id": user_id,
            "name": user.display_name if user else str(user_id)
        })
        added.append(f"<@{user_id}>")

    save_data(booster_list)

    await interaction.response.send_message(
        "✅ Adicionados:\n" + ("\n".join(added) if added else "Nenhum"),
        ephemeral=True
    )

@tree.command(name="removememberlist", description="Remove membros da lista 2x booster", guild=GUILD_OBJ)
async def removememberlist(interaction: discord.Interaction, membros: str):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    removed = []
    global booster_list

    for m in membros.replace(" ", "").split(","):
        user_id = int(m.replace("<@", "").replace(">", ""))
        if any(x["id"] == user_id for x in booster_list):
            booster_list = [x for x in booster_list if x["id"] != user_id]
            removed.append(f"<@{user_id}>")

    save_data(booster_list)

    await interaction.response.send_message(
        "❌ Removidos:\n" + ("\n".join(removed) if removed else "Nenhum"),
        ephemeral=True
    )

@tree.command(name="checkboosterlist", description="Mostra a lista de 2x boosters", guild=GUILD_OBJ)
async def checkboosterlist(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Sem permissão", ephemeral=True)

    if not booster_list:
        return await interaction.response.send_message("📭 Lista vazia", ephemeral=True)

    embed = discord.Embed(
        title="✨ | Lista 2x Boosters",
        color=0x9b59b6
    )

    for m in booster_list:
        embed.add_field(
            name="Member",
            value=f"<@{m['id']}> ︱ ID: `{m['id']}`",
            inline=False
        )

    view = RemoveView(booster_list)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ======================
# START
# ======================
bot.run(TOKEN)
