# macOS Native OpenAI-Compatible API (TTS & STT)

## ⚠️ Disclaimer

**Questo progetto è stato realizzato con il supporto di agenti AI ed è fornito "così com'è" senza alcuna garanzia.**

L'utilizzo di questo software è a vostra esclusiva responsabilità. Gli autori e i contributori non si assumono alcuna responsabilità per:
- Danni diretti o indiretti causati dall'utilizzo del software
- Perdita di dati o malfunzionamenti del sistema
- Problemi di sicurezza o violazioni della privacy
- Qualsiasi altro danno derivante dall'uso di questo progetto

Prima di utilizzare questo software, si consiglia di testarlo in un ambiente controllato e di verificare che funzioni correttamente nel vostro contesto specifico.

Questo progetto espone un servizio API compatibile con OpenAI per le funzioni di **Text-to-Speech (TTS)** e **Speech-to-Text (STT)**, sfruttando esclusivamente le risorse native di macOS (comando `say` e framework `Speech`).

## Caratteristiche

- **TTS Compatibile OpenAI**: Endpoint `/v1/audio/speech` che utilizza la sintesi vocale di sistema.
- **Mapping Voci OpenAI-to-macOS**: Supporta i parametri `voice` (nomi OpenAI: alloy, echo, nova, ecc.) e `language` per selezionare voci di sistema native (Siri, Alice, Samantha, ecc.) con mapping configurabile in `config.py`.
- **STT Compatibile OpenAI**: Endpoint `/v1/audio/transcriptions` che utilizza il framework `Speech` di Apple tramite il tool `macos-transcribe`.
- **Due Motori STT**:
  - **Motore Legacy** (`SFSpeechRecognizer`): Disponibile su macOS 14+ con chunking automatico da 15s per file lunghi
  - **Motore Analyzer** (`SpeechAnalyzer`): Disponibile su macOS 26 Tahoe+ con qualità migliorata e supporto nativo per audio long-form (nessun chunking forzato)
- **Chunking Automatico Audio Lunghi**: File audio > 15 secondi vengono automaticamente suddivisi in chunk da 15s, trascritti singolarmente e ricomposti. Il server ritorna un `job_id` (status 202) e un endpoint di polling (`GET /v1/audio/transcriptions/<job_id>`) permette di monitorare l'avanzamento chunk per chunk.
- **Configurazione tramite `.env`**: Server Flask con porta, host, modalità debug, protocollo HTTPS/HTTP, percorsi di `ffmpeg` e `macos-transcribe` configurabili tramite variabili d'ambiente.
- **Web Tester**: Interfaccia web moderna con progress bar per monitorare la trascrizione di file audio lunghi.
- **Zero Cloud**: Tutto il processamento avviene localmente sul tuo Mac.

## Requisiti

- macOS (testato su macOS 14+ Sonoma)
- Python 3.8+
- `ffmpeg` installato (es. via Homebrew: `brew install ffmpeg`)
- Xcode Command Line Tools (`xcode-select --install`)
- Tool `macos-transcribe`: va compilato (vedi sezione dedicata sotto)
- **Per il motore SpeechAnalyzer**: macOS 26 Tahoe o successivo

## Selezione Motore STT

Il server può scegliere automaticamente il miglior motore STT disponibile in base alla versione di macOS, oppure puoi configurarlo esplicitamente:

| Motore | Versione macOS | Vantaggi | Chunking |
|--------|---|----------|----------|
| **legacy** (SFSpeechRecognizer) | 14+ | Compatibile, stabile, collaudato | Auto 15s |
| **analyzer** (SpeechAnalyzer) | 26+ | Qualità migliore, supporto audio long-form nativo | Opzionale |

Configurazione tramite `.env`:
```bash
# Selezione automatica in base alla versione di macOS (consigliato)
STT_ENGINE=auto

# Forza il motore legacy (SFSpeechRecognizer)
STT_ENGINE=legacy

# Forza il motore analyzer (SpeechAnalyzer, richiede macOS 26+)
STT_ENGINE=analyzer
```

