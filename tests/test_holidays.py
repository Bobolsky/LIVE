import importlib
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch


class HolidayTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        with patch.dict(sys.modules, {
            "db": SimpleNamespace(db=Mock()),
            "settings": SimpleNamespace(ROME_TZ=timezone(timedelta(hours=1)), WELCOME_CHANNEL_ID=100),
        }):
            self.module = importlib.import_module("cogs.holidays")
        self.saved = {}
        self.state = Mock()
        self.state.get.return_value.to_dict.side_effect = lambda: dict(self.saved)
        self.state.set.side_effect = self.saved.update
        self.channel = SimpleNamespace(send=AsyncMock())
        self.bot = Mock()
        self.bot.get_channel.return_value = self.channel
        self.cog = self.module.Holidays(self.bot)
        self.cog.state_ref = self.state

    def at(self, year, month, day):
        clock = Mock()
        clock.now.return_value = datetime(year, month, day, tzinfo=self.module.ROME_TZ)
        return patch.object(self.module, "datetime", clock)

    async def test_fixed_holidays_and_exact_messages(self):
        expected = {
            (10, 31): "Buon Halloween! 👻 🎃 ❤️",
            (12, 24): "Buona Vigilia di Natale! ❄️ 🎁 ❤️",
            (12, 25): "Buon Natale! 🎄 🎅 ❤️",
            (1, 1): "Buon Anno! 🥂 ✨ ❤️",
            (8, 15): "Buon Ferragosto! 🔥 🌊 ❤️",
            (1, 6): "Buona Befana! 👵 🍫 ❤️",
        }
        for (month, day), message in expected.items():
            self.assertEqual(self.module.holiday_message(date(2026, month, day)), message)

    async def test_easter_changes_each_year(self):
        for day in (date(2026, 4, 5), date(2027, 3, 28), date(2028, 4, 16)):
            self.assertEqual(self.module.holiday_message(day), "Buona Pasqua! 🕊️ 🐣 ❤️")
        self.assertIsNone(self.module.holiday_message(date(2027, 4, 5)))

    async def test_regular_day_does_not_touch_database_or_send(self):
        with self.at(2026, 10, 24):
            await self.cog.send_greeting()
        self.state.get.assert_not_called()
        self.channel.send.assert_not_awaited()

    async def test_no_duplicates_after_check_or_restart(self):
        with self.at(2026, 10, 31):
            await self.cog.send_greeting()
            await self.cog.send_greeting()
            restarted = self.module.Holidays(self.bot)
            restarted.state_ref = self.state
            await restarted.send_greeting()
        self.channel.send.assert_awaited_once()
        self.assertEqual(self.channel.send.call_args.args[0], "Buon Halloween! 👻 🎃 ❤️")
        self.assertEqual(self.saved, {"last_sent": "2026-10-31"})

    async def test_holidays_are_sent_again_next_year(self):
        with self.at(2026, 12, 25):
            await self.cog.send_greeting()
        with self.at(2027, 12, 25):
            await self.cog.send_greeting()
        self.assertEqual(self.channel.send.await_count, 2)

    async def test_uses_rome_timezone(self):
        with self.at(2026, 12, 25) as clock:
            await self.cog.send_greeting()
        clock.now.assert_called_once_with(self.module.ROME_TZ)

    async def test_failed_send_is_retried_without_marking_sent(self):
        self.channel.send.side_effect = RuntimeError("Discord unavailable")
        with self.at(2026, 12, 25):
            with self.assertRaises(RuntimeError):
                await self.cog.send_greeting()
            self.state.set.assert_not_called()
            self.channel.send.side_effect = None
            await self.cog.send_greeting()
        self.assertEqual(self.saved, {"last_sent": "2026-12-25"})

    async def test_missing_channel_is_not_marked_sent(self):
        self.bot.get_channel.return_value = None
        with self.at(2026, 12, 25), self.assertLogs(level="WARNING"):
            await self.cog.send_greeting()
        self.state.set.assert_not_called()

    async def test_loop_handles_temporary_failures(self):
        with patch.object(self.cog, "send_greeting", AsyncMock(side_effect=RuntimeError("offline"))), \
                self.assertLogs(level="ERROR"):
            await self.cog.check_holidays.coro(self.cog)
