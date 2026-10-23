import io
import random
from PIL import Image, ImageDraw, ImageFont

SIZE = 360
WHEEL_RADIUS = 160
SPIN_FRAMES = 45
FRAME_MS = 60
FINAL_FRAME_MS = 3000
EXTRA_TURNS = 4
BACKGROUND = (49, 51, 56)  # Grigio dei messaggi di Discord
COLORS = [
    (237, 66, 69), (254, 231, 92), (87, 242, 135), (88, 101, 242),
    (235, 69, 158), (255, 159, 67), (69, 196, 237), (155, 89, 182),
]
MAX_NAME_LENGTH = 12


def slice_colors(count: int):
    colors = [COLORS[i % len(COLORS)] for i in range(count)]
    # Il primo e l'ultimo spicchio sono adiacenti: evita che abbiano lo stesso colore
    if count > 1 and colors[-1] == colors[0]:
        colors[-1] = COLORS[(count - 1 + 1) % len(COLORS)]
    return colors


def draw_wheel(names: list[str]):
    # Ruota ferma: lo spicchio i occupa gli angoli [i * step, (i + 1) * step), in senso orario dalle ore 3
    size = WHEEL_RADIUS * 2
    wheel = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(wheel)
    step = 360 / len(names)
    font = ImageFont.load_default(size=max(10, min(22, int(260 / max(len(names), 1)) + 6)))

    for i, (name, color) in enumerate(zip(names, slice_colors(len(names)))):
        draw.pieslice((0, 0, size - 1, size - 1), i * step, (i + 1) * step, fill=color, outline=(255, 255, 255), width=2)

        # Il nome viene scritto in orizzontale su un'immagine a parte e ruotato lungo il raggio dello spicchio
        label = name if len(name) <= MAX_NAME_LENGTH else name[:MAX_NAME_LENGTH - 1] + "…"
        box = draw.textbbox((0, 0), label, font=font)
        text_width, text_height = box[2] - box[0], box[3] - box[1]
        text = Image.new("RGBA", (WHEEL_RADIUS, text_height + 8), (0, 0, 0, 0))
        ImageDraw.Draw(text).text(
            (WHEEL_RADIUS - text_width - 14, 4 - box[1]), label, font=font,
            fill=(20, 20, 20), stroke_width=1, stroke_fill=(255, 255, 255)
        )
        # Il testo parte dal centro verso il bordo: si incolla su un quadrato grande quanto la ruota e si ruota
        layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        layer.paste(text, (WHEEL_RADIUS, WHEEL_RADIUS - text.height // 2), text)
        layer = layer.rotate(-(i + 0.5) * step, resample=Image.BICUBIC, center=(WHEEL_RADIUS, WHEEL_RADIUS))
        wheel.alpha_composite(layer)

    draw.ellipse((WHEEL_RADIUS - 18, WHEEL_RADIUS - 18, WHEEL_RADIUS + 18, WHEEL_RADIUS + 18), fill=(255, 255, 255), outline=(30, 30, 30), width=3)
    return wheel


def draw_frame(wheel: Image.Image, rotation: float):
    frame = Image.new("RGBA", (SIZE, SIZE), BACKGROUND + (255,))
    rotated = wheel.rotate(rotation, resample=Image.BICUBIC)
    offset = (SIZE - wheel.width) // 2
    frame.alpha_composite(rotated, (offset, offset))

    # Freccia fissa in alto che indica lo spicchio estratto
    center = SIZE // 2
    top = offset - 6
    ImageDraw.Draw(frame).polygon(
        [(center - 16, top), (center + 16, top), (center, top + 34)],
        fill=(255, 255, 255), outline=(30, 30, 30), width=3
    )
    return frame.convert("RGB")


def final_rotation(count: int, index: int):
    # Rotazione (antioraria, in gradi) che porta lo spicchio "index" sotto la freccia, che sta a 270°
    step = 360 / count
    target = (index + 0.5 + random.uniform(-0.35, 0.35)) * step
    return (target - 270) % 360 + 360 * EXTRA_TURNS


def render_spin(names: list[str], index: int):
    """Restituisce (gif animata della ruota che si ferma su names[index], png della ruota ferma, durata in secondi)."""
    wheel = draw_wheel(names)
    end = final_rotation(len(names), index)

    frames = []
    for i in range(SPIN_FRAMES):
        t = i / (SPIN_FRAMES - 1)
        frames.append(draw_frame(wheel, end * (1 - (1 - t) ** 3)))  # Rallenta verso la fine

    # Palette unica per tutti i frame, così i colori non sfarfallano
    palette = frames[-1].quantize(colors=128)
    frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]

    gif = io.BytesIO()
    durations = [FRAME_MS] * (SPIN_FRAMES - 1) + [FINAL_FRAME_MS]
    # Senza "loop" la gif viene riprodotta una sola volta
    frames[0].save(gif, format="GIF", save_all=True, append_images=frames[1:], duration=durations, disposal=1)

    png = io.BytesIO()
    draw_frame(wheel, end).save(png, format="PNG")

    return gif.getvalue(), png.getvalue(), (SPIN_FRAMES - 1) * FRAME_MS / 1000
