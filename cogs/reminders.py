import asyncio
from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands


async def schedule_reminder(interaction: discord.Interaction, delay, message, mentions=None):
    await asyncio.sleep(delay)

    if not mentions:
        await interaction.channel.send(f":bell: **{message}** :bell:")
        return

    # Prepara la lista delle menzioni
    mentions_to_send = []
    for mention in mentions.split():
        if mention.startswith("<@&"):  # Riconosce un ruolo
            role = discord.utils.get(interaction.guild.roles, id=int(mention[3:-1]))
            if role:
                mentions_to_send.append(role.mention)
        elif mention.startswith("<@"):  # Riconosce un membro
            member = await interaction.guild.fetch_member(int(mention[2:-1]))
            if member:
                mentions_to_send.append(member.mention)

    mention_string = " ".join(mentions_to_send)
    await interaction.channel.send(f":bell: {mention_string} **{message}** :bell:")


class Reminders(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='remind', description='Imposta un promemoria')
    async def remind(self, interaction: discord.Interaction,
                     time: str,
                     date: str = None,
                     mentions: str = None,
                     message: str = ''):
        try:
            # Usa la data odierna se non viene specificata una data
            if date is None:
                date = datetime.now().strftime("%d/%m/%Y")
            else:
                date = datetime.strptime(date, "%d/%m/%Y").strftime("%d/%m/%Y")

            # Se viene specificata solo l'ora senza i minuti
            if ":" not in time:
                time += ":00"

            remind_time = datetime.strptime(f"{date} {time}", "%d/%m/%Y %H:%M")
            current_time = datetime.now()

            if remind_time < current_time:
                await interaction.response.send_message("Non puoi impostare un promemoria per un evento passato!", ephemeral=True)
                return

            delay = (remind_time - current_time).total_seconds()
            await interaction.response.send_message(f"Promemoria impostato per {remind_time.strftime('%d/%m/%Y %H:%M')}!", ephemeral=True)

            asyncio.create_task(schedule_reminder(interaction, delay, message, mentions=mentions))

        except ValueError:
            await interaction.response.send_message("Formato della data o dell'ora non valido. Usa il formato DD/MM/YYYY HH:MM", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Reminders(bot))
