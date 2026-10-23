import asyncio
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from db import db
from settings import MEDAL_CHANNEL_ID
from cogs.medal_api import MedalAPIError, latest_clips, resolve_medal_user_id

CHECK_INTERVAL_HOURS = 3  # controlli rari, per non sovraccaricare l'API di Medal
DELAY_BETWEEN_USERS = 5  # secondi di pausa tra un utente e l'altro
MAX_SEEN_IDS = 50  # clip già viste ricordate per ogni utente


class Medal(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Iscrizioni salvate su Firestore: un documento per utente Discord
        self.subscriptions_ref = db.collection('medal_subscriptions')
        self.subscriptions = {}  # discord_user_id -> dati dell'iscrizione

    async def cog_load(self):
        docs = await asyncio.to_thread(lambda: list(self.subscriptions_ref.stream()))
        self.subscriptions = {int(doc.id): doc.to_dict() for doc in docs}
        print(f"[Medal] Iscrizioni caricate: {len(self.subscriptions)}")
        self.check_new_clips.start()

    async def cog_unload(self):
        self.check_new_clips.cancel()

    @app_commands.command(name="livemedal", description="Iscriviti a LiveMedal per publicare automatimcanete le tue clip")
    @app_commands.describe(
        link_clip="Il link di una tua clip di Medal (va bene anche il tuo ID utente di Medal)"
    )
    @app_commands.guild_only()
    async def medal(self, interaction: discord.Interaction, link_clip: str):
        await interaction.response.defer(ephemeral=True)

        try:
            async with aiohttp.ClientSession() as session:
                medal_user_id = await resolve_medal_user_id(session, link_clip)
                if medal_user_id is None:
                    await interaction.followup.send(
                        "Incolla il link completo di una tua clip pubblica di Medal, "
                        "il link medal.tv/users/<id> oppure il tuo ID numerico.", ephemeral=True
                    )
                    return
                clips = await latest_clips(session, medal_user_id)
        except MedalAPIError as error:
            await interaction.followup.send(str(error), ephemeral=True)
            return

        # Le clip già presenti vengono segnate come viste: verranno pubblicate solo quelle nuove
        subscription = {
            "medal_user_id": medal_user_id,
            "seen_ids": [clip["contentId"] for clip in clips],
        }
        await asyncio.to_thread(self.subscriptions_ref.document(str(interaction.user.id)).set, subscription)
        self.subscriptions[interaction.user.id] = subscription

        await interaction.followup.send(
            f"Fatto! Da adesso le tue nuove clip di Medal verranno pubblicate in <#{MEDAL_CHANNEL_ID}>. "
            "Usa /livemedalstop per disattivare.",
            ephemeral=True
        )

    @app_commands.command(name="livemedalstop", description="Disiscriviti da LiveMedal per non pubblicare automaticamente le tue clip")
    async def medalstop(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id not in self.subscriptions:
            await interaction.followup.send("Non hai attivato la pubblicazione delle clip di Medal.", ephemeral=True)
            return
        await asyncio.to_thread(self.subscriptions_ref.document(str(interaction.user.id)).delete)
        self.subscriptions.pop(interaction.user.id, None)
        await interaction.followup.send("Le tue clip di Medal non verranno più pubblicate.", ephemeral=True)

    @tasks.loop(hours=CHECK_INTERVAL_HOURS)
    async def check_new_clips(self):
        channel = self.bot.get_channel(MEDAL_CHANNEL_ID)
        if channel is None:
            print("[Medal] Canale delle clip non trovato.")
            return

        async with aiohttp.ClientSession() as session:
            for discord_user_id, subscription in list(self.subscriptions.items()):
                try:
                    await self.post_new_clips(session, channel, discord_user_id, subscription)
                except Exception as e:
                    # Un errore su un utente non deve bloccare gli altri
                    print(f"[Medal] Errore per l'utente {discord_user_id}: {e!r}")
                await asyncio.sleep(DELAY_BETWEEN_USERS)

    async def post_new_clips(self, session, channel, discord_user_id: int, subscription: dict):
        clips = await latest_clips(session, subscription["medal_user_id"])
        if not clips:
            return

        seen = ["cid" + str(clip_id).removeprefix("cid") for clip_id in subscription.get("seen_ids", [])]
        new_clips = [clip for clip in clips if clip["contentId"] not in seen]
        if not new_clips:
            return

        # Dalla più vecchia alla più nuova, così nel canale restano in ordine
        for clip in reversed(new_clips):
            url = clip.get("directClipUrl") or clip.get("contentUrl")
            if url:
                message = await channel.send(
                    url,
                    allowed_mentions=discord.AllowedMentions.none()
                )
                # L'autore resta disponibile per /clip senza una menzione visibile.
                await asyncio.to_thread(
                    db.collection('medal_clip_authors').document(str(message.id)).set,
                    {"author_id": discord_user_id}
                )
                clips_cog = self.bot.get_cog("Clips")
                if clips_cog is not None and clips_cog.loaded:
                    clips_cog.add_clip(message, author_id=discord_user_id)

        # Si ricordano solo le ultime clip viste, il resto non serve più
        subscription["seen_ids"] = ([clip["contentId"] for clip in new_clips] + seen)[:MAX_SEEN_IDS]
        await asyncio.to_thread(
            self.subscriptions_ref.document(str(discord_user_id)).update, {"seen_ids": subscription["seen_ids"]}
        )

    @check_new_clips.before_loop
    async def before_check_new_clips(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Medal(bot))
