import asyncio
import random
import discord
from discord import app_commands, ui
from discord.ext import commands

EMBED_COLOR = 0x5865F2
MIN_PLAYERS = 2
SPIN_FRAMES = 4  # quante volte cambia il nome mostrato mentre la ruota gira
SPIN_DELAY = 1.0  # secondi tra un nome e l'altro
ROUND_DELAY = 3.0  # secondi di pausa dopo ogni eliminazione


def format_players(players):
    # Un field di un embed accetta al massimo 1024 caratteri
    text = ", ".join(player.display_name for player in players) or "Nessuno"
    return text if len(text) <= 1000 else text[:1000].rsplit(",", 1)[0] + ", ..."


class WheelView(ui.View):
    def __init__(self, owner: discord.Member):
        super().__init__(timeout=1800)
        self.owner = owner
        self.players = {}  # user_id -> Member, solo chi è ancora in gioco
        self.eliminated = []
        self.running = False
        self.stopped = False
        self.message = None
        self.stop_button.disabled = True

    def can_control(self, user: discord.abc.User):
        # Possono avviare e fermare la ruota chi l'ha creata e chi partecipa, anche se già eliminato
        return user.id == self.owner.id or user.id in self.players or any(user.id == p.id for p in self.eliminated)

    def build_embed(self, title: str, description: str):
        embed = discord.Embed(title=title, description=description, color=EMBED_COLOR)
        embed.add_field(name=f"In gioco ({len(self.players)})", value=format_players(self.players.values()), inline=False)
        if self.eliminated:
            embed.add_field(name=f"Eliminati ({len(self.eliminated)})", value=format_players(self.eliminated), inline=False)
        return embed

    def lobby_embed(self):
        return self.build_embed(
            "🎡 Ruota",
            f"Premi **Iscriviti** per partecipare. Quando siete pronti (minimo {MIN_PLAYERS} giocatori) premi **Start**: "
            "a ogni giro la ruota elimina un giocatore, fino a quando ne resta uno."
        )

    def end_view(self):
        for item in self.children:
            item.disabled = True
        self.stop()

    @ui.button(label="Iscriviti", style=discord.ButtonStyle.success, custom_id="wheel_join")
    async def join_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id in self.players:
            await interaction.response.send_message("Sei già iscritto alla ruota.", ephemeral=True)
            return
        self.players[interaction.user.id] = interaction.user
        await interaction.response.edit_message(embed=self.lobby_embed(), view=self)

    @ui.button(label="Esci", style=discord.ButtonStyle.secondary, custom_id="wheel_leave")
    async def leave_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id not in self.players:
            await interaction.response.send_message("Non sei iscritto alla ruota.", ephemeral=True)
            return
        del self.players[interaction.user.id]
        await interaction.response.edit_message(embed=self.lobby_embed(), view=self)

    @ui.button(label="Start", style=discord.ButtonStyle.primary, custom_id="wheel_start")
    async def start_button(self, interaction: discord.Interaction, button: ui.Button):
        if not self.can_control(interaction.user):
            await interaction.response.send_message("Solo chi partecipa o chi ha creato la ruota può avviarla.", ephemeral=True)
            return
        if len(self.players) < MIN_PLAYERS:
            await interaction.response.send_message(f"Servono almeno {MIN_PLAYERS} giocatori per far girare la ruota.", ephemeral=True)
            return

        self.running = True
        self.join_button.disabled = self.leave_button.disabled = self.start_button.disabled = True
        self.stop_button.disabled = False
        await interaction.response.edit_message(embed=self.build_embed("🎡 La ruota sta per girare...", "Preparatevi!"), view=self)
        await self.run(interaction.message)

    @ui.button(label="Stop", style=discord.ButtonStyle.danger, custom_id="wheel_stop")
    async def stop_button(self, interaction: discord.Interaction, button: ui.Button):
        if not self.can_control(interaction.user):
            await interaction.response.send_message("Solo chi partecipa o chi ha creato la ruota può fermarla.", ephemeral=True)
            return
        self.stopped = True
        await interaction.response.defer()

    async def run(self, message: discord.Message):
        try:
            while len(self.players) > 1 and not self.stopped:
                for _ in range(SPIN_FRAMES):
                    if self.stopped:
                        break
                    name = random.choice(list(self.players.values())).display_name
                    await message.edit(embed=self.build_embed("🎡 La ruota gira...", f"➡️ **{name}**"))
                    await asyncio.sleep(SPIN_DELAY)
                if self.stopped:
                    break

                loser = random.choice(list(self.players.values()))
                del self.players[loser.id]
                self.eliminated.append(loser)
                await message.edit(embed=self.build_embed("🎡 La ruota si è fermata", f"💀 **{loser.display_name}** è stato eliminato!"))
                await asyncio.sleep(ROUND_DELAY)

            if self.stopped and len(self.players) > 1:
                embed = self.build_embed("⏹️ Ruota fermata", "Qualcuno ha fermato la ruota prima della fine.")
            else:
                winner = next(iter(self.players.values()))
                embed = self.build_embed("🏆 Ruota conclusa", f"{winner.mention} è l'ultimo rimasto!")
            self.end_view()
            await message.edit(embed=embed, view=self)
        except discord.NotFound:
            self.end_view()  # Il messaggio è stato cancellato

    async def on_timeout(self):
        # Scatta solo se nessuno ha interagito con i bottoni per 30 minuti
        if self.running or self.message is None:
            return
        self.end_view()
        try:
            await self.message.edit(embed=self.build_embed("🎡 Ruota scaduta", "Nessuno l'ha avviata in tempo."), view=self)
        except discord.NotFound:
            pass


class Wheel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="wheel", description="Fai girare la ruota ed elimina un giocatore alla volta")
    @app_commands.guild_only()
    async def wheel(self, interaction: discord.Interaction):
        view = WheelView(interaction.user)
        await interaction.response.send_message(embed=view.lobby_embed(), view=view)
        view.message = await interaction.original_response()


async def setup(bot: commands.Bot):
    await bot.add_cog(Wheel(bot))
