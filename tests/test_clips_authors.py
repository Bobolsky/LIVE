import importlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


class ClipAuthorTests(unittest.TestCase):
    def test_medal_author_is_preserved_without_visible_mention(self):
        with patch.dict(sys.modules, {
            "db": SimpleNamespace(db=Mock()),
            "settings": SimpleNamespace(CLIPS_CHANNEL_ID=100, GUILD_ID=200),
        }):
            module = importlib.import_module("cogs.clips")
        cog = module.Clips(SimpleNamespace(user=SimpleNamespace(id=1)))
        self.assertEqual(cog.clip.description, "Rivivi un momento indimenticabile attraverso una clip")
        message = SimpleNamespace(id=20, author=SimpleNamespace(id=1), mentions=[])
        cog.add_clip(message)
        cog.add_clip(message, author_id=42)
        cog.add_clip(message)
        self.assertEqual(cog.author_of, {20: 42})
        self.assertEqual(cog.clips_by_author, {42: [20]})
