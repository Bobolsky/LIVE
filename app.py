from discord import app_commands
import discord 
from discord.ext import commands
import asyncio
import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime, time, timedelta
from discord.ext import tasks
from discord import app_commands, ui
from config import TOKEN
import io
from google.cloud.firestore_v1 import FieldFilter
import yt_dlp as youtube_dl
import urllib.parse, urllib.request, re
from zoneinfo import ZoneInfo
from io import StringIO
import os
import aiohttp
import logging

# Inizializzazione di Firebase
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Inizializzazione Bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
TICKET_CHANNEL_ID = 1283478923925262357 # CHANGEID
global TICKET_ID 
TICKET_ID = 500
global max_id
sfida_in_corso = None
rome_tz = ZoneInfo("Europe/Rome")
last_video_ids = {}
medal_users=['154233863','60469834','6577771']
# Lista di comandi disponibili
games_list = [
    "Pallavolo con Stebo00",
    "Ping Pong con Alesibo",
    "Golf",
    "Lethal Company con i Frat-m",
    "Coding con Iannacetor",
    "Monster Hunter con Fransmalth",
    "Zelda con Fransmalth",
    "Hot Wheels",
    "Assetto Corsa",
    "Palia",
    "xDefiant",
    "Clash of Clans",
    "Neverwinter",
    "Little Big Planet 2",
    "Rust",
    "Minecraft",
    "League of Legends",
    "Fall Guys",
    "Genshin Impact",
    "Clash of Clans",
    "Deep Rock Galactic",
    "FiveM",
    "Fortnite",
    "Red Dead Redemption",
    "Elden Ring",
    "Poker",
    "Rocket League",
    "CSGO",
    "Valorant",
    "F1® 25",
    "Grounded", 
    "PUBG",
    "Krunker.io",
    "Portal 2",
    "PES 2006",
    "FIFA 25",
    "NBA 2K25",
    "Among Us",
    "Assasin's Creed",
    "Pokémon Rosso Fuoco",
    "Pokémon Smeraldo",
    "Pokémon Diamante",
    "Pokémon Platino",
    "Pokémon SoulSiver",
    "Pokémon Bianco",
    "PokeMMO",
    "Tamagotchi",
    "Nintendogs",
    "Grand Theft Auto: San Andreas",
    "Grand Theft Auto V",
    "Grand Theft Auto VI",
    "The Sims 4",
    "Bugs Bunny & Taz In Viaggio nel Tempo",
    "Bugs Bunny Lost In Time",
    "Crash Bandicoot",
    "Crash Bash",
    "Crash Team Racing",
    "Croc 1 Legend of the Gobbos",
    "Croc 2",
    "Hercules",
    "Kirikou",
    "Monster & Co",
    "Pink Panther",
    "Spiderman",
    "Spyro: Reignited Trilogy",
    "Crash Bandicoot: N. Sane Trilogy",
    "Tarzan",
    "Tom And Jerry",
    "Toy Story",
    "Small Soldiers",
    "Agent Hugo",
    "Alien Hominid",
    "Asterix & Obelix XXL",
    "Barbie",
    "Barnyard Il Cortile",
    "Bionicle",
    "Boog & Elliot",
    "Bowling",
    "Bully",
    "Disney-Pixar Cars",
    "Cell Damage Overdrive",
    "DragonBall Z Budokai",
    "Driv3r",
    "Mobile Suit Gundam - Federation vs. Zeon",
    "The Incredible Hulk",
    "Saint Seiya - The Sanctuary",
    "Jak and Daxter",
    "Klonoa",
    "Ratchet Gladiator",
    "Robots",
    "Sitting Ducs",
    "Sly Raccoon",
    "Simpsons, The - Hit & Run",
    "Spongebob e Quello",
    "Superman Returns",
    "The Italian Job",
    "Tekken 4",
    "Vampire Night"
    "Burnout 3: Takedown", 
    "War Chess",
    "Teenage Mutant Ninja Turtles 2 Battle Nexus",
    "Maximo",
    "Power Rangers Super Legends",
    "Call of Duty: Modern Warfare",
    "Call of Duty: World at War",
    "Call of Duty: Modern Warfare 2",
    "Call of Duty: Modern Warfare 3",
    "Call of Duty: Black Ops",
    "Call of Duty: Black Ops II",
    "Call of Duty: Ghosts",
    "Dirt 2",
    "The Ratchet & Clank Trilogy",
    "The Jak and Daxter Trilogy",
    "Dante's Inferno",
    "Toy Story 3: Il videogioco",
    "Madagascar Kartz",
    "Ratchet & Clan: QForce",
    "Turok",
    "Army of Two",
    "Mafia II",
    "Termination Salvation",
    "Fifa Street",
    "Beach Soccer",
    "calcetto",
    "Fifa Street con zinno",
    "Rust con SuperVista_",
    "Football Manager con Rolgio",
    "FiveM con Gigginovic",
    "zombie con GenTen",
    "scacchi vs King",
    "FantaLive",
    "Beach Soccer con il DUOK",
    "calcetto con gli Sciacalli",
    "calcetto con gli Zood",
    "Garfield",
    "Lego Indiana Jones - The Original Adventures",
    "Lego Batman",
    "Rayman Raving Rabbits",
    "It Takes Two",
    "Portal 2 ",
    "Overcooked 1",
    "Overcooked 2",
    "Biped",
    "We Were Here",
    "We Were Here Too",
    "We Were Here Together",
    "We Were Here Forever",
    "We Were Here Expeditions: The FriendShip",
    "Haven",
    "A Way Out",
    "Lego Batman",
    "Sackboy: A Big Adventure",
    "Super Mario 3D World ",
    "Unravel Two",
    "Blanc",
    "Looney Tunes Acme Arsenal",
    "Human Fall Flat",
    "Tomb Raider I",
    "Tomb Raider II",
    "Tomb Raider III",
    "Brothers: A Tale of Two Sons Remake",
    "Stuart Little 3 - Big Photo Adventure",
    "Meta Quest 3"
]
watching_list = [
    "La società della neve",
    "Il petroliere",
    "Barbie",
    "Lunetta sbavare",
    "OLD",
    "Dune",
    "Dune - Parte due",
    "Memento",
    "The Butterfly Effect",
    "Zathura - Un'avventura spaziale",
    "Due Fantagenitori",
    "Batman of the Future",
    "Leone il Cane Fifone",
    "SamSam",
    "Jurassic Park",
    "Spirit",
    "Fight Club",
    "Interstellar",
    "Lilo & Stitch",
    "Koda, fratello orso",
    "Chicken Little - Amici per le penne",
    "I Robinson - Una famiglia spaziale",
    "Bolt - Un eroe a quattro zampe",
    "Le follie dell'imperatore",
    "Dinosauri",
    "Toy Story",
    "A Bug’s Life",
    "Alla ricerca di Nemo",
    "Gli Incredibili",
    "Ratatouille",
    "Wall E",
    "Up",
    "Inside Out",
    "Spider-Man 3",
    "Guardiani della Galassia",
    "Hulk",
    "Batman Begins",
    "I Celestini",
    "Arcane",
    "Squid Game",
    "Pinocchio",
    "La carica dei cento e uno",
    "Il libro della giungla",
    "Le avventure di Winnie the Pooh",
    "Red e Toby – Nemiciamici",
    "Mucca e pollo",
    "Topolino",
    "Baby Looney Tunes",
    "Le Corse Pazze",
    "Looney Tunes",
    "Johnny Bravo",
    "Il Laboratorio di Dexter",
    "Le Superchicche",
    "Ed, Edd n Eddy",
    "Le tenebrose avventure di Billy e Mandy",
    "Piccoli Brividi",
    "Ultimate Muscle",
    "Scooby-Doo",
    "Austin & Ally",
    "A Casa di Raven",
    "Lizzie McGuire",
    "The Sleepover Club",
    "Zack e Cody al grand Hotel",
    "Hannah Montana",
    "I maghi di Waverly",
    "Il Mondo di Patty",
    "Buona Fortuna Charlie",
    "Victorious",
    "Toy Story - Il mondo dei giocattoli",
    "Attack on Titan",
    "Death Note",
    "YouTube",
    "Twitch",
    "Seria A",
    "Space Jam",
    "Power Rangers Wild Force",
    "Doraemon",
    "Phineas e Ferb",
    "Teen Titans",
    "Flintstones",
    "Pingu",
    "Trenino Thomas",
    "Braccio di Ferro",
    "Heidi",
    "Shrek",
    "Simpson",
    "Donnie Darko",
    "Avatar",
    "Challengers",
    "Il castello errante di Howl",
    "Jujutsu kaisen",
    "One Piece",
    "una Kong Strong",
    "il PC di Zinno",
    "Chris Life",
    "Little Einstein",
    "Spongebob",
    "Totally Spies",
    "Mr Bean",
    "Holly e Benji"
]
listening_list = [
    "S&S",
    "Schujattulino",
    "Macchina Mia",
    "Monzesi",
    "Natiellobbello",
    "Fish 'n' Chips",
    "Scottrap",
    "BRT",
    "11/10",
    "BJ",
    "papi",
    "Senza Respiro",
    "absolute in doubt",
    "All Alone",
    "Automatic",
    "Better Ways",
    "boost",
    "Chemical Release",
    "Comptine d'un Autre été: L'Après-Midi",
    "Consequence",
    "crash & burn",
    "Crave Me",
    "A Different Age",
    "ectsacy",
    "Falling Down",
    "Falling Stars",
    "Feels Like We Only Go Backwards",
    "Haunt u",
    "How I got depressed",
    "Icarus",
    "Idfc",
    "I Miss You",
    "Karma Police",
    "Kill Myself",
    "La morte di rinquore",
    "Let Me Die",
    "lil numb",
    "little queen",
    "Long Nights",
    "Lo Que Siento",
    "Low",
    "Monday",
    "my revenge",
    "Neve",
    "No Name",
    "Nuts",
    "Obstacles",
    "Only u",
    "Radioactive",
    "Sail",
    "Save Me",
    "Save That Shit",
    "scars",
    "Smile",
    "Stop Crying Your Heart Out",
    "Survive",
    "Sweather Weather",
    "Teen Romance",
    "tinted green",
    "Tumblr Girls",
    "U & I",
    "we think too much",
    "Where Is My Mind?",
    "Senza e' te",
    "Wish you Were Here",
    "Me Gustas Tu",
    "Papaya"
]


