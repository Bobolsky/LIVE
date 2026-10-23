import asyncio
import unittest

import aiohttp

from cogs.medal_api import MedalAPIError, MedalClient, request_json, resolve_medal_user_id


class Response:
    def __init__(self, status=200, data=None):
        self.status = status
        self.data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self, **kwargs):
        if isinstance(self.data, Exception):
            raise self.data
        return self.data


class Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class MedalAPITests(unittest.IsolatedAsyncioTestCase):
    async def test_numeric_id_and_profile_do_not_request_api(self):
        session = Session(None)
        for text in (" 123 ", "https://medal.tv/users/123?x=1", "<https://medal.tv/users/123>"):
            self.assertEqual(await resolve_medal_user_id(session, text), "123")
        self.assertEqual(session.calls, [])

    async def test_reject_foreign_hosts(self):
        session = Session(None)
        for text in ("https://evilmedal.tv/users/123", "https://medal.tv.evil.com/clips/abc",
                     "https://evil.com/medal.tv/users/123", "not a link"):
            self.assertIsNone(await resolve_medal_user_id(session, text))
        self.assertEqual(session.calls, [])

    async def test_clip_link_formats(self):
        for path in ("games/valorant/clips/abc-123?invite=x", "clip/abc-123/token", "clips/cidabc-123"):
            session = Session(Response(data={"poster": {"userId": 123}}))
            self.assertEqual(await resolve_medal_user_id(session, "https://medal.tv/" + path), "123")
            self.assertTrue(session.calls[0][0].endswith("/abc-123"))

    async def test_guest_session_reused_without_api_key(self):
        client = MedalClient()
        session = SequenceSession([
            Response(data={"user": {"userId": "1", "guest": True}, "auth": {"key": "guest-key"}}),
            Response(data=[]), Response(data=[]),
        ])
        self.assertEqual(await client.latest_clips(session, "123"), [])
        self.assertEqual(await client.latest_clips(session, "123"), [])
        self.assertEqual([method for method, _, _ in session.calls], ["post", "get", "get"])
        self.assertEqual(session.calls[1][2]["headers"]["X-Authentication"], "1,guest-key")
        self.assertEqual(session.calls[1][2]["params"]["privacy"], "0")

    async def test_api_errors(self):
        for status, message in ((401, "rifiutato"), (403, "rifiutato"), (429, "limite"),
                                (404, "non trovato"), (503, "HTTP 503")):
            with self.subTest(status=status):
                with self.assertRaisesRegex(MedalAPIError, message):
                    await request_json(Session(Response(status)), "https://medal.tv/api/content")

    async def test_bad_response(self):
        for data in (ValueError(), {}, {"contentObjects": None}):
            with self.assertRaises(MedalAPIError):
                client = MedalClient()
                client.token = "1,guest-key"
                await client.latest_clips(Session(Response(data=data)), "123")

    async def test_network_errors(self):
        for error in (asyncio.TimeoutError(), aiohttp.ClientConnectionError()):
            with self.assertRaisesRegex(MedalAPIError, "contattare"):
                await request_json(Session(error), "https://medal.tv/api/content")

    async def test_empty_list_is_success(self):
        client = MedalClient()
        client.token = "1,guest-key"
        self.assertEqual(await client.latest_clips(Session(Response(data=[])), "123"), [])

    async def test_normalizes_ids_and_filters_invalid_entries(self):
        clip = {"contentId": "abc", "poster": {"userId": 123}, "privacy": 0, "publishedAt": 100}
        session = Session(Response(data=[None, {}, "bad", clip,
                                        dict(clip, privacy=1), dict(clip, publishedAt=None),
                                        dict(clip, poster={"userId": 456})]))
        client = MedalClient()
        client.token = "1,guest-key"
        clips = await client.latest_clips(session, "123")
        self.assertEqual(len(clips), 1)
        self.assertEqual(clips[0]["contentId"], "cidabc")
        self.assertEqual(clips[0]["directClipUrl"], "https://medal.tv/clips/abc")
        self.assertEqual(session.calls[0][1]["timeout"].total, 20)

    async def test_expired_guest_session_renews_once(self):
        client = MedalClient()
        client.token = "old"
        session = SequenceSession([
            Response(401),
            Response(data={"user": {"userId": "2", "guest": True}, "auth": {"key": "new"}}),
            Response(data=[]),
        ])
        self.assertEqual(await client.latest_clips(session, "123"), [])
        self.assertEqual(client.token, "2,new")
        self.assertEqual(len(session.calls), 3)

    async def test_does_not_retry_forever(self):
        client = MedalClient()
        client.token = "old"
        session = SequenceSession([
            Response(401),
            Response(data={"user": {"userId": "2", "guest": True}, "auth": {"key": "new"}}),
            Response(401),
        ])
        with self.assertRaises(MedalAPIError):
            await client.latest_clips(session, "123")
        self.assertEqual(len(session.calls), 3)

    async def test_invalid_guest(self):
        for data in ({}, {"user": {"userId": "1", "guest": False}, "auth": {"key": "key"}}):
            with self.assertRaisesRegex(MedalAPIError, "ospite valida"):
                await MedalClient().latest_clips(SequenceSession([Response(data=data)]), "123")

    async def test_invalid_poster(self):
        for data in ([], {}, {"poster": []}, {"poster": {"userId": "abc"}}):
            self.assertIsNone(await resolve_medal_user_id(
                Session(Response(data=data)), "https://medal.tv/clips/abc"
            ))


class SequenceSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        return next(self.responses)

    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        return next(self.responses)


if __name__ == "__main__":
    unittest.main()
