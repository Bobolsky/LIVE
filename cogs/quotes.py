import random
from datetime import timedelta
from io import StringIO
import discord
from discord import app_commands
from discord.ext import commands
from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter
from db import db
from settings import CITAZIONI_CHANNEL_ID


def get_max_id_cit():
    docs = db.collection('citazioni').order_by("id", direction=firestore.Query.DESCENDING).limit(1).get()
    return docs[0].to_dict().get("id") if docs else 0


# Import una tantum della cronologia del canale citazioni nel DB
async def save_channel_messages_to_db(channel):
    messages = [message async for message in channel.history(limit=2000)]

    citazioni_ref = db.collection('citazioni')
    print("Inizio Caricamento")
    for i, message in enumerate(messages):
        if message.content:  # Esclude messaggi vuoti
            citazioni_ref.add({
                'author': message.author.display_name,
                'content': message.content,
                'id': i
            })

    print("Messaggi salvati correttamente nel database.")


class Quotes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.max_id = 0

    async def cog_load(self):
        self.max_id = get_max_id_cit()
        print(self.max_id)

    # Cooldown di /cit e /parla
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            # Formatta il tempo rimanente in ore e minuti
            time_left = timedelta(seconds=int(error.retry_after))
            hours, remainder = divmod(int(time_left.total_seconds()), 3600)
            minutes = remainder // 60
            cooldown_message = f"Rispetta il Cooldown! Puoi usare di nuovo il comando tra {hours} ore e {minutes} minuti."
            await interaction.response.send_message(cooldown_message, ephemeral=True)

    @app_commands.command(name="cit", description="Ricorda una citazione casuale")
    @app_commands.checks.cooldown(1, 36000)
    async def cit(self, interaction: discord.Interaction):
        citazioni_ref = db.collection('citazioni')

        # Le citazioni usate vengono eliminate, quindi l'ID estratto potrebbe non esistere più:
        # prendi la prima citazione con ID >= a quello estratto, altrimenti l'ultima prima di esso
        random_id = random.randint(1, max(self.max_id, 1))
        query = citazioni_ref.where(filter=FieldFilter("id", ">=", random_id)).order_by("id").limit(1).get()
        if not query:
            query = citazioni_ref.where(filter=FieldFilter("id", "<", random_id)).order_by("id", direction=firestore.Query.DESCENDING).limit(1).get()

        if not query:
            await interaction.response.send_message("Nessuna citazione trovata.")
            return

        citazione_random = query[0].to_dict().get("content", "Nessuna citazione trovata.")
        query[0].reference.delete()
        await interaction.response.send_message(f"{citazione_random}")

    # Salva nel DB i nuovi messaggi del canale citazioni
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id != CITAZIONI_CHANNEL_ID or message.author.bot:
            return

        self.max_id += 1
        db.collection('citazioni').add({
            'author': message.author.display_name,
            'content': message.content,
            'id': self.max_id
        })
        print(f"Citazione aggiunta al database con ID {self.max_id}!")

    @app_commands.command(name="parla", description="Dai voce al nostro amato BOT LIVE")
    @app_commands.checks.cooldown(1, 36000)
    async def parla(self, interaction: discord.Interaction):
        frasi = db.collection('frasi').get()

        if not frasi:
            await interaction.response.send_message("Non ci sono frasi disponibili al momento.")
            return

        frase_casuale = random.choice(frasi)
        stringa = frase_casuale.to_dict().get('stringa', 'Nessuna stringa trovata.')

        await interaction.response.send_message(stringa)

        # Elimina l'entry dal database
        try:
            frase_casuale.reference.delete()
            print("Frase eliminata con successo dal database.")
        except Exception as e:
            print(f"Errore durante l'eliminazione della frase dal database: {str(e)}")

    @app_commands.command(name="frase", description="Aggiungi una frase alla collezione")
    async def frase(self, interaction: discord.Interaction, frase_da_aggiungere: str):
        db.collection("frasi").add({"stringa": frase_da_aggiungere})
        await interaction.response.send_message("Frase aggiunta con successo al database!", ephemeral=True)

    @app_commands.command(name="listafrasi", description="Restituisci un file TXT con la lista delle frasi")
    async def lista_frasi(self, interaction: discord.Interaction):
        frasi_io = StringIO()
        frasi_io.write("Lista delle Frasi:\n\n")

        for doc in db.collection("frasi").stream():
            frase = doc.to_dict().get("stringa", "Frase non disponibile")
            frasi_io.write(f"{frase}\n")

        frasi_io.seek(0)
        await interaction.response.send_message(
            file=discord.File(fp=frasi_io, filename="frasi.txt"),
            content="Ecco la lista delle frasi:",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Quotes(bot))
