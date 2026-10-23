import random
import discord
from discord.ext import commands, tasks
from data.status import games_list, watching_list, listening_list


class Status(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.change_status.start()

    async def cog_unload(self):
        self.change_status.cancel()

    # Task loop per cambiare lo status del bot
    @tasks.loop(hours=1)
    async def change_status(self):
        # Seleziona una lista casuale e un elemento casuale dalla lista
        random_list = random.choice([games_list, watching_list, listening_list])
        random_command = random.choice(random_list)

        # Controlla quale lista è stata scelta e cambia l'intervallo
        if random_list == listening_list:
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=random_command))
            self.change_status.change_interval(minutes=30)
        elif random_list == watching_list:
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=random_command))
            self.change_status.change_interval(hours=1)
        else:
            await self.bot.change_presence(activity=discord.Game(name=random_command))  # Sta giocando
            self.change_status.change_interval(hours=1)

    @change_status.before_loop
    async def before_change_status(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Status(bot))
