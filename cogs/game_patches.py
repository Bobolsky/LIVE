import html
import re
from dataclasses import dataclass
import aiohttp
import discord
from discord.ext import commands, tasks
from db import db
import settings

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; LiveBot)"}
MAX_PATCHES_PER_CHECK = 3


@dataclass
class PatchNotesSource:
    # Giochi con una pagina ufficiale per ogni patch: si controlla se esiste la pagina della patch successiva
    url: str  # con {major} e {minor}, es. ".../league-of-legends-patch-{major}-{minor}-notes/"
    seed: str  # ultima patch nota, usata al primo avvio
    pad_minor: bool = False  # Valorant scrive 13.08, LoL 26.8

    def format(self, major: int, minor: int):
        return f"{major}.{minor:02d}" if self.pad_minor else f"{major}.{minor}"

    def article_url(self, patch: str):
        major, minor = patch.split(".")
        return self.url.format(major=major, minor=minor)

    def next_patches(self, patch: str):
        # Dopo la 26.21 può uscire la 26.22 oppure, a cambio di versione, la 27.0 / 27.1
        major, minor = (int(n) for n in patch.split("."))
        return [self.format(major, minor + 1), self.format(major + 1, 0), self.format(major + 1, 1)]


@dataclass
class FortniteSource:
    # Fortnite non ha patch notes ufficiali con un indirizzo fisso: si legge la versione del gioco
    url: str = "https://fortnite-api.com/v2/aes"
    news_url: str = "https://www.fortnite.com/news"


@dataclass
class Game:
    name: str
    state_doc: str  # documento in bot_state con l'ultima patch notificata
    channel_id: int
    role_id: int
    color: int
    source: PatchNotesSource | FortniteSource


GAMES = [
    Game(
        name="League of Legends",
        state_doc="lol_patch",
        channel_id=settings.LOL_PATCH_CHANNEL_ID,
        role_id=settings.LOL_PATCH_ROLE_ID,
        color=0x69C6FE,
        source=PatchNotesSource(
            url="https://www.leagueoflegends.com/en-us/news/game-updates/league-of-legends-patch-{major}-{minor}-notes/",
            seed="26.21",
        ),
    ),
    Game(
        name="Valorant",
        state_doc="valorant_patch",
        channel_id=settings.VALORANT_PATCH_CHANNEL_ID,
        role_id=settings.VALORANT_PATCH_ROLE_ID,
        color=0xFB6868,
        source=PatchNotesSource(
            url="https://playvalorant.com/en-us/news/game-updates/valorant-patch-notes-{major}-{minor}/",
            seed="13.08",
            pad_minor=True,
        ),
    ),
    Game(
        name="Fortnite",
        state_doc="fortnite_patch",
        channel_id=settings.FORTNITE_PATCH_CHANNEL_ID,
        role_id=settings.FORTNITE_PATCH_ROLE_ID,
        color=0x3D7EFF,
        source=FortniteSource(),
    ),
]


def og_tag(page: str, name: str):
    # Legge un tag OpenGraph (og:title, og:description, og:image) dall'HTML della pagina
    for tag in re.findall(r"<meta\b[^>]*>", page, re.IGNORECASE):
        if re.search(rf'property=["\']og:{name}["\']', tag, re.IGNORECASE):
            content = re.search(r'content=["\']([^"\']*)["\']', tag, re.IGNORECASE)
            return html.unescape(content.group(1)).strip() if content else None
    return None


async def fetch_patch_embed(session: aiohttp.ClientSession, game: Game, patch: str):
    # Restituisce l'embed con titolo, descrizione e immagine della pagina ufficiale delle patch notes,
    # oppure None se la pagina non esiste ancora
    url = game.source.article_url(patch)
    try:
        async with session.get(url, headers=HEADERS) as response:
            if response.status != 200:
                return None
            page = await response.text()
    except aiohttp.ClientError as e:
        print(f"[{game.name}] Errore durante la richiesta delle patch notes: {e}")
        return None

    title = og_tag(page, "title")
    # Evita le pagine "non trovata" servite con status 200: il titolo deve contenere il numero della patch
    if not title or patch not in title:
        print(f"[{game.name}] Pagina senza titolo valido per la patch {patch}: {url} (titolo: {title})")
        return None

    embed = discord.Embed(title=title, url=url, description=og_tag(page, "description"), color=game.color)
    image = og_tag(page, "image")
    if image:
        embed.set_thumbnail(url=image)
    return embed