# Task loop per cambiare lo status del bot
@tasks.loop(hours=1)  # Cambia ogni 30 secondi
async def change_status():  
    # Definisci le tue liste
    status_lists = [games_list, watching_list, listening_list]  # Esempio di liste
    
    # Seleziona una lista casuale
    random_list = random.choice(status_lists)
    
    # Seleziona un comando casuale dalla lista scelta
    random_command = random.choice(random_list)
    
    # Cambia lo stato del bot
    

    


    # Controlla quale lista è stata scelta e cambia l'intervallo
    if random_list == listening_list:
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=random_command))
        change_status.change_interval(minutes=30)  # Cambia intervallo a 30 minuti
    elif random_list == watching_list:
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=random_command))
        discord.ActivityType.custom
        change_status.change_interval(hours=1)  # Cambia intervallo a 2 ore
    else:
        await client.change_presence(activity=discord.Game(name=random_command))  # Sta giocando
        change_status.change_interval(hours=1)  # Cambia intervallo a 2 ore 

async def get_max_id_cit():
    citazioni_ref = db.collection('citazioni')
    docs = citazioni_ref.order_by("id", direction=firestore.Query.DESCENDING).limit(1).get()
    
    max_id = docs[0].to_dict().get("id")
    return max_id

async def save_channel_messages_to_db(channel):
    # Lista di tutti i messaggi del canale
    messages = [message async for message in channel.history(limit=2000)]

    # Collezione di citazioni
    citazioni_ref = db.collection('citazioni')
    print("Inizio Caricamento")
    # Aggiungi ogni messaggio come documento separato nel DB
    for i, message in enumerate(messages):
        if message.content:  # Esclude messaggi vuoti
            citazione_data = {
                'author': message.author.display_name,
                'content': message.content,
                'id':i
            }
            # Salva nel DB con un ID unico generato automaticamente
            citazioni_ref.add(citazione_data)


    print("Messaggi salvati correttamente nel database.")

