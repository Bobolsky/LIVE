import logging
import os
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ["DISCORD_TOKEN"]

EXTENSIONS = [
    "cogs.status",
    "cogs.quotes",
    "cogs.birthdays",
    "cogs.reminders",
    "cogs.tickets",
    "cogs.sfida",
    "cogs.welcome",
    "cogs.medal",
    "cogs.lol_patches",
    "cogs.clips",
]


class LiveBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)

    # Eseguito una sola volta all'avvio (a differenza di on_ready, che scatta a ogni riconnessione)
    async def setup_hook(self):
        for extension in EXTENSIONS:
            await self.load_extension(extension)
        self.tree.error(self.on_app_command_error)
        synced = await self.tree.sync()
        print(f"Synced {len(synced)} commands")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        logging.error("Errore nel comando %s", interaction.command.name if interaction.command else "?", exc_info=error)
        message = "Si è verificato un errore, riprova tra poco."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def on_ready(self):
        print(f"Bot connesso come {self.user}")


logging.basicConfig(level=logging.INFO)

bot = LiveBot()
bot.run(TOKEN)
