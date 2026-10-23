import io
import unittest
from unittest.mock import patch

from PIL import Image, ImageFont

import wheel_image
from wheel_text import WheelLabels, download_emoji, emoji_codepoints, name_tokens


class WheelImageTests(unittest.TestCase):
    def test_labels_have_dark_bold_text_and_white_outline(self):
        result = WheelLabels().render("Vista", ImageFont.load_default(size=28), 160, 12)
        pixels = list(result.getdata())
        self.assertIn((15, 15, 15, 255), pixels)
        self.assertIn((255, 255, 255, 255), pixels)
        self.assertGreater(result.getbbox()[3] - result.getbbox()[1], 22)
        self.assertGreaterEqual(result.getbbox()[0], 18)
        self.assertLessEqual(result.getbbox()[2], 146)

    def test_sequences_are_not_split_when_truncating(self):
        for value in ("❤️", "🇮🇹", "👍🏽", "👨‍👩‍👧‍👦", "👩🏽‍💻", "1️⃣"):
            with self.subTest(emoji=value):
                self.assertEqual(name_tokens("A" + value + "BC", 3),
                                 [("A", False), (value, True), ("…", False)])

    def test_twemoji_codepoints(self):
        self.assertEqual(emoji_codepoints("❤️"), "2764")
        self.assertEqual(emoji_codepoints("🇮🇹"), "1f1ee-1f1f9")
        self.assertEqual(emoji_codepoints("👍🏽"), "1f44d-1f3fd")
        self.assertEqual(emoji_codepoints("🏳️‍🌈"), "1f3f3-fe0f-200d-1f308")

    def test_download_cache(self):
        data = io.BytesIO()
        Image.new("RGBA", (72, 72), "red").save(data, format="PNG")
        download_emoji.cache_clear()
        try:
            with patch("wheel_text.urlopen") as fetch:
                fetch.return_value.__enter__.return_value.read.return_value = data.getvalue()
                self.assertEqual(download_emoji("🔥").size, (72, 72))
                download_emoji("🔥")
                fetch.assert_called_once()
                self.assertEqual(fetch.call_args.kwargs["timeout"], 2)
        finally:
            download_emoji.cache_clear()

    def test_colored_emoji_are_composited(self):
        with patch("wheel_text.download_emoji", return_value=Image.new("RGBA", (72, 72), "red")) as fetch:
            labels = WheelLabels()
            result = labels.render("🔥🔥", ImageFont.load_default(size=22), 160, 12)
            fetch.assert_called_once_with("🔥")
            self.assertIn((255, 0, 0, 255), result.getdata())
            self.assertEqual(result.width, 160)

    def test_unavailable_emoji_does_not_break_rendering_or_repeat_requests(self):
        with patch("wheel_text.download_emoji", side_effect=OSError("offline")) as fetch:
            labels = WheelLabels()
            image = labels.render("Uno 🔥🔥", ImageFont.load_default(size=22), 160, 12)
            self.assertIsNotNone(image.getbbox())
            fetch.assert_called_once_with("🔥")

    def test_no_download_after_budget(self):
        labels = WheelLabels()
        labels.deadline = 0
        with patch("wheel_text.download_emoji") as fetch:
            self.assertIsNone(labels.emoji_image("🔥"))
            fetch.assert_not_called()

    def test_gif_and_final_png_with_emoji_names(self):
        with patch("wheel_text.download_emoji", return_value=Image.new("RGBA", (72, 72), "red")):
            gif, png, duration = wheel_image.render_spin(["Uno 🇮🇹", "Due 👩🏽‍💻"], 1)
        with Image.open(io.BytesIO(gif)) as image:
            self.assertEqual(image.format, "GIF")
            self.assertGreater(image.n_frames, 1)
            self.assertEqual(image.size, (360, 360))
        with Image.open(io.BytesIO(png)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (360, 360))
        self.assertGreater(duration, 0)