@client.event
async def on_ready():
    global max_id
    
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} commands")
        check_birthdays.start()
        change_status.start()
        #check_medal_users_videos.start()
        max_id = await  get_max_id_cit()
        print(max_id)
        #await save_channel_messages_to_db(client.get_channel(715023970700623874))
    except Exception as e:
        print(e)

    print(f"Bot connesso come {client.user}")
    channel = client.get_channel(TICKET_CHANNEL_ID)
    
    # Controlla se il messaggio esiste già
    '''async for message in channel.history(limit=10):
        if message.author == client.user and message.content == "Premi il bottone per creare un ticket.":
            return  # Non fare nulla se il messaggio esiste già'''
        
    # Invia il messaggio con il bottone
    await channel.send("", file=discord.File("Support.png"))

    embed = discord.Embed(
        description="**Clicca sul bottone ''Crea Ticket'' per ricevere assistenza, ricordiamo anche la possibilità di un'assistenza vocale su richiesta! 💌**",
        color=0xFF0000
    )
    embed.set_footer(text="-Gigginovic", icon_url=None)
    await channel.send(embed=embed, view=TicketButton())


@tasks.loop(seconds=30)  # Controlla ogni 30 secondi
async def check_medal_users_videos():
    url_base = "https://developers.medal.tv/v1/latest?limit=1"
    headers = {'Authorization': 'pub_4fJs7veQ3yFWSnvL8nxG9aQ8maQIdlFd'}
    print("CONTROLLO")
    for user_id in medal_users:
        url = f"{url_base}&userId={user_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    print(data)
                    if data and data['contentObjects']:
                        video = data['contentObjects'][0]
                        video_id = video['contentId']  # Ottieni l'ID del video
                        
                        # Verifica se è un nuovo video
                        if last_video_ids.get(user_id) != video_id:
                            last_video_ids[user_id] = video_id  # Aggiorna l'ID dell'ultimo video
                            video_url = video['directClipUrl']

                            # Trova il canale testuale
                            channel = client.get_channel(744756058383319105)
                            if channel:
                                await channel.send(video_url)
                else:
                    print(f"Errore durante la richiesta all'API: {response.status}")

@tree.command(name="cit", description="Ricorda una citazione casuale!")
@app_commands.checks.cooldown(1,36000)
async def cit(interaction: discord.Interaction):
    
    citazioni_ref = db.collection('citazioni')
    
    
    # Seleziona un ID casuale tra 1 e il massimo
    random_id = random.randint(1, max_id)
    # Esegui una query per ottenere la citazione con l'ID selezionato
    query = citazioni_ref.where(filter=FieldFilter("id", "==", random_id)).get()
    
    citazione_random = query[0].to_dict().get("content", "Nessuna citazione trovata.")

    query[0].reference.delete()
    # Rispondi con la citazione casuale
    await interaction.response.send_message(f"{citazione_random}")


# Cooldown parla
@cit.error
async def on_cit_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        # Ottieni i secondi rimanenti dal cooldown
        time_left = timedelta(seconds=int(error.retry_after))
        # Formatta il tempo in ore e minuti
        hours, remainder = divmod(int(time_left.total_seconds()), 3600)
        minutes = remainder // 60
        cooldown_message = f"Rispetta il Cooldown! Puoi usare di nuovo il comando tra {hours} ore e {minutes} minuti."
        await interaction.response.send_message(cooldown_message, ephemeral=True)

# Comando parla
@tree.command(name="parla", description="Dai voce al nostro amato BOT LIVE!")
@app_commands.checks.cooldown(1, 36000)
async def parla(interaction: discord.Interaction):
    frasi_ref = db.collection('frasi')
    frasi = frasi_ref.get()

    if not frasi:
        await interaction.response.send_message("Non ci sono frasi disponibili al momento.")
        return

    frase_casuale = random.choice(frasi)
    stringa = frase_casuale.to_dict().get('stringa', 'Nessuna stringa trovata.')

    await interaction.response.send_message(stringa) #
    sergio = client.get_user(159058177189478401)
    sara = client.get_user(687406239684362282)


    # Elimina l'entry dal database
    try:
        frase_casuale.reference.delete()
        print("Frase eliminata con successo dal database.")
    except Exception as e:
        print(f"Errore durante l'eliminazione della frase dal database: {str(e)}")

