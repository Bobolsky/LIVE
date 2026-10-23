import io
import time
from functools import lru_cache
from urllib.error import URLError
from urllib.request import Request, urlopen

import emoji
from PIL import Image, ImageDraw

# Twemoji graphics: Twitter, Inc. and contributors, CC BY 4.0 (see README).
TWEMOJI_URL = "https://cdn.jsdelivr.net/gh/jdecked/twemoji@17.0.2/assets/72x72/{codepoints}.png"
DOWNLOAD_BUDGET = 5  # secondi massimi dedicati ai download in un giro
TEXT_OUTLINE = 3
TEXT_WEIGHT = 1
TEXT_COLOR = (15, 15, 15)


def name_tokens(name, limit):
    """Tronca i nomi senza dividere bandiere, tonalità della pelle o sequenze ZWJ."""
    tokens = []
    end = 0
    for match in emoji.emoji_list(name):
        tokens.extend((char, False) for char in name[end:match["match_start"]])
        tokens.append((match["emoji"], True))
        end = match["match_end"]
    tokens.extend((char, False) for char in name[end:])
    if len(tokens) > limit:
        tokens = tokens[:limit - 1] + [("…", False)]
    # Raggruppa il testo normale per mantenere la spaziatura del font.
    runs = []
    for text, is_emoji in tokens:
        if runs and not is_emoji and not runs[-1][1]:
            runs[-1] = (runs[-1][0] + text, False)
        else:
            runs.append((text, is_emoji))
    return runs


def emoji_codepoints(value):
    # Twemoji omette VS16, tranne nelle sequenze con zero-width joiner.
    if "\u200d" not in value:
        value = value.replace("\ufe0f", "")
    return "-".join(f"{ord(char):x}" for char in value)


@lru_cache(maxsize=256)
def download_emoji(value):
    request = Request(TWEMOJI_URL.format(codepoints=emoji_codepoints(value)),
                      headers={"User-Agent": "LiveBot/1.0"})
    with urlopen(request, timeout=2) as response:
        data = response.read(128 * 1024 + 1)
    if len(data) > 128 * 1024:
        raise ValueError("Emoji troppo grande")
    with Image.open(io.BytesIO(data)) as image:
        if image.format != "PNG" or image.size != (72, 72):
            raise ValueError("Formato emoji non valido")
        return image.convert("RGBA")


class WheelLabels:
    def __init__(self):
        self.deadline = time.monotonic() + DOWNLOAD_BUDGET
        self.images = {}  # include i fallimenti: niente tentativi ripetuti nello stesso giro

    def emoji_image(self, value):
        if value not in self.images:
            image = None
            if time.monotonic() < self.deadline:
                try:
                    image = download_emoji(value)
                except (OSError, URLError, ValueError):
                    pass  # CDN irraggiungibile: la ruota deve comunque funzionare
            self.images[value] = image
        return self.images[value]

    def render(self, name, font, width, limit):
        runs = []
        measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        height = font.size
        for text, is_emoji in name_tokens(name, limit):
            image = self.emoji_image(text) if is_emoji else None
            if is_emoji:
                # Un simbolo leggibile se l'emoji non è disponibile, non un glifo mancante.
                runs.append((image if image is not None else "?", font.size, None))
            else:
                box = measure.textbbox((0, 0), text, font=font, stroke_width=TEXT_OUTLINE)
                run_width = box[2] - box[0]
                height = max(height, box[3] - box[1])
                runs.append((text, run_width, box))
        label = Image.new("RGBA", (max(1, sum(run[1] for run in runs)), height + 8))
        draw = ImageDraw.Draw(label)
        x = 0
        for content, run_width, box in runs:
            if isinstance(content, Image.Image):
                icon = content.resize((font.size, font.size), Image.Resampling.LANCZOS)
                label.alpha_composite(icon, (x, (label.height - font.size) // 2))
            else:
                box = box or draw.textbbox((0, 0), content, font=font, stroke_width=TEXT_OUTLINE)
                position = (x - box[0], (label.height - box[3] + box[1]) // 2 - box[1])
                # Due passaggi: contorno bianco e lettere ispessite, senza dipendere
                # dai font installati sul server. Le emoji restano immagini a colori.
                draw.text(position, content, font=font, fill=TEXT_COLOR,
                          stroke_width=TEXT_OUTLINE, stroke_fill=(255, 255, 255))
                draw.text(position, content, font=font, fill=TEXT_COLOR,
                          stroke_width=TEXT_WEIGHT, stroke_fill=TEXT_COLOR)
            x += run_width
        # Nessun nome deve uscire dallo spicchio o finire sotto il mozzo centrale.
        available = width - 32
        if label.width > available:
            scale = available / label.width
            label = label.resize((available, max(1, round(label.height * scale))), Image.Resampling.LANCZOS)
        result = Image.new("RGBA", (width, label.height))
        result.alpha_composite(label, (width - label.width - 14, 0))
        return result
