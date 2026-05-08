# macOS Native OpenAI-Compatible API (TTS & STT)

Questo progetto espone un servizio API compatibile con OpenAI per le funzioni di **Text-to-Speech (TTS)** e **Speech-to-Text (STT)**, sfruttando esclusivamente le risorse native di macOS (comando `say` e framework `Speech`).

## Caratteristiche

- **TTS Compatibile OpenAI**: Endpoint `/v1/audio/speech` che utilizza la sintesi vocale di sistema.
- **Siri Voices Support**: Utilizza automaticamente la voce di sistema predefinita (es. Siri Voce 1), garantendo un'altissima qualità audio senza configurazioni complesse.
- **STT Compatibile OpenAI**: Endpoint `/v1/audio/transcriptions` che utilizza il framework `Speech` di Apple tramite il tool `macos-transcribe`.
- **HTTP/HTTPS configurabile**: Server Flask sulla porta 5050 con supporto HTTPS (certificati self-signed) o HTTP semplice, tramite variabile `USE_HTTP` in `.env`.
- **Web Tester**: Interfaccia web moderna per testare rapidamente sia la sintesi che la trascrizione.
- **Zero Cloud**: Tutto il processamento avviene localmente sul tuo Mac.

## Requisiti

- macOS (testato su macOS 14+ Sonoma)
- Python 3.14+
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
Il tester sarà disponibile su `http://localhost:3000` e rispetta automaticamente la stessa configurazione `USE_HTTP` del `.env`.

## Utilizzo API

### Text-to-Speech (TTS)
**Endpoint**: `POST /v1/audio/speech`
```bash
# Con HTTP:
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Ciao, sono il tuo Mac che parla!","speed": 1.0}' \
  --output audio.mp3

# Con HTTPS (aggiungi -k per certificato self-signed):
curl -k -X POST https://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Ciao, sono il tuo Mac che parla!","speed": 1.0}' \
  --output audio.mp3
```

### Speech-to-Text (STT)
**Endpoint**: `POST /v1/audio/transcriptions`
```bash
# Con HTTP:
curl -X POST http://localhost:5050/v1/audio/transcriptions \
  -F "file=@audio.mp3" \
  -F "model=whisper-1" \
  -F "language=it-IT"

# Con HTTPS (aggiungi -k per certificato self-signed):
curl -k -X POST https://localhost:5050/v1/audio/transcriptions \
  -F "file=@audio.mp3" \
  -F "model=whisper-1" \
  -F "language=it-IT"
```

## Note Tecniche
- Il comando `say` viene eseguito senza il parametro `-v` per permettere l'utilizzo delle voci Siri di sistema, che offrono una naturalezza superiore.
- L'audio viene normalizzato a 16kHz mono WAV prima di essere processato dal framework `Speech` per massimizzare l'accuratezza.