Default: `STT_ENGINE=auto` (seleziona automaticamente il miglior motore disponibile)

## Autorizzazione Speech Recognition su macOS

Entrambi i motori STT (legacy e analyzer) dipendono dal framework Speech Recognition di Apple, che richiede autorizzazione esplicita dell'utente per ogni lingua utilizzata.

### Configurazione Iniziale
1. **Primo lancio di trascrizione** potrebbe richiederti di autorizzare la speech recognition:
  - Consenti la richiesta cliccando "OK" nella finestra di dialogo di sistema
  - Se non vedi una richiesta, continua al passo successivo

2. **Autorizzazione Manuale** (se necessario):
  - Apri **Preferenze di Sistema** → **Privacy e Sicurezza** → **Speech Recognition**
  - Individua il tuo ambiente Python o l'app terminale nella lista
  - Assicurati che l'interruttore sia abilitato (verde) per consentirle di usare Speech Recognition

3. **Risolvere i Problemi di Autorizzazione**:
  - Se vedi "Speech recognizer not available for [language]":
    - Vai su **Impostazioni di Sistema** → **Generale** → **Lingua e Area**
    - Aggiungi la lingua desiderata (es. Italiano) alle tue lingue preferite
    - Riavvia l'applicazione
  - Se l'autorizzazione continua a fallire dopo l'abilitazione in Privacy e Sicurezza:
    - Riavvia il Mac
    - Elimina la cache di Speech Recognition: `rm -rf ~/Library/SpeechRecognition`
    - Riprova la trascrizione

### Lingue Supportate
Il supporto linguistico di Speech Recognition dipende dalle impostazioni di lingua del tuo sistema. Le lingue comunemente supportate includono:
- Inglese (en-US, en-GB)
- Spagnolo (es-ES)
- Francese (fr-FR)
- Italiano (it-IT)
- Tedesco (de-DE)

### Comportamento Predefinito
- Se l'autorizzazione viene negata o la lingua non è disponibile: Il sistema restituisce un messaggio di errore descrittivo
- Entrambi i motori hanno fallback automatico: Se il motore selezionato fallisce, il sistema tenta l'engine alternativo

## Struttura del Progetto

- `app.py`: Server Flask principale.
- `config.py`: Configurazioni di sistema, percorsi e mapping. I percorsi leggibili da `.env` hanno fallback hardcoded.
- `macos-transcribe/`: Progetto Swift per la trascrizione nativa.
- `web-app/`: Applicazione Node.js di test (Proxy Express + UI).

## Installazione e Avvio

### 1. Preparazione ambiente Python
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurazione (opzionale)
Crea un file `.env` nella root del progetto per controllare i parametri del server e i percorsi dei binari:

```bash
# Porta del server (default: 5050)
PORT=5050

# Host del server (default: 0.0.0.0)
HOST=0.0.0.0

# Modalità debug (default: True)
DEBUG=True

# USE_HTTP=True usa HTTP (consigliato per HA), False usa HTTPS
USE_HTTP=True

# Motore STT: auto, legacy, analyzer (default: auto)
STT_ENGINE=auto

# Percorso del binario ffmpeg (default: /opt/homebrew/bin/ffmpeg)
FFMPEG_BIN=/opt/homebrew/bin/ffmpeg

# Percorso del binario macos-transcribe (default: percorso build Swift)
# MACOS_TRANSCRIBE_BIN=./macos-transcribe/.build/arm64-apple-macosx/release/macos-transcribe

# Percorso del binario macos-transcribe-analyzer (default: percorso build Swift)
# MACOS_TRANSCRIBE_ANALYZER_BIN=./macos-transcribe-analyzer/.build/arm64-apple-macosx/release/macos-transcribe-analyzer
```

### 3. Avvio del Server API
```bash
python app.py
```

- Con `USE_HTTP=True`: server su `http://localhost:<PORT>` (default: 5050)
- Con `USE_HTTP=False` o omesso: server su `https://localhost:<PORT>` con certificato self-signed (generato automaticamente in `certs/`)