# Cooldown parla
@parla.error
async def on_parla_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        # Ottieni i secondi rimanenti dal cooldown
        time_left = timedelta(seconds=int(error.retry_after))
        # Formatta il tempo in ore e minuti
        hours, remainder = divmod(int(time_left.total_seconds()), 3600)
        minutes = remainder // 60
        cooldown_message = f"Rispetta il Cooldown! Puoi usare di nuovo il comando tra {hours} ore e {minutes} minuti."
        await interaction.response.send_message(cooldown_message, ephemeral=True)

# Aggiungi frase al parla
@tree.command(name="frase", description="Aggiungi una frase alla collezione.")
async def frase(interaction: discord.Interaction, frase_da_aggiungere: str):

    # Aggiungi la frase alla collezione "frasi" nel database Firestore
    db.collection("frasi").add({"stringa": frase_da_aggiungere})

        # Conferma che la frase è stata aggiunta
    await interaction.response.send_message("Frase aggiunta con successo al database!",ephemeral=True)
    
@tree.command(name="listafrasi", description="Restituisci un file TXT con la lista delle frasi.")
async def lista_frasi(interaction: discord.Interaction):
    # Crea un oggetto StringIO per il file TXT
    frasi_io = StringIO()
    frasi_io.write("Lista delle Frasi:\n\n")

    # Ottieni tutti i documenti dalla collezione "frasi"
    frasi_ref = db.collection("frasi")
    docs = frasi_ref.stream()

    # Scrivi le frasi nel file
    for doc in docs:
        data = doc.to_dict()
        frase = data.get("stringa", "Frase non disponibile")
        frasi_io.write(f"{frase}\n")

    # Riavvolgi il cursore del StringIO
    frasi_io.seek(0)

    # Invia il file come allegato
    await interaction.response.send_message(
        file=discord.File(fp=frasi_io, filename="frasi.txt"),
        content="Ecco la lista delle frasi:",
        ephemeral=True
    )

# Benvenuto
@client.event
async def on_member_join(member):
    # Canale dove verrà inviato il messaggio di benvenuto
    channel = client.get_channel(687431352626184205)  
    
    if channel:
        # Messaggio di benvenuto inviato al canale specifico
        await channel.send(f"Benvenuto {member.mention} nella Famiglia LIVE! <:LIVE:772499018831233034>")
    # Ruoli di default da assegnare
    role_ids = [1054765383669776464, 1054767452443131935, 1054767463469948989, 690156064972472345]  # Sostituisci con gli ID dei ruoli che vuoi assegnare

    roles = [member.guild.get_role(role_id) for role_id in role_ids]

    # Aggiungi i ruoli all'utente
    for role in roles:
        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                print(f"Non ho il permesso di aggiungere il ruolo {role.name} a {member.name}.")
            except discord.HTTPException as e:
                print(f"Errore durante l'aggiunta del ruolo {role.name} a {member.name}: {str(e)}")

# Addio
@client.event
async def on_member_remove(member):
    # Canale dove verrà inviato il messaggio di addio
    channel = client.get_channel(826784552944664636) 
    
    if channel:
        # Messaggio di addio inviato al canale specifico
        await channel.send(f'**{member.name}** è morto. :skull:')

# Remind
@tree.command(name='remind', description='Imposta un promemoria')
async def remind(interaction: discord.Interaction, 
                 time: str, 
                 date: str = None, 
                 mentions: str = None,  # Cambiato da 'mention' a 'mentions'
                 message: str = ''):
    try:
        # Usa la data odierna se non viene specificata una data
        if date is None:
            date = datetime.now().strftime("%d/%m/%Y")
        else:
            date = datetime.strptime(date, "%d/%m/%Y").strftime("%d/%m/%Y")
        
        # Se viene specificata solo l'ora senza i minuti
        if ":" not in time:
            time += ":00"
        
        # Combina data e ora in un oggetto datetime
        event_time = datetime.strptime(f"{date} {time}", "%d/%m/%Y %H:%M")
        
        # Calcola il tempo del promemoria
        remind_time = event_time
        current_time = datetime.now()

        if remind_time < current_time:
            await interaction.response.send_message("Non puoi impostare un promemoria per un evento passato!", ephemeral=True)
            return

        # Calcola il tempo da aspettare
        delay = (remind_time - current_time).total_seconds()
        print(delay)
        # Conferma la creazione del promemoria
        await interaction.response.send_message(f"Promemoria impostato per {event_time.strftime('%d/%m/%Y %H:%M')}!", ephemeral=True)

        # Programma il messaggio di promemoria
        asyncio.create_task(schedule_reminder(interaction, delay, message, mentions=mentions))

    except ValueError:
        await interaction.response.send_message("Formato della data o dell'ora non valido. Usa il formato DD/MM/YYYY HH:MM", ephemeral=True)

async def schedule_reminder(interaction, delay, message, mentions=None):
    await asyncio.sleep(delay)
    print(delay)

    # Prepara la lista delle menzioni
    if mentions:
        mention_list = mentions.split()
        mentions_to_send = []
        for mention in mention_list:
            if mention.startswith("<@&"):  # Riconosce un ruolo
                role_id = int(mention[3:-1])
                role = discord.utils.get(interaction.guild.roles, id=role_id)
                if role:
                    mentions_to_send.append(role.mention)
            elif mention.startswith("<@"):  # Riconosce un membro
                user_id = int(mention[2:-1])
                member = await interaction.guild.fetch_member(user_id)
                if member:
                    mentions_to_send.append(member.mention)
            else:
                # Gestione del caso in cui la menzione non è valida
                continue
        
        mention_string = " ".join(mentions_to_send)
        await interaction.channel.send(f":bell: {mention_string} **{message}** :bell:")
    else:
        await interaction.channel.send(f":bell: **{message}** :bell:")

