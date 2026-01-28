import discord
from discord.ext import commands, tasks
from discord import app_commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1316931391430197268
ROLE_2X_ID = 1317717808737419295

LOG_VERIFICACAO_ID = 1465942893209583838
LOG_REMOVIDO_ID = 1465946692191785041

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ======================
# FUNÇÃO PRINCIPAL
# ======================
async def verificar_2x_boosters():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    role_2x = guild.get_role(ROLE_2X_ID)
    log_channel = guild.get_channel(LOG_VERIFICACAO_ID)

    if not role_2x or not log_channel:
        return

    for member in guild.members:
        # booster com 2 meses ou mais
        if member.premium_since:
            if role_2x not in member.roles:
                await member.add_roles(role_2x)
                await log_channel.send(
                    f"""```VERIFICAÇÃO DE 2X BOOSTERS

<{member.id}> recebeu seu cargo de 2x booster!
```"""
                )


# ======================
# TASK 5 EM 5 MINUTOS
# ======================
@tasks.loop(minutes=5)
async def verificar_loop():
    await verificar_2x_boosters()


# ======================
# EVENTOS
# ======================
@bot.event
async def on_ready():
    print(f"🤖 Online como {bot.user}")

    await tree.sync(guild=discord.Object(id=GUILD_ID))

    # VERIFICA IMEDIATAMENTE
    await verificar_2x_boosters()

    # INICIA LOOP
    if not verificar_loop.is_running():
        verificar_loop.start()

    print("✅ Verificação iniciada")


@bot.event
async def on_member_update(before, after):
    guild = after.guild
    role_2x = guild.get_role(ROLE_2X_ID)

    # GANHOU BOOST
    if before.premium_since is None and after.premium_since:
        if role_2x not in after.roles:
            await after.add_roles(role_2x)

            log_channel = guild.get_channel(LOG_VERIFICACAO_ID)
            if log_channel:
                await log_channel.send(
                    f"""```DEU SEU 2X BOOSTERS

<{after.id}> recebeu seu cargo de 2x booster!
```"""
                )

    # REMOVEU BOOST
    if before.premium_since and after.premium_since is None:
        if role_2x in after.roles:
            await after.remove_roles(role_2x)

            log_channel = guild.get_channel(LOG_REMOVIDO_ID)
            if log_channel:
                await log_channel.send(
                    f"""```2X BOOSTER REMOVIDO

<{after.id}> teve seu cargo de 2x booster removido por retirar seu boost!
```"""
                )


# ======================
# SLASH COMMAND
# ======================
@tree.command(
    name="forcarverificacao",
    description="Força a verificação de 2x boosters",
    guild=discord.Object(id=GUILD_ID)
)
async def forcarverificacao(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message(
            "❌ Sem permissão", ephemeral=True
        )

    await verificar_2x_boosters()
    await interaction.response.send_message(
        "✅ Verificação executada com sucesso", ephemeral=True
    )


# ======================
# START
# ======================
bot.run(TOKEN)
