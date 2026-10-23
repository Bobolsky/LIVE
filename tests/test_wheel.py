import importlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import discord


class WheelTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        with patch.dict(sys.modules, {"wheel_image": SimpleNamespace(render_spin=lambda *args: None)}):
            self.module = importlib.import_module("cogs.wheel")
        self.owner = SimpleNamespace(id=1, display_name="Uno")
        self.other = SimpleNamespace(id=2, display_name="Due")
        self.view = self.module.WheelView(self.owner)

    async def test_command_name_and_red_buttons(self):
        self.assertEqual(self.module.Wheel.wheel.name, "wheel")
        self.assertEqual(self.module.Wheel.wheel.description, "Crea una ruota")
        self.assertTrue(all(button.style == discord.ButtonStyle.danger for button in self.view.children))
        self.assertEqual([button.label for button in self.view.children], ["Partecipa", "▶", "◼"])
        self.assertFalse(hasattr(self.view, "leave_button"))

    async def test_embed_title_no_description_and_player_icons(self):
        self.view.players = {1: self.owner}
        self.view.eliminated = [self.other]
        embed = self.view.lobby_embed()
        self.assertEqual(embed.title, "LIVE Wheel")
        self.assertIsNone(embed.description)
        self.assertEqual(embed.colour.value, 0xFF0000)
        self.assertEqual(embed.fields[0].name, "❤️ In gioco (1)")
        self.assertEqual(embed.fields[0].value, "Uno")
        self.assertEqual(embed.fields[1].name, "💀 Eliminati (1)")
        self.assertEqual(embed.fields[1].value, "Due")

    async def test_start_without_leave_button(self):
        self.view.players = {1: self.owner, 2: self.other}
        interaction = SimpleNamespace(
            user=self.owner, response=SimpleNamespace(edit_message=AsyncMock()), message=object()
        )
        with patch.object(self.view, "run", new=AsyncMock()) as run:
            await self.view.start_button.callback(interaction)
        run.assert_awaited_once_with(interaction.message)
        self.assertTrue(self.view.join_button.disabled)
        self.assertTrue(self.view.start_button.disabled)
        self.assertFalse(self.view.stop_button.disabled)

    async def test_all_spin_states_keep_same_title_without_description(self):
        self.view.players = {1: self.owner, 2: self.other}
        message = SimpleNamespace(edit=AsyncMock())
        with patch.object(self.module, "render_spin", return_value=(b"gif", b"png", 0)), \
                patch.object(self.module.asyncio, "sleep", new=AsyncMock()):
            await self.view.run(message)
        self.assertEqual(message.edit.await_count, 3)
        for call in message.edit.await_args_list:
            self.assertEqual(call.kwargs["embed"].title, "LIVE Wheel")
            self.assertIsNone(call.kwargs["embed"].description)
        self.assertEqual(len(self.view.players), 1)
        self.assertEqual(len(self.view.eliminated), 1)

    async def test_timeout_keeps_title_without_description(self):
        self.view.message = SimpleNamespace(edit=AsyncMock())
        await self.view.on_timeout()
        embed = self.view.message.edit.call_args.kwargs["embed"]
        self.assertEqual(embed.title, "LIVE Wheel")
        self.assertIsNone(embed.description)