### 4. Compilazione Strumenti STT

#### Strumento Legacy (macos-transcribe)
Il tool di trascrizione nativo va compilato con Swift. Disponibile su macOS 14+:
```bash
cd macos-transcribe
swift build -c release
cd ..
```
Il binario verrà generato in `macos-transcribe/.build/arm64-apple-macosx/release/macos-transcribe`, che è il percorso di default. Per sovrascriverlo, imposta `MACOS_TRANSCRIBE_BIN` in `.env`.

#### Strumento Analyzer (macos-transcribe-analyzer)
**Opzionale** — Necessario solo se desideri utilizzare il motore SpeechAnalyzer su macOS 26 Tahoe o successivo:
```bash
cd macos-transcribe-analyzer
swift build -c release
cd ..
```
Il binario verrà generato in `macos-transcribe-analyzer/.build/arm64-apple-macosx/release/macos-transcribe-analyzer`. Per utilizzarlo, imposta `STT_ENGINE=analyzer` in `.env`.

### 5. Avvio del Web Tester
```bash
cd web-app
npm install
npm start
```
Il tester sarà disponibile su `http://localhost:3000` e rispetta la configurazione `USE_HTTP` del `.env` (default: HTTPS se il file `.env` non esiste o `USE_HTTP` non è impostato). Consulta `.env.sample` per tutte le variabili disponibili.

### 6. Abilita Speech Recognition (Importante!)

**Prima di poter trascrivere l'audio**, devi autorizzare Speech Recognition sul tuo Mac:

**Script Setup Veloce** (consigliato):
```bash
./setup-speech-recognition.sh
```
Questo script fornisce:
- Istruzioni di autorizzazione chiare
- Navigazione interattiva di System Settings
- Link alle guide di risoluzione dei problemi

**Test dei Motori STT** (dopo il setup):
```bash
./test-stt-engines.sh
```
Questo script testa:
- Disponibilità dei binari
- Supporto linguistico nel tuo sistema
- Diagnosi dei problemi di Speech Recognition

**Setup Manuale** (se gli script non funzionano):
1. Apri **Impostazioni di Sistema** → **Privacy e Sicurezza**
2. Trova **Speech Recognition** nella lista
3. Individua Terminal o Python nelle app autorizzate
4. Attiva l'interruttore (diventa verde)
5. Vai a **Impostazioni di Sistema** → **Generale** → **Lingua e Area**
6. Aggiungi le tue lingue desiderate alla lista
7. Riavvia Terminal/IDE e riprova la trascrizione

## ⚠️ Note Importanti sull'Autorizzazione Speech Recognition

### Perché l'Autorizzazione è Necessaria

Entrambi i motori STT (legacy e analyzer) dipendono dal framework Speech Recognition di Apple (`Speech.framework`), una risorsa di sistema che richiede l'autorizzazione esplicita dell'utente. È simile a come le app devono richiedere accesso a Fotocamera, Microfono o Contatti.

### Cosa Accade Senza Autorizzazione

Se provi a trascrivere audio senza autorizzare Speech Recognition:

1. **Senza Speech Recognition aggiunto alle app autorizzate:**
  - Errore: `Speech recognizer not available for [language]`
  - **Soluzione**: Vai in **Impostazioni di Sistema** → **Privacy e Sicurezza** → **Speech Recognition** e attiva l'interruttore per il tuo ambiente Python/Terminal

2. **Senza la lingua installata:**
  - Errore: `Speech recognizer not available for [language]`
  - **Soluzione**: Aggiungi la lingua in **Impostazioni di Sistema** → **Generale** → **Lingua e Area**

3. **Il motore analyzer fallisce (exit code -6):**
  - Il sistema automaticamente effettua un fallback al motore legacy
  - Se anche il legacy fallisce, l'API restituisce un messaggio di errore
  - Non c'è nessun altro fallback disponibile

### Meccanismo di Fallback Automatico

Il server implementa un fallback intelligente per massimizzare l'affidabilità:

```
Richiesta Utente
  ↓
Prova Motore Analyzer (se macOS 26+)
  ↓ (se fallisce con autorizzazione o errore non disponibile)
Prova Motore Legacy (macOS 14+)
  ↓ (se anche questo fallisce)
Restituisci Messaggio di Errore
```

### Test dello Stato di Autorizzazione

Usa lo script di test fornito per verificare se Speech Recognition è correttamente autorizzato:

```bash
./test-stt-engines.sh
```

Output previsto per un sistema correttamente autorizzato:
```
Testing en-US... ✓ Available
Testing it-IT... ✓ Available
... (lingue in base alle tue impostazioni di sistema)
```

### Lista di Controllo per la Risoluzione dei Problemi

- [ ] Apri **Impostazioni di Sistema** → **Privacy e Sicurezza** → **Speech Recognition**
- [ ] È Terminal/Python nella lista autorizzata?
- [ ] L'interruttore per Terminal/Python è ACCESO (verde)?
- [ ] Hai almeno una lingua installata in **Impostazioni di Sistema** → **Generale** → **Lingua e Area**?
- [ ] Hai riavviato Terminal/IDE dopo aver cambiato le impostazioni?
- [ ] Prova a cancellare la cache: `rm -rf ~/Library/SpeechRecognition` e riavvia

## Utilizzo API

### Text-to-Speech (TTS)
**Endpoint**: `POST /v1/audio/speech`

Parametri supportati:
- `input` (stringa, obbligatorio) — testo da sintetizzare
- `voice` (stringa, default `"alloy"`) — voce OpenAI mappata su voci macOS (alloy, echo, nova, onyx, shimmer, fable)
- `language` (stringa, opzionale) — sovrascrive la voce in base alla lingua (es. `"it"`, `"en"`, `"fr"`)
- `speed` (float, default `1.0`) — velocità di lettura
- `response_format` (stringa, default `"mp3"`) — formato audio: mp3, opus, aac, flac, wav, pcm

```bash
# Base - solo input:
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Ciao, sono il tuo Mac che parla!"}' \
  --output audio.mp3

# Con voce e lingua specifici:
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, I am your Mac speaking!","voice": "nova","language": "en","speed": 1.2}' \
  --output audio.mp3

# Con HTTPS (aggiungi -k per certificato self-signed):
curl -k -X POST https://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Ciao, sono il tuo Mac che parla!","speed": 1.0}' \
  --output audio.mp3
```

### Speech-to-Text (STT)
**Endpoint**: `POST /v1/audio/transcriptions`

Parametri supportati:
- `file` (file, obbligatorio) — file audio da trascrivere
- `model` (stringa, default `"whisper-1"`) — compatibile OpenAI (valore a scopo identificativo)
- `language` (stringa, default `"en-US"`) — lingua del parlato (es. `"it-IT"`, `"fr-FR"`, `"de-DE"`)
- `response_format` (stringa, default `"json"`) — formato risposta: json, verbose_json, text

```bash
# Base - file e lingua esplicita:
curl -X POST http://localhost:5050/v1/audio/transcriptions \
  -F "file=@audio.mp3" \
  -F "model=whisper-1" \
  -F "language=it-IT"

# Con HTTPS (aggiungi -k per certificato self-signed):
curl -k -X POST https://localhost:5050/v1/audio/transcriptions \
  -F "file=@audio.mp3" \
  -F "model=whisper-1" \
  -F "language=en-US"
```

#### File Audio Lunghi (Chunking Automatico)

Per file audio di durata superiore a ~15 secondi, il server attiva automaticamente la modalità asincrona:

```bash
# Invia un file lungo → ricevi un job_id
curl -X POST http://localhost:5050/v1/audio/transcriptions \
  -F "file=@intervista_lunga.mp3" \
  -F "language=it-IT"
```
Risposta (status 202):
```json
{"job_id": "uuid-della-transcrizione"}
```

