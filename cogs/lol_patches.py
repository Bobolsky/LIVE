import html
import re
import aiohttp
import discord
from discord.ext import commands, tasks
from db import db
from settings import LOL_PATCH_CHANNEL_ID, LOL_PATCH_ROLE_ID

# Data Dragon serve solo per il primo avvio (numerazione per stagione, es. "16.20.1"): è in ritardo
# rispetto alle patch notes, quindi le nuove patch si rilevano controllando la pagina ufficiale
VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
# Pagina ufficiale della singola patch (es. patch 26.20 -> .../league-of-legends-patch-26-20-notes/)
PATCH_ARTICLE_URL = "https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-{major}-{minor}-notes/"
EMBED_COLOR = 0x0AC8B9
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LiveBot)"}
MAX_PATCHES_PER_CHECK = 3


def article_url(patch: str):
    major, minor = patch.split(".")
    return PATCH_ARTICLE_URL.format(major=major, minor=minor)


def next_patches(patch: str):
    # Dopo la 26.21 può uscire la 26.22 oppure, a cambio anno, la 27.1
    major, minor = (int(n) for n in patch.split("."))
    return [f"{major}.{minor + 1}", f"{major + 1}.1"]


def og_tag(page: str, name: str):
    # Legge un tag OpenGraph (og:title, og:description, og:image) dall'HTML della pagina
    for tag in re.findall(r"<meta\b[^>]*>", page, re.IGNORECASE):
        if re.search(rf'property=["\']og:{name}["\']', tag, re.IGNORECASE):
            content = re.search(r'content=["\']([^"\']*)["\']', tag, re.IGNORECASE)
            return html.unescape(content.group(1)).strip() if content else None
    return None


async def fetch_patch_embed(session: aiohttp.ClientSession, patch: str):
    # Restituisce l'embed con titolo, descrizione e immagine della pagina ufficiale delle patch notes,
    # oppure None se la pagina non esiste ancora
    url = article_url(patch)
    try:
        async with session.get(url, headers=HEADERS) as response:
            if response.status != 200:
                return None
            page = await response.text()
    except aiohttp.ClientError as e:
        print(f"Errore durante la richiesta delle patch notes: {e}")
        return None

    title = og_tag(page, "title")
    # Evita le pagine "non trovata" servite con status 200: il titolo deve contenere il numero della patch
    if not title or patch not in title:
        print(f"Pagina senza titolo valido per la patch {patch}: {url} (titolo: {title})")
        return None

    embed = discord.Embed(title=title, url=url, description=og_tag(page, "description"), color=EMBED_COLOR)
    image = og_tag(page, "image")
    if image:
        embed.set_thumbnail(url=image)
    return embed


async def find_next_patch(session: aiohttp.ClientSession, current: str):
    for candidate in next_patches(current):
        embed = await fetch_patch_embed(session, candidate)
        if embed:
            return candidate, embed
    return None


async def latest_data_dragon_patch(session: aiohttp.ClientSession):
    async with session.get(VERSIONS_URL) as response:
        if response.status != 200:
            print(f"Errore durante la richiesta a Data Dragon: {response.status}")
            return None
        try:
            versions = await response.json(content_type=None)
        except ValueError:
            versions = None

    if not isinstance(versions, list) or not versions:
        print("Risposta non valida da Data Dragon.")
        return None

    # Data Dragon numera le patch per stagione (es. 16.20), le patch notes usano l'anno (26.20)
    major, minor = versions[0].split(".")[:2]
    major = int(major)
    return f"{major + 10 if major < 20 else major}.{minor}"


class LolPatches(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # L'ultima patch notificata è salvata su Firestore, così un riavvio non rimanda la notifica
        self.state_ref = db.collection('bot_state').document('lol_patch')

    async def cog_load(self):
        self.check_lol_patch.start()

    async def cog_unload(self):
        self.check_lol_patch.cancel()

    @tasks.loop(minutes=30)
    async def check_lol_patch(self):
        current = (self.state_ref.get().to_dict() or {}).get("notes_patch")

        async with aiohttp.ClientSession() as session:
            # Primo avvio: si parte dall'ultima patch già uscita, senza notificare
            if current is None:
                current = await latest_data_dragon_patch(session)
                if current is None:
                    return
                for _ in range(MAX_PATCHES_PER_CHECK):
                    found = await find_next_patch(session, current)
                    if not found:
                        break
                    current = found[0]
                self.state_ref.set({"notes_patch": current})
                print(f"Patch di LoL attuale: {current}")
                return

            for _ in range(MAX_PATCHES_PER_CHECK):
                found = await find_next_patch(session, current)
                if not found:
                    return
                current, embed = found

                channel = self.bot.get_channel(LOL_PATCH_CHANNEL_ID) if LOL_PATCH_CHANNEL_ID else None
                if channel is None:
                    print("Canale per le patch di LoL non configurato o non trovato.")
                    return

                await channel.send(
                    f"<@&{LOL_PATCH_ROLE_ID}>",
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions(roles=[discord.Object(id=LOL_PATCH_ROLE_ID)])
                )
                self.state_ref.set({"notes_patch": current})

    @check_lol_patch.before_loop
    async def before_check_lol_patch(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(LolPatches(bot))
