import asyncio
import re
import uuid
from urllib.parse import urlsplit

import aiohttp

MEDAL_API_URL = "https://medal.tv/api/content"
MEDAL_GUEST_URL = "https://medal.tv/api/users"
MEDAL_CONTENT_URL = "https://medal.tv/api/content/{clip_id}"
CLIPS_PER_CHECK = 10
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=20)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LiveBot)",
    "Accept": "application/json",
    "Medal-User-Agent": "Medal-web/1.0 (string_id; simplified_signup; no_upscale; markdown)",
}


class MedalAPIError(Exception):
    """Errore mostrabile all'utente, senza includere chiavi API o risposte remote."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class MedalClient:
    """Una sessione ospite per processo, rinnovata solo se Medal la rifiuta."""

    def __init__(self):
        self.token = None
        self.lock = asyncio.Lock()

    async def guest_token(self, session, rejected_token=None):
        async with self.lock:
            if self.token and self.token != rejected_token:
                return self.token
            data = await request_json(
                session, MEDAL_GUEST_URL, method="post",
                json={"email": "guest", "userName": "guest", "password": str(uuid.uuid4())},
            )
            user = data.get("user") if isinstance(data, dict) else None
            auth = data.get("auth") if isinstance(data, dict) else None
            if (not isinstance(user, dict) or user.get("guest") is not True
                    or not str(user.get("userId", "")).isdigit()
                    or not isinstance(auth, dict) or not isinstance(auth.get("key"), str)
                    or not auth["key"]):
                raise MedalAPIError("Medal non ha restituito una sessione ospite valida. Riprova più tardi.")
            self.token = f"{user['userId']},{auth['key']}"
            return self.token

    async def latest_clips(self, session, medal_user_id):
        token = await self.guest_token(session)
        for attempt in range(2):
            try:
                data = await request_json(
                    session, MEDAL_API_URL,
                    params={"userId": str(medal_user_id), "limit": CLIPS_PER_CHECK,
                            "privacy": "0", "sortBy": "publishedAt", "sortDirection": "DESC"},
                    headers={"X-Authentication": token},
                )
                break
            except MedalAPIError as error:
                if error.status != 401 or attempt:
                    raise
                token = await self.guest_token(session, rejected_token=token)
        if not isinstance(data, list):
            raise MedalAPIError("Il formato della risposta di Medal non è valido. Riprova più tardi.")
        clips = []
        for clip in data:
            if not isinstance(clip, dict) or not clip.get("contentId"):
                continue
            poster = clip.get("poster")
            if (not isinstance(poster, dict) or str(poster.get("userId")) != str(medal_user_id)
                    or clip.get("privacy") not in (0, "0") or not clip.get("publishedAt")):
                continue
            # La vecchia API anteponeva 'cid': manteniamo gli ID delle iscrizioni esistenti.
            clip_id = str(clip["contentId"]).removeprefix("cid")
            clips.append(dict(clip, contentId="cid" + clip_id,
                              directClipUrl=f"https://medal.tv/clips/{clip_id}"))
        return clips


client = MedalClient()


async def request_json(session, url, method="get", **kwargs):
    try:
        async with getattr(session, method)(url, headers=HEADERS | kwargs.pop("headers", {}),
                               timeout=REQUEST_TIMEOUT, **kwargs) as response:
            if response.status in (401, 403):
                raise MedalAPIError(
                    "Medal ha rifiutato l'accesso alla sessione ospite. Riprova più tardi.",
                    status=response.status,
                )
            if response.status == 429:
                raise MedalAPIError("Medal ha raggiunto il limite di richieste. Riprova più tardi.")
            if response.status == 404:
                raise MedalAPIError("Clip o profilo Medal non trovato: verifica che sia pubblico e che il link sia corretto.")
            if response.status != 200:
                raise MedalAPIError(f"Medal non è disponibile (HTTP {response.status}). Riprova più tardi.")
            try:
                return await response.json(content_type=None)
            except ValueError as error:
                raise MedalAPIError("Medal ha restituito una risposta non valida. Riprova più tardi.") from error
    except (aiohttp.ClientError, asyncio.TimeoutError) as error:
        raise MedalAPIError("Non riesco a contattare Medal. Riprova tra poco.") from error


async def latest_clips(session, medal_user_id):
    return await client.latest_clips(session, medal_user_id)


async def resolve_medal_user_id(session, text):
    text = text.strip().strip("<>")
    if text.isascii() and text.isdigit():
        return text
    url = urlsplit(text if "://" in text else "https://" + text)
    if url.scheme not in ("http", "https") or url.hostname not in ("medal.tv", "www.medal.tv"):
        return None
    if match := re.fullmatch(r"/users/(\d+)/?", url.path):
        return match.group(1)
    match = re.search(r"/(?:clips?|clip)/(?:cid)?([A-Za-z0-9_-]+)(?:/|$)", url.path)
    if not match:
        return None
    data = await request_json(session, MEDAL_CONTENT_URL.format(clip_id=match.group(1)))
    poster = data.get("poster") if isinstance(data, dict) else None
    user_id = str(poster.get("userId", "")) if isinstance(poster, dict) else ""
    return user_id if user_id.isascii() and user_id.isdigit() else None