@tree.command(name="listacompleanni", description="Restituisci un file TXT con la lista dei compleanni.")
async def lista_compleanni(interaction: discord.Interaction):
    # Crea un oggetto StringIO per il file TXT
    compleanni_io = StringIO()
    compleanni_io.write("Lista dei Compleanni:\n\n")

    # Ottieni tutti i documenti dalla collezione "compleanni"
    compleanni_ref = db.collection("compleanni")
    docs = compleanni_ref.stream()

    # Scrivi i compleanni nel file
    for doc in docs:
        data = doc.to_dict()
        user_id = data["user_id"]
        birthday = data["birthday"]

        # Trova il membro nel server usando l'ID
        member = interaction.guild.get_member(user_id)
        member_name = member.display_name if member else "Utente non trovato"

        compleanni_io.write(f"Nome Utente: {member_name}, Compleanno: {birthday}\n")

    # Riavvolgi il cursore del StringIO
    compleanni_io.seek(0)

    # Invia il file come allegato
    await interaction.response.send_message(
        file=discord.File(fp=compleanni_io, filename="compleanni.txt"),
        content="Ecco la lista dei compleanni:",
        ephemeral=True
    )

@tree.command(name="compleanno", description="Aggiungi il compleanno del tuo migliore amico!")
async def compleanno(interaction: discord.Interaction, user: discord.Member, giorno: int, mese: int):

    try:
        # Controlla che il giorno e il mese siano validi
        datetime.strptime(f"{giorno}/{mese}", "%d/%m")
        birthday = normalizza_data(giorno, mese)
        
        # Salva il compleanno nel database Firestore
        user_data = {
            "user_id": user.id,
            "birthday": birthday
        }
        db.collection("compleanni").document(str(user.id)).set(user_data)
        
        await interaction.response.send_message(f"Compleanno salvato con successo per il {giorno}/{mese}!", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("Formato della data non valido. Usa: /compleanno giorno mese", ephemeral=True)

def normalizza_data(giorno: int, mese: int) -> str:
    # Restituisce la data nel formato DD/MM, con due cifre per giorno e mese
    return f"{giorno:02d}/{mese:02d}"

@tasks.loop(time=time(hour=0, minute=0,second=10, tzinfo=rome_tz))  # Esegui il task ogni giorno a mezzanotte
async def check_birthdays():
    today = datetime.today().strftime("%d/%m")
    birthdays_ref = db.collection("compleanni")
    docs = birthdays_ref.stream()
    
    guild_id = 687431352626184202  

    guild = client.get_guild(guild_id)
    
    if guild is None:
        print("Server non trovato.")
        return

    for doc in docs:
        data = doc.to_dict()
        birthday = data["birthday"]
        if birthday == today:
            user_id = data["user_id"]
            user = await guild.fetch_member(user_id)
            
            channel = client.get_channel(687431352626184205)  
            if channel:
                await channel.send(f"Buon compleanno {user.mention}! 🥳 🎉 ❤ 🎂 🧁")


class TicketButton(ui.View):
    def __init__(self, TICKET_ID=500):
        super().__init__(timeout=None)  # Il bottone rimane sempre attivo
        self.TICKET_ID=TICKET_ID 

    @ui.button(label="Crea Ticket", style=discord.ButtonStyle.red, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: ui.Button):
        guild = interaction.guild
        user = interaction.user
        role_admin = guild.get_role(687431600660938754)  
        role_president = guild.get_role(1195727558721945702)
        bot_id = 980487053361958984

        # Ottieni il ticket con l'ID più alto dal Firestore
        tickets_ref = db.collection('tickets')
        docs = tickets_ref.order_by('__name__', direction=firestore.Query.DESCENDING).limit(1).get()

        if docs:
            doc = docs[0]  # Docs è un elenco di documenti
            ticket_id = int(doc.id)  # ID del documento
        else:
            ticket_id = 500

        next_ticket_id = ticket_id + 1
        print(next_ticket_id)
        new_ticket_ref = tickets_ref.document(str(next_ticket_id))
        new_ticket_ref.set({'id': next_ticket_id})
        
        # Crea un canale con permessi specifici
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),  
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),  
            role_admin: discord.PermissionOverwrite(view_channel=True, send_messages=True),   
            role_president: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.get_member(bot_id): discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        # Crea il canale nella categoria specificata
        ticket_channel = await guild.create_text_channel(
            name=f"🆘︱ticket-{next_ticket_id}",
            position=0,  # Imposta la categoria dei ticket
            overwrites=overwrites
        )
        embed = discord.Embed(
            description="Clicca sul bottone **Crea Ticket** qui sotto per ricevere assistenza.",
            color=0xFF0000
        )

        await interaction.response.send_message(f"Il tuo ticket è stato creato: {ticket_channel.mention}", ephemeral=True)
        await ticket_channel.send(
            f"Benvenuto {user.mention}, di cosa hai bisogno?\n"
            "",
            view=TicketCloseButton(user,new_ticket_ref, ticket_channel, role_admin, role_president, guild.get_member(bot_id))
        )
