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
- **HTTP/HTTPS configurabile**: Server Flask sulla porta 5050 con supporto HTTPS (certificati self-signed) o HTTP semplice, tramite variabile `USE_HTTP` in `.env`.
- **Web Tester**: Interfaccia web moderna per testare rapidamente sia la sintesi che la trascrizione.
- **Zero Cloud**: Tutto il processamento avviene localmente sul tuo Mac.

## Requisiti

- macOS (testato su macOS 14+ Sonoma)
- Python 3.8+
- `ffmpeg` installato (es. via Homebrew: `brew install ffmpeg`)
- Xcode Command Line Tools (`xcode-select --install`)
- Tool `macos-transcribe`: va compilato (vedi sezione dedicata sotto)

## Struttura del Progetto

- `app.py`: Server Flask principale.
- `config.py`: Configurazioni di sistema, percorsi e mapping.
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
Crea un file `.env` nella root del progetto per controllare il protocollo:

```bash
# .env — USE_HTTP=True usa HTTP (consigliato per HA), False usa HTTPS
USE_HTTP=True
```

### 3. Avvio del Server API
```bash
python app.py
```

- Con `USE_HTTP=True`: server su `http://localhost:5050`
- Con `USE_HTTP=False` o omesso: server su `https://localhost:5050` con certificato self-signed (generato automaticamente in `certs/`)

### 4. Compilazione di macos-transcribe

Il tool di trascrizione nativo va compilato con Swift:
```bash
cd macos-transcribe
swift build -c release
cd ..
```
Il binario verrà generato in `macos-transcribe/.build/arm64-apple-macosx/release/macos-transcribe`, percorso già configurato in `config.py`.

### 5. Avvio del Web Tester
```bash
cd web-app
npm install
npm start
```
Il tester sarà disponibile su `http://localhost:3000` e rispetta la configurazione `USE_HTTP` del `.env` (default: HTTPS se il file `.env` non esiste o `USE_HTTP` non è impostato).

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

### Voci Disponibili
**Endpoint**: `GET /v1/voices`
```bash
curl http://localhost:5050/v1/voices
```
Restituisce la lista delle voci OpenAI supportate, il mapping verso le voci macOS e il mapping personalizzato per lingua.

## Note Tecniche
- Il comando `say` viene eseguito senza il parametro `-v`, delegando la scelta della voce al mapping in `config.py` (parametro `voice` dell'API) che utilizza le voci Siri/native di sistema per una qualità superiore.
- L'audio viene normalizzato a 16kHz mono WAV prima di essere processato dal framework `Speech` per massimizzare l'accuratezza.

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
