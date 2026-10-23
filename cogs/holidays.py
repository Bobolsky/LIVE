import asyncio
import logging
from datetime import datetime

import discord
from dateutil.easter import easter
from discord.ext import commands, tasks

from db import db
from settings import ROME_TZ, WELCOME_CHANNEL_ID

HOLIDAYS = {
    (10, 31): "Buon Halloween! 👻 🎃 ❤️",
    (12, 24): "Buona Vigilia di Natale! ❄️ 🎁 ❤️",
    (12, 25): "Buon Natale! 🎄 🎅 ❤️",
    (1, 1): "Buon Anno! 🥂 ✨ ❤️",
    (8, 15): "Buon Ferragosto! 🔥 🌊 ❤️",
    (1, 6): "Buona Befana! 👵 🍫 ❤️",
}


def holiday_message(day):
    if day == easter(day.year):
        return "Buona Pasqua! 🕊️ 🐣 ❤️"
    return HOLIDAYS.get((day.month, day.day))


class Holidays(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state_ref = db.collection('bot_state').document('holiday_greetings')

    async def cog_load(self):
        self.check_holidays.start()

    async def cog_unload(self):
        self.check_holidays.cancel()

    async def send_greeting(self):
        today = datetime.now(ROME_TZ).date()
        message = holiday_message(today)
        if message is None:
            return

        state = await asyncio.to_thread(self.state_ref.get)
        if (state.to_dict() or {}).get("last_sent") == today.isoformat():
            return
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if channel is None:
            logging.warning("[Feste] Canale degli auguri non trovato.")
            return

        await channel.send(message, allowed_mentions=discord.AllowedMentions.none())
        await asyncio.to_thread(self.state_ref.set, {"last_sent": today.isoformat()})

    # Controlla anche all'avvio: recupera gli auguri del giorno se il bot era spento.
    @tasks.loop(minutes=1)
    async def check_holidays(self):
        try:
            await self.send_greeting()
        except Exception:
            # Un errore temporaneo non deve disabilitare gli auguri futuri.
            logging.exception("[Feste] Errore durante l'invio degli auguri.")

    @check_holidays.before_loop
    async def before_check_holidays(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Holidays(bot))