class TicketCloseButton(ui.View):
    def __init__(self, user, new_ticket_ref, ticket_channel, role_admin, role_president, bot):
        super().__init__(timeout=None)  # Il bottone rimane sempre attivo
        self.user = user
        self.ticket_channel = ticket_channel
        self.role_admin = role_admin
        self.role_president = role_president
        self.bot = bot
        self.new_ticket_ref = new_ticket_ref

    @ui.button(label="Chiudi Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: ui.Button):
        # Verifica se l'utente è l'admin o il presidente
        if interaction.user == self.user:

            await interaction.response.send_message("Hai chiuso il ticket. Gli admin e il Presidente possono ancora accedervi.", ephemeral=True)
            await self.ticket_channel.set_permissions(self.user, view_channel=False)  # Rimuovi l'utente dal canale

            # Aggiungi il bottone di gestione per admin e presidente
            await self.ticket_channel.send(
                "",
                view=TicketAdminButtons(self.ticket_channel, self.new_ticket_ref, self.user, self.role_admin, self.role_president, self.bot)
            ) 
        
        
        # Se è l'utente che ha creato il ticket
        elif any(role in interaction.user.roles for role in [self.role_admin, self.role_president]):
            # Se è l'admin o il presidente
            await interaction.response.send_message("Hai chiuso il ticket. L'utente è stato rimosso.", ephemeral=True)
            await self.ticket_channel.set_permissions(self.user, view_channel=False)  # Rimuovi l'utente dal canale
            
            # Mostra il bottone per gestire il ticket solo per admin/presidente
            await self.ticket_channel.send(
                "",
                view=TicketAdminButtons(self.ticket_channel, self.new_ticket_ref, self.user, self.role_admin, self.role_president, self.bot)
            )


class TicketAdminButtons(ui.View):
    def __init__(self, ticket_channel, new_ticket_ref, user, role_admin, role_president, bot):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.user = user
        self.role_admin = role_admin
        self.role_president = role_president
        self.bot = bot
        self.new_ticket_ref = new_ticket_ref

    @ui.button(label="Riapri Ticket", style=discord.ButtonStyle.success, custom_id="reopen_ticket")
    async def reopen_ticket(self, interaction: discord.Interaction, button: ui.Button):    
        await self.ticket_channel.set_permissions(self.user, view_channel=True, send_messages=True)
        await interaction.response.send_message("Il ticket è stato riaperto.", ephemeral=True)
        
    @ui.button(label="Salva ed Elimina", style=discord.ButtonStyle.red, custom_id="close_ticket_permanently")
    async def close_ticket_permanently(self, interaction: discord.Interaction, button: ui.Button):  
        # Scarica il trascritto della chat
        transcript = io.StringIO()
        # Ottieni la cronologia dei messaggi nel canale
        messages = [msg async for msg in self.ticket_channel.history(limit=1000)]

        # Filtra i messaggi, evitando quelli del bot e rimuovendo l'orario
        filtered_messages = [
            f"[{message.created_at.strftime('%d/%m/%Y')}] [{message.created_at.strftime('%H:%M')}]{message.author.display_name}: {message.content}"
            for message in messages
            if message.author.name != 'LIVE' or message.author.discriminator != '0011'
        ]

        # Inverti l'ordine dei messaggi per mettere il più vecchio all'inizio
        filtered_messages.reverse()

        # Scrivi i messaggi filtrati nel transcript
        for msg in filtered_messages:
            transcript.write(f"{msg}\n")
        transcript.seek(0)


        # Salva il trascritto nel Firestore
        self.new_ticket_ref.set({'transcript': transcript.getvalue()})


        # Specifica l'ID del canale dove inviare il file
        file_channel_id = 753385140251525220  # Inserisci l'ID del canale testuale
        file_channel = client.get_channel(file_channel_id)

        
        await file_channel.send(
            file=discord.File(fp=transcript, filename=f"{self.ticket_channel.name}_transcript.txt"),
            content=""
            )
        await interaction.response.send_message("Il trascritto è stato inviato nel canale specificato.", ephemeral=True)
       
        await self.ticket_channel.delete()
       

   
        

        
        
        










@tree.command(name="sfida", description="Sfida il tuo peggior nemico a QUANTO TE LA RISCHI!")
async def sfida(interaction: discord.Interaction, utente_sfidato: discord.Member):
    global sfida_in_corso

    if sfida_in_corso:
        await interaction.response.send_message("C'è già una sfida in corso. Attendi che finisca.", ephemeral=True)
        return

    if interaction.user.id == utente_sfidato.id:
        await interaction.response.send_message(f"{utente_sfidato.mention} è così confuso da sfidarsi da solo!")
        return

    sfida_in_corso = {
        "sfidante": interaction.user,
        "sfidato": utente_sfidato,
        "stato": "in_attesa"
    }

    await interaction.response.send_message(f"**{interaction.user.mention} ha sfidato {utente_sfidato.mention} a QUANTO TE LA RISCHI. {utente_sfidato.mention} di' un numero:**")

async def timeout_sfida(interaction: discord.Interaction):
    global sfida_in_corso
    await asyncio.sleep(60*10)  # Attende 10 minuti
    if sfida_in_corso:
        await interaction.channel.send(f"{sfida_in_corso['sfidato'].mention} non ha risposto entro i 10 minuti e si è rifiutato automaticamente di giocare. Ti aspettiamo in https://discord.com/channels/687431352626184202/1283478923925262357 per chiarimenti.")
        sfida_in_corso = None
        #avvertimenti.clear()  # Resetta gli avvertimenti quando la sfida termina

@tree.command(name="rifiuta", description="Rifiuta la sfida a QUANTO TE LA RISCHI")
async def rifiuta(interaction: discord.Interaction):
    global sfida_in_corso

    if sfida_in_corso and interaction.user == sfida_in_corso["sfidato"]:
        await interaction.response.send_message(f"Ti sei rifiutato di giocare, ti aspettiamo in https://discord.com/channels/687431352626184202/1283478923925262357 per chiarimenti, se necessari.")
        sfida_in_corso = None
    elif sfida_in_corso:
        await interaction.response.send_message("Solo lo sfidato può rifiutare la sfida.", ephemeral=True)
    else:
        await interaction.response.send_message("Non c'è nessuna sfida in corso da rifiutare.", ephemeral=True)

@tree.command(name="ritira", description="Ritirare la sfida a QUANTO TE LA RISCHI")
async def ritira(interaction: discord.Interaction):
    global sfida_in_corso #avvertimenti

    if sfida_in_corso and interaction.user == sfida_in_corso["sfidante"]:
        await interaction.response.send_message(f"{interaction.user.mention} ha ritirato la sfida.")
        sfida_in_corso = None
        #avvertimenti.clear()
    elif sfida_in_corso:
        await interaction.response.send_message("Solo lo sfidante può ritirare la sfida.", ephemeral=True)
    else:
        await interaction.response.send_message("Non c'è nessuna sfida in corso da ritirare.", ephemeral=True)

@client.event
async def on_message(message):
    global sfida_in_corso, num_sfidante, num_sfidato

    if message.channel.id == 715023970700623874 and not message.author.bot:
        citazione = message.content
        
        # Ottieni il documento che tiene traccia del massimo id
        citazioni_ref = db.collection('citazioni')
        
        
        # Incrementa l'ID massimo
        next_id = max_id + 1

        # Aggiungi la citazione al database
        citazione_data = {
                'author': message.author.display_name,
                'content': message.content,
                'id':next_id
            }
        citazioni_ref.add(citazione_data)
        # Aggiorna il valore del massimo id

        # Feedback di conferma nel canale
        print(f"Citazione aggiunta al database con ID {next_id}!")
    if "rifiuta" in message.content:
        pass
    elif sfida_in_corso and message.author.id == sfida_in_corso["sfidato"].id and sfida_in_corso["stato"] == "in_attesa":
        try:
            numero = int(message.content)
            await message.channel.send(f"**OFFICIAL da 1 a {numero}**")
            sfida_in_corso["stato"] = "in_corso"
            
            # Contatta lo sfidante in privato
            await sfida_in_corso["sfidante"].send(f"Dimmi un numero da 1 a {numero}")
            
            # Contatta lo sfidato in privato
            await sfida_in_corso["sfidato"].send(f"Dimmi un numero da 1 a {numero}")
            
            # Imposta una funzione per gestire le risposte private
            def check(m):
                return m.author in [sfida_in_corso["sfidante"], sfida_in_corso["sfidato"]] and m.guild is None
            
            # Attendi le risposte private
            num_sfidante = num_sfidato = None
            for _ in range(2):
                try:
                    risposta = await client.wait_for('message', check=check, timeout=60.0)
                    numero_scelto = int(risposta.content)
                    if 1 <= numero_scelto <= numero:
                        if risposta.author == sfida_in_corso["sfidante"]:
                            num_sfidante = numero_scelto
                        else:
                            num_sfidato = numero_scelto
                    else:
                        await risposta.author.send("Numero non valido. Sfida annullata.")
                        sfida_in_corso = None
                        return
                except asyncio.TimeoutError:
                    await message.channel.send("Tempo scaduto. Sfida annullata.")
                    sfida_in_corso = None
                    return
                except ValueError:
                    await risposta.author.send("Input non valido. Sfida annullata.")
                    sfida_in_corso = None
                    return
                
            # Controlla se i numeri coincidono
            await asyncio.sleep(10) 
            await message.channel.send(
                f"*{sfida_in_corso['sfidato'].mention} ha detto: {num_sfidato}*\n"
                f"*{sfida_in_corso['sfidante'].mention} ha detto: {num_sfidante}*\n\n"
                f"{sfida_in_corso['sfidato'].mention} {'**è stato beccato!**' if num_sfidante == num_sfidato else '**è salvo!**'}"
                )
            
            # Resetta la sfida
            sfida_in_corso = None

        except ValueError:
            await message.channel.send(f"{message.author.mention} Ma non stai giocando? Di' un numero oppure utilizza il comando */rifiuta*.")  



logging.basicConfig(level=logging.INFO)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,  # Permetti il download di playlist
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'scsearch1',  # Cerca su SoundCloud e restituisce il primo risultato
    'source_address': '0.0.0.0'  # Bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')  # Aggiungi questa riga

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        except Exception as e:
            logging.error(f"Errore durante l'estrazione delle informazioni: {e}")
            raise

        if 'entries' in data:
            # Se è una playlist, prendi la prima traccia
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

async def update_status(title):
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=title))

