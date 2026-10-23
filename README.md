# LiveBotDiscord

## Emoji nella ruota

Le emoji Unicode nei nickname sono disegnate a colori nella GIF e nel PNG finale,
incluse bandiere, tonalità della pelle e sequenze composte. I nomi lunghi vengono
accorciati senza spezzare le emoji. Installare le dipendenze di `requirements.txt`.
Le immagini vengono scaricate da jsDelivr e mantenute in una cache in memoria;
se non sono disponibili viene mostrato `?`, senza interrompere la ruota.

Grafica emoji [Twemoji](https://github.com/jdecked/twemoji), copyright Twitter, Inc.
e contributori, licenza [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Le immagini sono ridimensionate e ruotate per essere inserite negli spicchi.

## Medal

`/livemedal link_clip:<link di una clip pubblica o medal.tv/users/ID o ID numerico>`
attiva la pubblicazione delle **nuove** clip. Le clip già presenti non vengono ripubblicate;
il controllo avviene ogni 3 ore. `/livemedalstop` disattiva la pubblicazione.

Non serve più una chiave API né un account personale: il bot usa una sessione ospite
di Medal per leggere esclusivamente le clip pubblicate e pubbliche del profilo.
La sessione viene riutilizzata in memoria e rinnovata una sola volta in caso di `401`.
`MEDAL_API_KEY` e le vecchie chiavi nelle sottoscrizioni non vengono più utilizzate.
Le sottoscrizioni esistenti restano compatibili e non occorre rifare `/livemedal`.

La vecchia API `developers.medal.tv/v1/latest` rifiutava anche chiavi appena generate;
la lettura tramite sessione ospite è stata verificata con richieste reali.
Questo endpoint web non è un'API pubblica documentata e potrebbe cambiare in futuro.
Il comando distingue errori di accesso, limite richieste, timeout e risposte non valide,
senza salvare una sottoscrizione non verificata. Riavviare il bot per sincronizzare
la nuova versione del comando (senza il parametro `api_key`).

Test locali (con `aiohttp` e `discord.py` installati): `python -m unittest discover -s tests -v`.
