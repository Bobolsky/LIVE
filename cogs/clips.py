import asyncio
import random
import re
import discord
from discord import app_commands
from discord.ext import commands
from db import db
from settings import CLIPS_CHANNEL_ID, GUILD_ID


# Solo i link di Medal (https://medal.tv/...), niente allegati o altri link
MEDAL_URL = re.compile(r"https?://(?:www\.)?medal\.tv/\S+", re.IGNORECASE)


def is_clip(message: discord.Message):
    return bool(MEDAL_URL.search(message.content))


class Clips(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel = None
        # Si salvano solo gli ID dei messaggi; il link viene letto al momento del comando
        # così una clip cancellata nel frattempo viene scartata
        self.clips_by_author = {}  # author_id -> [message_id]
        self.author_of = {}  # message_id -> author_id
        self.seen = set()  # clip già uscite nel giro corrente
        # Le clip uscite sono salvate su Firestore, così un riavvio non fa ricominciare il giro
        self.state_ref = db.collection('bot_state').document('clips_seen')
        self.loaded = False

    async def cog_load(self):
        self.load_task = asyncio.create_task(self.load_clips())

    async def cog_unload(self):
        self.load_task.cancel()

    def add_clip(self, message: discord.Message):
        # Le clip pubblicate dal bot con /medal appartengono all'utente menzionato nel messaggio
        author_id = message.author.id
        if message.author.id == self.bot.user.id and message.mentions:
            author_id = message.mentions[0].id
        self.clips_by_author.setdefault(author_id, []).append(message.id)
        self.author_of[message.id] = author_id

    def remove_clip(self, message_id: int):
        author_id = self.author_of.pop(message_id, None)
        if author_id is None:
            return
        self.clips_by_author[author_id].remove(message_id)
        if not self.clips_by_author[author_id]:
            del self.clips_by_author[author_id]
        self.seen.discard(message_id)

    async def load_clips(self):
        await self.bot.wait_until_ready()

        if CLIPS_CHANNEL_ID:
            self.channel = self.bot.get_channel(CLIPS_CHANNEL_ID)
        else:
            guild = self.bot.get_guild(GUILD_ID)
            self.channel = discord.utils.find(lambda c: "clips" in c.name.lower(), guild.text_channels) if guild else None

        if self.channel is None:
            print("Canale Clips non trovato.")
            return

        async for message in self.channel.history(limit=None):
            if is_clip(message):
                self.add_clip(message)
        saved = await asyncio.to_thread(self.state_ref.get)
        # Si tengono solo le clip ancora presenti nel canale
        self.seen = set((saved.to_dict() or {}).get("ids", [])) & set(self.author_of)
        self.loaded = True
        print(f"Clip già uscite nel giro corrente: {len(self.seen)}")
        print(f"Caricate {len(self.author_of)} clip di {len(self.clips_by_author)} utenti da #{self.channel.name}")

    # Sceglie prima un utente (tutti con la stessa probabilità), poi una sua clip non ancora uscita.
    # Quando tutte le clip sono uscite il giro ricomincia. Restituisce (message_id, nuovo_giro)
    def pick_clip(self):
        new_round = False
        remaining = {
            author_id: [m for m in ids if m not in self.seen]
            for author_id, ids in self.clips_by_author.items()
        }
        remaining = {author_id: ids for author_id, ids in remaining.items() if ids}

        if not remaining:
            if not self.clips_by_author:
                return None, False
            self.seen.clear()
            remaining = self.clips_by_author
            new_round = True

        author_id = random.choice(list(remaining))
        message_id = random.choice(remaining[author_id])
        self.seen.add(message_id)
        return message_id, new_round

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self.loaded and message.channel.id == self.channel.id and is_clip(message):
            self.add_clip(message)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        self.remove_clip(payload.message_id)

    @app_commands.command(name="clip", description="Rivivi un momento indimenticabile attraverso con una clip")
    async def clip(self, interaction: discord.Interaction):
        if not self.loaded:
            await interaction.response.send_message("Sto ancora caricando le clip, riprova tra poco.", ephemeral=True)
            return

        await interaction.response.defer()

        while True:
            message_id, new_round = self.pick_clip()
            if message_id is None:
                await interaction.followup.send("Non ci sono clip nel canale.")
                return
            try:
                message = await self.channel.fetch_message(message_id)
                break
            except discord.NotFound:
                self.remove_clip(message_id)

        link = MEDAL_URL.search(message.content).group(0)
        text = link
        if new_round:
            text += "\n-# Sono uscite tutte le clip: il giro ricomincia!"
        await interaction.followup.send(text)
        await asyncio.to_thread(self.state_ref.set, {"ids": list(self.seen)})


async def setup(bot: commands.Bot):
    await bot.add_cog(Clips(bot))