queue = []
current_embed_message = None


def format_duration(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

async def play_next(interaction):
    global current_embed_message
    if queue:
        player = queue[0]  # Modifica qui: non rimuovere il player dalla coda
        interaction.guild.voice_client.play(player[0], after=lambda e: client.loop.create_task(play_next(interaction)))
        await update_status(player[0].title)

        embed = discord.Embed(
        description = (
            f"**<a:Beat:1291564628970704967>︱Titolo: ''{player[0].title}''**\n\n"
            f"**🕛︱Durata: {format_duration(player[0].duration)}**\n\n"
            f"**<:SoundCloud:1291562956974461079>︱[Link SoundCloud]({player[1]})**\n\n" # TO DO
            f"**:bust_in_silhouette:︱Richiesta da:** {interaction.user.mention}"),
            color=0xFF0000
        )

        view = MusicControlView(interaction)
        
        current_embed_message = await interaction.followup.send(embed=embed, view=view)
    else:
        await client.change_presence(activity=None)

class MusicControlView(discord.ui.View):
    def __init__(self, interaction):
        super().__init__(timeout=None)
        self.original_interaction = interaction

    @discord.ui.button(style=discord.ButtonStyle.red, label="", emoji="<:Resume:1291836808895922268>")
    async def play_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await resume(interaction)
        
    @discord.ui.button(style=discord.ButtonStyle.red, label="", emoji="<:Pause:1291836806848839881>")
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await pause(interaction)

    @discord.ui.button(style=discord.ButtonStyle.red, label="", emoji="<:Skip:1291836810699210853>")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()        
        await skip(interaction)

    @discord.ui.button(style=discord.ButtonStyle.red, label="", emoji="<:Quit:1291867636073889802>")
    async def quit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await quit(interaction)

async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.pause()
        
        embed = discord.Embed(
            title="CANZONE SKIPPATA",
            description=f"<:Skip:1291836810699210853>︱{interaction.user.mention} ha skippato la canzone!",
            color=0xFF0000
        )
        await interaction.followup.send(embed=embed)
        
        interaction.guild.voice_client.stop()
        
        if queue:
            queue.pop(0)  # Rimuovi la canzone corrente dalla coda
            await play_next(interaction)
        else:
            await interaction.followup.send("La coda è vuota. Nessuna altra canzone da riprodurre.")
            await client.change_presence(activity=None)
    else:
        await interaction.followup.send("Nessuna canzone in riproduzione da skippare.", ephemeral=True)

async def pause(interaction: discord.Interaction):
    try:
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            embed = discord.Embed(
                title="CANZONE IN PAUSA",
                description=f"<:Pause:1291836806848839881>︱{interaction.user.mention} ha fermato la canzone!",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Nessuna canzone in riproduzione da mettere in pausa.", ephemeral=True)
    except Exception as e:
        logging.error(f"Errore durante la pausa: {e}")
        await interaction.followup.send("Si è verificato un errore durante la pausa della canzone.")

async def resume(interaction: discord.Interaction):
    if interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.resume()
        embed = discord.Embed(
            title="RIPRODUZIONE RIPRESA",
            description=f"<:Resume:1291836808895922268>︱{interaction.user.mention} ha ripreso la riproduzione della canzone!",
            color=0xFF0000
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("Nessuna canzone in pausa da riprendere.")

async def quit(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        queue.clear()
        await interaction.guild.voice_client.disconnect()
        inactivity_check.stop()
        await change_status()
        embed = discord.Embed(
            title="BOT DISCONNESSO",
            description=f"<:Stop:1291867636073889802>︱{interaction.user.mention} ha disconnesso il BOT <@980487053361958984>!",
            color=0xFF0000
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("Il Bot LIVE non è connesso a nessun canale vocale", ephemeral=True)

@tree.command(name='play', description='Riproduci una canzone da SoundCloud')
async def play_command(interaction: discord.Interaction, search: str):
    if not interaction.user.voice:
        await interaction.response.send_message("Non sei connesso a un canale vocale.", ephemeral=True)
        return

    channel = interaction.user.voice.channel
    voice_client = discord.utils.get(client.voice_clients, guild=interaction.guild)

    if voice_client is None:
        await channel.connect()
    
    await interaction.response.defer()

    async with interaction.channel.typing():
        try:
            data = await asyncio.to_thread(ytdl.extract_info, search, download=False)
        except Exception as e:
            logging.error(f"Errore durante l'estrazione delle informazioni: {e}")
            await interaction.followup.send("Si è verificato un errore durante la ricerca.")
            return

        if 'entries' in data:
            # Se è una playlist, aggiungi tutte le tracce alla coda
            for entry in data['entries']:
                player = await YTDLSource.from_url(entry['webpage_url'], loop=client.loop, stream=True)
                
                queue.append((player, entry['webpage_url']))
                print(f"Durata della canzone '{player.title}': {format_duration(player.duration)}")
        else:
            # Se è una singola traccia, aggiungila alla coda
            player = await YTDLSource.from_url(search, loop=client.loop, stream=True)

            queue.append(player)
            print(f"Durata della canzone '{player.title}': {format_duration(player.duration)}")

    if not interaction.guild.voice_client.is_playing():
        await play_next(interaction)
    else:
        # Se una canzone è già in riproduzione, informa l'utente che la sua richiesta è stata aggiunta alla coda
        canzone_aggiunta = queue[-1][0].title  # Prende il titolo dell'ultima canzone aggiunta alla coda
        embed = discord.Embed(
            title="AGGIUNTO ALLA CODA",
            description=f"<:Queue:1291836813043826838> ︱{interaction.user.mention} ha aggiunto ''{canzone_aggiunta}'' alla coda! Posizione: {len(queue)}",
            color=0xFF0000
        )
        await interaction.followup.send(embed=embed)

    if not inactivity_check.is_running():
        inactivity_check.start(interaction.guild.voice_client)

@tree.command(name='skip', description='Salta alla prossima canzone nella coda')
async def skip_command(interaction: discord.Interaction):
    await skip(interaction)

@tree.command(name='pause', description='Mette in pausa la canzone attualmente in riproduzione')
async def pause_command(interaction: discord.Interaction):
    await pause(interaction)

@tree.command(name='resume', description='Riprende la canzone dalla pausa')
async def resume_command(interaction: discord.Interaction):
    await resume(interaction)

@tree.command(name='stop', description='Ferma il bot e cancella la coda')
async def stop_command(interaction: discord.Interaction):
    await quit(interaction)

@tasks.loop(minutes=10)
async def inactivity_check(voice_client):
    if not voice_client.is_playing():
        await voice_client.disconnect()
        inactivity_check.stop()
        await change_status()



client.run(TOKEN)