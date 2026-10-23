import asyncio
import discord
from discord import app_commands
from discord.ext import commands


class Sfida(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sfida_in_corso = None

    @app_commands.command(name="sfida", description="Sfida il tuo peggior nemico a QUANTO TE LA RISCHI")
    async def sfida(self, interaction: discord.Interaction, utente_sfidato: discord.Member):
        if self.sfida_in_corso:
            await interaction.response.send_message("C'è già una sfida in corso. Attendi che finisca.", ephemeral=True)
            return

        if interaction.user.id == utente_sfidato.id:
            await interaction.response.send_message(f"{utente_sfidato.mention} è così confuso da sfidarsi da solo!")
            return

        self.sfida_in_corso = {
            "sfidante": interaction.user,
            "sfidato": utente_sfidato,
            "stato": "in_attesa"
        }

        await interaction.response.send_message(f"**{interaction.user.mention} ha sfidato {utente_sfidato.mention} a QUANTO TE LA RISCHI. {utente_sfidato.mention} di' un numero:**")

    @app_commands.command(name="rifiuta", description="Rifiuta la sfida a QUANTO TE LA RISCHI")
    async def rifiuta(self, interaction: discord.Interaction):
        if self.sfida_in_corso and interaction.user == self.sfida_in_corso["sfidato"]:
            await interaction.response.send_message("Ti sei rifiutato di giocare, ti aspettiamo in https://discord.com/channels/687431352626184202/1283478923925262357 per chiarimenti, se necessari.")
            self.sfida_in_corso = None
        elif self.sfida_in_corso:
            await interaction.response.send_message("Solo lo sfidato può rifiutare la sfida.", ephemeral=True)
        else:
            await interaction.response.send_message("Non c'è nessuna sfida in corso da rifiutare.", ephemeral=True)

    @app_commands.command(name="ritira", description="Ritirare la sfida a QUANTO TE LA RISCHI")
    async def ritira(self, interaction: discord.Interaction):
        if self.sfida_in_corso and interaction.user == self.sfida_in_corso["sfidante"]:
            await interaction.response.send_message(f"{interaction.user.mention} ha ritirato la sfida.")
            self.sfida_in_corso = None
        elif self.sfida_in_corso:
            await interaction.response.send_message("Solo lo sfidante può ritirare la sfida.", ephemeral=True)
        else:
            await interaction.response.send_message("Non c'è nessuna sfida in corso da ritirare.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        sfida = self.sfida_in_corso
        if "rifiuta" in message.content:
            return
        if not (sfida and message.author.id == sfida["sfidato"].id and sfida["stato"] == "in_attesa"):
            return

        try:
            numero = int(message.content)
        except ValueError:
            await message.channel.send(f"{message.author.mention} Ma non stai giocando? Di' un numero oppure utilizza il comando */rifiuta*.")
            return

        await message.channel.send(f"**OFFICIAL da 1 a {numero}**")
        sfida["stato"] = "in_corso"

        # Contatta sfidante e sfidato in privato
        await sfida["sfidante"].send(f"Dimmi un numero da 1 a {numero}")
        await sfida["sfidato"].send(f"Dimmi un numero da 1 a {numero}")

        def check(m):
            return m.author in [sfida["sfidante"], sfida["sfidato"]] and m.guild is None

        # Attendi le risposte private
        num_sfidante = num_sfidato = None
        for _ in range(2):
            try:
                risposta = await self.bot.wait_for('message', check=check, timeout=60.0)
                numero_scelto = int(risposta.content)
                if 1 <= numero_scelto <= numero:
                    if risposta.author == sfida["sfidante"]:
                        num_sfidante = numero_scelto
                    else:
                        num_sfidato = numero_scelto
                else:
                    await risposta.author.send("Numero non valido. Sfida annullata.")
                    self.sfida_in_corso = None
                    return
            except asyncio.TimeoutError:
                await message.channel.send("Tempo scaduto. Sfida annullata.")
                self.sfida_in_corso = None
                return
            except ValueError:
                await risposta.author.send("Input non valido. Sfida annullata.")
                self.sfida_in_corso = None
                return

        # Controlla se i numeri coincidono
        await asyncio.sleep(10)
        await message.channel.send(
            f"*{sfida['sfidato'].mention} ha detto: {num_sfidato}*\n"
            f"*{sfida['sfidante'].mention} ha detto: {num_sfidante}*\n\n"
            f"{sfida['sfidato'].mention} {'**è stato beccato!**' if num_sfidante == num_sfidato else '**è salvo!**'}"
        )

        # Resetta la sfida
        self.sfida_in_corso = None


async def setup(bot: commands.Bot):
    await bot.add_cog(Sfida(bot))