```bash
# Polling dello stato (progresso chunk per chunk)
curl http://localhost:5050/v1/audio/transcriptions/<job_id>
```
Risposta durante l'elaborazione:
```json
{
  "job_id": "uuid...",
  "status": "processing",
  "progress": 0.6,
  "current_chunk": 3,
  "total_chunks": 5,
  "result": null,
  "error": null
}
```

Risposta a completamento:
```json
{
  "job_id": "uuid...",
  "status": "completed",
  "progress": 1.0,
  "current_chunk": 5,
  "total_chunks": 5,
  "result": {"text": "trascrizione completa..."},
  "error": null
}
```

Il meccanismo:
1. Il server converte l'audio in WAV 16kHz mono
2. `ffmpeg` estrae chunk di 15 secondi con indici progressivi
3. Ogni chunk viene trascritto individualmente da `macos-transcribe`
4. I testi vengono concatenati preservando l'ordine
5. Il job scade automaticamente dopo 5 minuti dal completamento

### Voci Disponibili
**Endpoint**: `GET /v1/voices`
```bash
curl http://localhost:5050/v1/voices
```
Restituisce la lista delle voci OpenAI supportate, il mapping verso le voci macOS e il mapping personalizzato per lingua.

## Note Tecniche
- Il comando `say` viene eseguito senza il parametro `-v`, delegando la scelta della voce al mapping in `config.py` (parametro `voice` dell'API) che utilizza le voci Siri/native di sistema per una qualità superiore.
- L'audio viene normalizzato a 16kHz mono WAV prima di essere processato dal framework `Speech` per massimizzare l'accuratezza.
- **Motori STT**:
  - **Legacy (SFSpeechRecognizer)**: Chunking automatico da 15s. Limite empirico di ~16 secondi per chunk; 15 secondi garantiscono margine di sicurezza.
  - **Analyzer (SpeechAnalyzer)**: Supporto nativo per audio long-form. Processa interi file audio senza chunking forzato su macOS 26+.
- **Chunking STT**: La soglia di chunking è impostata a 15 secondi (`CHUNK_DURATION` in `app.py`) per il motore legacy. La durata viene rilevata tramite `ffprobe`. Se `ffprobe` non è disponibile, il file viene processato direttamente senza chunking.
- **Polling**: I job asincroni vengono rimossi automaticamente dopo 5 minuti. Lo stato `error` viene impostato in caso di fallimento in uno qualsiasi dei chunk.
- **Rilevamento Motore**: Il server rileva automaticamente la versione di macOS e seleziona il motore appropriato. Usa `GET /v1/voices` per controllare quale motore è attualmente attivo.

## Licenza

Questo progetto è distribuito sotto la licenza MIT. Vedi il file [LICENSE](LICENSE) per i dettagli completi.

```
MIT License

Copyright (c) 2026

Per concessione gratuita a chiunque ottenente una copia
di questo software e dei file di documentazione associati (il "Software"),
è consentito di usare, copiare, modificare, unire, pubblicare, distribuire,
sub-licenziare, e/o vendere copie del Software, a condizione che:

La suddetta nota di copyright e questa nota di permesso devono essere incluse
in tutte le copie o parti sostanziali del Software.

IL SOFTWARE È FORNITO "COM'È", SENZA GARANZIE DI ALCUN TIPO,
ESPLICITE O IMPLICITE, INCLUSE MA NON LIMITATE ALLE GARANZIE
DI COMMERCIABILITÀ, IDONEITÀ PER UNO SCOPO PARTICOLARE E NON VIOLAZIONE.

IN NESSUN CASO GLI AUTORI O I DETENTORI DEL COPYRIGHT POTRANNO ESSERE
RITENUTI RESPONSABILI PER RECLAMI, DANNI O ALTRA RESPONSABILITÀ,
SIA IN UN'AZIONE DI CONTRATTO, TORTO O ALTRIMENTI, DERIVANTE DA,
O IN CONNESSIONE CON IL SOFTWARE O L'USO O ALTRE TRANSAZIONI NEL SOFTWARE.
```
