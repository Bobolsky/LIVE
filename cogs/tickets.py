import io
import discord
from discord import ui
from discord.ext import commands
from firebase_admin import firestore
from db import db
from settings import TICKET_CHANNEL_ID, TRANSCRIPT_CHANNEL_ID, ADMIN_ROLE_ID, PRESIDENT_ROLE_ID

# Le view sono persistenti (timeout=None + custom_id) e registrate all'avvio, quindi non possono
# tenere stato in memoria: utente e ticket vengono ricavati dal canale su cui si clicca.


def get_ticket_ref(channel: discord.TextChannel):
    # Il canale si chiama "🆘︱ticket-<id>", lo stesso id del documento su Firestore
    ticket_id = channel.name.rsplit("-", 1)[-1]
    return db.collection('tickets').document(ticket_id)


def get_ticket_user(channel: discord.TextChannel):
    # L'utente che ha aperto il ticket è l'unico membro (non bot) con permessi specifici sul canale
    for target in channel.overwrites:
        if isinstance(target, discord.Member) and not target.bot:
            return target
    return None


def is_staff(member: discord.Member):
    return any(role.id in (ADMIN_ROLE_ID, PRESIDENT_ROLE_ID) for role in member.roles)


class TicketButton(ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Il bottone rimane sempre attivo

    @ui.button(label="Crea Ticket", style=discord.ButtonStyle.red, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: ui.Button):
        guild = interaction.guild
        user = interaction.user
        role_admin = guild.get_role(ADMIN_ROLE_ID)
        role_president = guild.get_role(PRESIDENT_ROLE_ID)

        # Ottieni il ticket con l'ID più alto dal Firestore
        tickets_ref = db.collection('tickets')
        docs = tickets_ref.order_by('__name__', direction=firestore.Query.DESCENDING).limit(1).get()
        ticket_id = int(docs[0].id) if docs else 500

        next_ticket_id = ticket_id + 1
        print(next_ticket_id)
        tickets_ref.document(str(next_ticket_id)).set({'id': next_ticket_id})

        # Crea un canale con permessi specifici
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            role_admin: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            role_president: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f"🆘︱ticket-{next_ticket_id}",
            position=0,
            overwrites=overwrites
        )

        await interaction.response.send_message(f"Il tuo ticket è stato creato: {ticket_channel.mention}", ephemeral=True)
        await ticket_channel.send(f"Benvenuto {user.mention}, di cosa hai bisogno?\n", view=TicketCloseButton())


class TicketCloseButton(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Chiudi Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        ticket_channel = interaction.channel
        user = get_ticket_user(ticket_channel)

        # Può chiudere il ticket l'utente che l'ha creato oppure un admin/presidente
        if interaction.user == user:
            message = "Hai chiuso il ticket. Gli admin e il Presidente possono ancora accedervi."
        elif is_staff(interaction.user):
            message = "Hai chiuso il ticket. L'utente è stato rimosso."
        else:
            return

        await interaction.response.send_message(message, ephemeral=True)
        if user:
            await ticket_channel.set_permissions(user, view_channel=False)  # Rimuovi l'utente dal canale

        # Aggiungi il bottone di gestione per admin e presidente
        await ticket_channel.send("", view=TicketAdminButtons())


class TicketAdminButtons(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Riapri Ticket", style=discord.ButtonStyle.success, custom_id="reopen_ticket")
    async def reopen_ticket(self, interaction: discord.Interaction, button: ui.Button):
        user = get_ticket_user(interaction.channel)
        if user is None:
            await interaction.response.send_message("L'utente che ha aperto il ticket non è più nel server.", ephemeral=True)
            return
        await interaction.channel.set_permissions(user, view_channel=True, send_messages=True)
        await interaction.response.send_message("Il ticket è stato riaperto.", ephemeral=True)

    @ui.button(label="Salva ed Elimina", style=discord.ButtonStyle.red, custom_id="close_ticket_permanently")
    async def close_ticket_permanently(self, interaction: discord.Interaction, button: ui.Button):
        ticket_channel = interaction.channel
        messages = [msg async for msg in ticket_channel.history(limit=1000)]

        # Filtra i messaggi, evitando quelli del bot
        filtered_messages = [
            f"[{message.created_at.strftime('%d/%m/%Y')}] [{message.created_at.strftime('%H:%M')}]{message.author.display_name}: {message.content}"
            for message in messages
            if message.author.name != 'LIVE' or message.author.discriminator != '0011'
        ]
        # Inverti l'ordine dei messaggi per mettere il più vecchio all'inizio
        filtered_messages.reverse()

        transcript = io.StringIO()
        for msg in filtered_messages:
            transcript.write(f"{msg}\n")
        transcript.seek(0)

        # Salva il trascritto nel Firestore
        get_ticket_ref(ticket_channel).set({'transcript': transcript.getvalue()})

        file_channel = interaction.client.get_channel(TRANSCRIPT_CHANNEL_ID)
        await file_channel.send(
            file=discord.File(fp=transcript, filename=f"{ticket_channel.name}_transcript.txt"),
            content=""
        )
        await interaction.response.send_message("Il trascritto è stato inviato nel canale specificato.", ephemeral=True)

        await ticket_channel.delete()


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.panel_checked = False

    async def cog_load(self):
        # Registra le view persistenti, così i bottoni funzionano anche dopo un riavvio
        self.bot.add_view(TicketButton())
        self.bot.add_view(TicketCloseButton())
        self.bot.add_view(TicketAdminButtons())

    @commands.Cog.listener()
    async def on_ready(self):
        # on_ready scatta a ogni riconnessione: controlla il pannello una sola volta
        if self.panel_checked:
            return
        self.panel_checked = True

        channel = self.bot.get_channel(TICKET_CHANNEL_ID)
        if channel is None:
            print("Canale ticket non trovato.")
            return

        # Non ripubblicare il pannello se esiste già
        async for message in channel.history(limit=10):
            if message.author == self.bot.user and message.components:
                return

        await channel.send("", file=discord.File("Support.png"))
        embed = discord.Embed(
            description="**Clicca sul bottone ''Crea Ticket'' per ricevere assistenza, ricordiamo anche la possibilità di un'assistenza vocale su richiesta! 💌**",
            color=0xFF0000
        )
        embed.set_footer(text="-Gigginovic", icon_url=None)
        await channel.send(embed=embed, view=TicketButton())


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
