from datetime import datetime, time
from io import StringIO
import discord
from discord import app_commands
from discord.ext import commands, tasks
from db import db
from settings import ROME_TZ, GUILD_ID, WELCOME_CHANNEL_ID


def normalizza_data(giorno: int, mese: int) -> str:
    # Restituisce la data nel formato DD/MM, con due cifre per giorno e mese
    return f"{giorno:02d}/{mese:02d}"


class Birthdays(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.check_birthdays.start()

    async def cog_unload(self):
        self.check_birthdays.cancel()

    @app_commands.command(name="listacompleanni", description="Restituisci un file TXT con la lista dei compleanni")
    async def lista_compleanni(self, interaction: discord.Interaction):
        compleanni_io = StringIO()
        compleanni_io.write("Lista dei Compleanni:\n\n")

        for doc in db.collection("compleanni").stream():
            data = doc.to_dict()
            # Trova il membro nel server usando l'ID
            member = interaction.guild.get_member(data["user_id"])
            member_name = member.display_name if member else "Utente non trovato"
            compleanni_io.write(f"Nome Utente: {member_name}, Compleanno: {data['birthday']}\n")

        compleanni_io.seek(0)
        await interaction.response.send_message(
            file=discord.File(fp=compleanni_io, filename="compleanni.txt"),
            content="Ecco la lista dei compleanni:",
            ephemeral=True
        )

    @app_commands.command(name="compleanno", description="Aggiungi il compleanno del tuo migliore amico")
    async def compleanno(self, interaction: discord.Interaction, user: discord.Member, giorno: int, mese: int):
        try:
            # Controlla che il giorno e il mese siano validi
            datetime.strptime(f"{giorno}/{mese}", "%d/%m")
            birthday = normalizza_data(giorno, mese)

            db.collection("compleanni").document(str(user.id)).set({
                "user_id": user.id,
                "birthday": birthday
            })

            await interaction.response.send_message(f"Compleanno salvato con successo per il {giorno}/{mese}!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Formato della data non valido. Usa: /compleanno giorno mese", ephemeral=True)

    @tasks.loop(time=time(hour=0, minute=0, second=10, tzinfo=ROME_TZ))  # Ogni giorno a mezzanotte
    async def check_birthdays(self):
        today = datetime.today().strftime("%d/%m")

        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            print("Server non trovato.")
            return

        for doc in db.collection("compleanni").stream():
            data = doc.to_dict()
            if data["birthday"] == today:
                user = await guild.fetch_member(data["user_id"])
                channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
                if channel:
                    await channel.send(f"Buon compleanno {user.mention}! 🥳 🎉 ❤ 🎂 🧁")

    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Birthdays(bot))
