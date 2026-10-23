import importlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from cogs.medal_api import MedalAPIError


class MedalCommandTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Nessuna connessione reale a Firestore o Discord durante i test.
        with patch.dict(sys.modules, {
            "db": SimpleNamespace(db=Mock()),
            "settings": SimpleNamespace(MEDAL_CHANNEL_ID=100),
        }):
            self.module = importlib.import_module("cogs.medal")
        self.cog = self.module.Medal(Mock())
        self.cog.subscriptions_ref = Mock()
        self.document = self.cog.subscriptions_ref.document.return_value
        self.interaction = SimpleNamespace(
            user=SimpleNamespace(id=42),
            response=SimpleNamespace(defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )

    async def test_subscribe_marks_existing_clips_seen_without_posting(self):
        self.assertEqual(self.cog.medal.name, "livemedal")
        self.assertEqual(self.cog.medal.description, "Iscriviti a LiveMedal per publicare automatimcanete le tue clip")
        self.assertEqual(self.cog.medalstop.name, "livemedalstop")
        self.assertEqual(self.cog.medalstop.description, "Disiscriviti da LiveMedal per non pubblicare automaticamente le tue clip")
        with patch.object(self.module, "resolve_medal_user_id", AsyncMock(return_value="123")), \
                patch.object(self.module, "latest_clips", AsyncMock(return_value=[{"contentId": "cidold"}])):
            await self.cog.medal.callback(self.cog, self.interaction, "https://medal.tv/clips/old")
        self.assertEqual(self.cog.subscriptions[42], {"medal_user_id": "123", "seen_ids": ["cidold"]})
        self.document.set.assert_called_once_with(self.cog.subscriptions[42])
        self.assertIn("Fatto!", self.interaction.followup.send.call_args.args[0])
        self.assertIn("/livemedalstop", self.interaction.followup.send.call_args.args[0])

    async def test_api_error_does_not_save_subscription(self):
        with patch.object(self.module, "resolve_medal_user_id", AsyncMock(return_value="123")), \
                patch.object(self.module, "latest_clips", AsyncMock(side_effect=MedalAPIError("Medal non disponibile"))):
            await self.cog.medal.callback(self.cog, self.interaction, "123")
        self.assertEqual(self.cog.subscriptions, {})
        self.document.set.assert_not_called()
        self.interaction.followup.send.assert_awaited_once_with("Medal non disponibile", ephemeral=True)

    async def test_posts_only_new_clips_in_order_and_does_not_repeat(self):
        subscription = {"medal_user_id": "123", "seen_ids": ["old"]}
        clips = [{"contentId": "cidnew2", "directClipUrl": "https://medal.tv/clips/new2"},
                 {"contentId": "cidnew1", "directClipUrl": "https://medal.tv/clips/new1"},
                 {"contentId": "cidold", "directClipUrl": "https://medal.tv/clips/old"}]
        channel = SimpleNamespace(send=AsyncMock())
        with patch.object(self.module, "latest_clips", AsyncMock(return_value=clips)):
            await self.cog.post_new_clips(None, channel, 42, subscription)
            await self.cog.post_new_clips(None, channel, 42, subscription)
        self.assertEqual(channel.send.await_count, 2)
        self.assertEqual(channel.send.await_args_list[0].args[0], "https://medal.tv/clips/new1")
        self.assertEqual(channel.send.await_args_list[1].args[0], "https://medal.tv/clips/new2")
        self.document.update.assert_called_once()

    async def test_stop_keeps_subscription_if_database_fails(self):
        self.cog.subscriptions[42] = {"medal_user_id": "123"}
        self.document.delete.side_effect = RuntimeError("database unavailable")
        with self.assertRaises(RuntimeError):
            await self.cog.medalstop.callback(self.cog, self.interaction)
        self.assertIn(42, self.cog.subscriptions)
        self.interaction.response.defer.assert_awaited_once_with(ephemeral=True)
