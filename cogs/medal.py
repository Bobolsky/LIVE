import asyncio
import os
import re
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from db import db
from settings import MEDAL_CHANNEL_ID

MEDAL_API_URL = "https://developers.medal.tv/v1/latest"
# Dati di una singola clip, tra cui l'autore (poster.userId): serve a ricavare l'ID dal link di una clip
MEDAL_CONTENT_URL = "https://medal.tv/api/content/{clip_id}"
CLIP_LINK = re.compile(r"medal\.tv/(?:[^\s]*/)?clips?/([A-Za-z0-9_-]+)", re.IGNORECASE)
PROFILE_LINK = re.compile(r"medal\.tv/users/(\d+)", re.IGNORECASE)
# Chiave del bot (dal .env), usata per chi non inserisce una propria chiave
DEFAULT_API_KEY = os.environ.get("MEDAL_API_KEY")
CHECK_INTERVAL_HOURS = 3  # controlli rari, per non sovraccaricare l'API di Medal
DELAY_BETWEEN_USERS = 5  # secondi di pausa tra un utente e l'altro
CLIPS_PER_CHECK = 10  # clip più recenti lette a ogni controllo
MAX_SEEN_IDS = 50  # clip già viste ricordate per ogni utente


async def latest_clips(session: aiohttp.ClientSession, medal_user_id: str, api_key: str):
    # Restituisce le clip più recenti dell'utente (dalla più nuova), oppure None se la richiesta fallisce
    if not api_key:
        print("[Medal] Nessuna chiave API: imposta MEDAL_API_KEY nel .env")
        return None
    params = {"userId": medal_user_id, "limit": CLIPS_PER_CHECK}
    async with session.get(MEDAL_API_URL, params=params, headers={"Authorization": api_key}) as response:
        if response.status != 200:
            print(f"[Medal] Errore durante la richiesta per l'utente {medal_user_id}: {response.status}")
            return None
        try:
            data = await response.json(content_type=None)
        except ValueError:
            return None
    if not isinstance(data, dict) or not isinstance(data.get("contentObjects"), list):
        return None
    return [clip for clip in data["contentObjects"] if clip.get("contentId")]


async def resolve_medal_user_id(session: aiohttp.ClientSession, text: str):
    # Accetta l'ID numerico, il link del profilo (medal.tv/users/<id>) o il link di una clip dell'utente
    text = text.strip()
    if text.isdigit():
        return text
    if match := PROFILE_LINK.search(text):
        return match.group(1)
    match = CLIP_LINK.search(text)
    if not match:
        return None

    url = MEDAL_CONTENT_URL.format(clip_id=match.group(1))
    async with session.get(url, headers={"Accept": "application/json"}) as response:
        if response.status != 200:
            print(f"[Medal] Errore durante la lettura della clip {match.group(1)}: {response.status}")
            return None
        try:
            data = await response.json(content_type=None)
        except ValueError:
            return None
    user_id = str(((data or {}).get("poster") or {}).get("userId") or "") if isinstance(data, dict) else ""
    return user_id if user_id.isdigit() else None


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

    @app_commands.command(name="medal", description="Pubblica automaticamente le tue nuove clip di Medal nel canale delle clip")
    @app_commands.describe(
        link_clip="Il link di una tua clip di Medal (va bene anche il tuo ID utente di Medal)",
        api_key="La tua chiave API pubblica di Medal (pub_...), facoltativa"
    )
    @app_commands.guild_only()
    async def medal(self, interaction: discord.Interaction, link_clip: str, api_key: str = None):
        await interaction.response.defer(ephemeral=True)

        api_key = (api_key or "").strip() or None
        async with aiohttp.ClientSession() as session:
            medal_user_id = await resolve_medal_user_id(session, link_clip)
            if medal_user_id is None:
                await interaction.followup.send(
                    "Non riesco a capire chi sei su Medal: incolla il link di una tua clip "
                    "(Condividi > Copia link su Medal).",
                    ephemeral=True
                )
                return
            clips = await latest_clips(session, medal_user_id, api_key or DEFAULT_API_KEY)
        if clips is None:
            await interaction.followup.send("Non riesco a leggere le clip da Medal: controlla l'ID utente e la chiave API.", ephemeral=True)
            return

        # Le clip già presenti vengono segnate come viste: verranno pubblicate solo quelle nuove
        subscription = {
            "medal_user_id": medal_user_id,
            "api_key": api_key,
            "seen_ids": [clip["contentId"] for clip in clips],
        }
        await asyncio.to_thread(self.subscriptions_ref.document(str(interaction.user.id)).set, subscription)
        self.subscriptions[interaction.user.id] = subscription

        await interaction.followup.send(
            f"Fatto! Da adesso le tue nuove clip di Medal verranno pubblicate in <#{MEDAL_CHANNEL_ID}>. "
            "Usa /medalstop per disattivare.",
            ephemeral=True
        )

    @app_commands.command(name="medalstop", description="Smetti di pubblicare automaticamente le tue clip di Medal")
    async def medalstop(self, interaction: discord.Interaction):
        if self.subscriptions.pop(interaction.user.id, None) is None:
            await interaction.response.send_message("Non hai attivato la pubblicazione delle clip di Medal.", ephemeral=True)
            return
        await asyncio.to_thread(self.subscriptions_ref.document(str(interaction.user.id)).delete)
        await interaction.response.send_message("Le tue clip di Medal non verranno più pubblicate.", ephemeral=True)

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
        clips = await latest_clips(session, subscription["medal_user_id"], subscription.get("api_key") or DEFAULT_API_KEY)
        if not clips:
            return

        seen = subscription.get("seen_ids", [])
        new_clips = [clip for clip in clips if clip["contentId"] not in seen]
        if not new_clips:
            return

        # Dalla più vecchia alla più nuova, così nel canale restano in ordine
        for clip in reversed(new_clips):
            url = clip.get("directClipUrl") or clip.get("contentUrl")
            if url:
                await channel.send(
                    f"🎬 Nuova clip di <@{discord_user_id}>\n{url}",
                    allowed_mentions=discord.AllowedMentions.none()
                )

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