async def find_next_patch(session: aiohttp.ClientSession, game: Game, current: str):
    for candidate in game.source.next_patches(current):
        embed = await fetch_patch_embed(session, game, candidate)
        if embed:
            return candidate, embed
    return None


async def fortnite_version(session: aiohttp.ClientSession, source: FortniteSource):
    # La build è del tipo "++Fortnite+Release-42.40-CL-59086525": interessa solo "42.40"
    async with session.get(source.url, headers=HEADERS) as response:
        if response.status != 200:
            print(f"[Fortnite] Errore durante la richiesta della versione: {response.status}")
            return None
        try:
            data = await response.json(content_type=None)
        except ValueError:
            data = None

    build = ((data or {}).get("data") or {}).get("build", "") if isinstance(data, dict) else ""
    match = re.search(r"Release-(\d+\.\d+)", build)
    if not match:
        print(f"[Fortnite] Versione non valida: {build!r}")
        return None
    return match.group(1)


class GamePatches(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.check_patches.start()

    async def cog_unload(self):
        self.check_patches.cancel()

    def state_ref(self, game: Game):
        # L'ultima patch notificata è salvata su Firestore, così un riavvio non rimanda la notifica
        return db.collection('bot_state').document(game.state_doc)

    async def notify(self, game: Game, embed: discord.Embed):
        channel = self.bot.get_channel(game.channel_id)
        if channel is None:
            print(f"[{game.name}] Canale per le patch non trovato.")
            return False
        await channel.send(
            f"<@&{game.role_id}>",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=[discord.Object(id=game.role_id)])
        )
        return True

    async def check_patch_notes(self, session: aiohttp.ClientSession, game: Game):
        state_ref = self.state_ref(game)
        current = (state_ref.get().to_dict() or {}).get("patch")

        # Primo avvio: si parte dall'ultima patch nota e si avanza fino all'ultima uscita, senza notificare
        if current is None:
            current = game.source.seed
            for _ in range(MAX_PATCHES_PER_CHECK):
                found = await find_next_patch(session, game, current)
                if not found:
                    break
                current = found[0]
            state_ref.set({"patch": current})
            print(f"[{game.name}] Patch attuale: {current}")
            return

        for _ in range(MAX_PATCHES_PER_CHECK):
            found = await find_next_patch(session, game, current)
            if not found:
                return
            current, embed = found
            if not await self.notify(game, embed):
                return
            state_ref.set({"patch": current})

    async def check_fortnite(self, session: aiohttp.ClientSession, game: Game):
        version = await fortnite_version(session, game.source)
        if version is None:
            return

        state_ref = self.state_ref(game)
        current = (state_ref.get().to_dict() or {}).get("patch")
        if current == version:
            return

        # Primo avvio: salva la versione attuale senza notificare
        if current is not None:
            embed = discord.Embed(
                title=f"Fortnite: nuovo aggiornamento {version}",
                url=game.source.news_url,
                description=f"È disponibile la versione **{version}**.\n**[Leggi le novità]({game.source.news_url})**",
                color=game.color
            )
            if not await self.notify(game, embed):
                return
        state_ref.set({"patch": version})

    @tasks.loop(minutes=30)
    async def check_patches(self):
        async with aiohttp.ClientSession() as session:
            for game in GAMES:
                # Un errore su un gioco non deve bloccare il controllo degli altri
                try:
                    if isinstance(game.source, FortniteSource):
                        await self.check_fortnite(session, game)
                    else:
                        await self.check_patch_notes(session, game)
                except Exception as e:
                    print(f"[{game.name}] Errore durante il controllo delle patch: {e!r}")

    @check_patches.before_loop
    async def before_check_patches(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(GamePatches(bot))
