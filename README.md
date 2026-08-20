# macOS Native OpenAI-Compatible API (TTS & STT)

## ⚠️ Disclaimer

**This project was developed with the support of AI agents and is provided "as is" without any warranty.**

The use of this software is entirely at your own risk. The authors and contributors assume no responsibility for:
- Direct or indirect damages caused by the use of the software
- Data loss or system malfunctions
- Security issues or privacy violations
- Any other damage resulting from the use of this project

Before using this software, it is recommended to test it in a controlled environment and verify that it works correctly in your specific context.

This project exposes an OpenAI-compatible API service for **Text-to-Speech (TTS)** and **Speech-to-Text (STT)** functions, leveraging exclusively native macOS resources (the `say` command and the `Speech` framework).

## Features

- **OpenAI-Compatible TTS**: Endpoint `/v1/audio/speech` that uses system speech synthesis.
- **OpenAI-to-macOS Voice Mapping**: Supports the `voice` parameters (OpenAI names: alloy, echo, nova, etc.) and `language` to select native system voices (Siri, Alice, Samantha, etc.) with configurable mapping in `config.py`.
- **OpenAI-Compatible STT**: Endpoint `/v1/audio/transcriptions` that uses Apple's `Speech` framework through the `macos-transcribe` tool.
- **Dual STT Engines**:
  - **Legacy Engine** (`SFSpeechRecognizer`): Available on macOS 14+ with automatic 15s chunking for long files
  - **Analyzer Engine** (`SpeechAnalyzer`): Available on macOS 26 Tahoe+ with improved quality and native long-form audio support (no forced chunking)
- **Automatic Long Audio Chunking**: Audio files > 15 seconds are automatically split into 15s chunks, transcribed individually, and reassembled. The server returns a `job_id` (status 202) and a polling endpoint (`GET /v1/audio/transcriptions/<job_id>`) tracks per-chunk progress.
- **Configurable via `.env`**: Flask server with port, host, debug mode, HTTPS/HTTP protocol, and configurable `ffmpeg` and `macos-transcribe` binary paths via environment variables.
- **Web Tester**: Modern web interface with progress bar to monitor long audio transcription.
- **Zero Cloud**: All processing happens locally on your Mac.

## Requirements

- macOS (tested on macOS 14+ Sonoma)
- Python 3.8+
- `ffmpeg` installed (e.g., via Homebrew: `brew install ffmpeg`)
- Xcode Command Line Tools (`xcode-select --install`)
- `macos-transcribe` tool: must be compiled (see dedicated section below)
- **For SpeechAnalyzer engine**: macOS 26 Tahoe or later

## STT Engine Selection

The server can automatically choose the best available STT engine based on your macOS version, or you can explicitly configure it:

| Engine | macOS Version | Strengths | Chunking |
|--------|---------------|-----------|----------|
| **legacy** (SFSpeechRecognizer) | 14+ | Compatible, stable, established | Auto 15s chunking |
| **analyzer** (SpeechAnalyzer) | 26+ | Better quality, long-form native support | Optional |

Configuration via `.env`:
```bash
# Automatic selection based on macOS version (recommended)
STT_ENGINE=auto

# Force legacy engine (SFSpeechRecognizer)
STT_ENGINE=legacy

# Force analyzer engine (SpeechAnalyzer, requires macOS 26+)
STT_ENGINE=analyzer
```

Default: `STT_ENGINE=auto` (automatically selects the best available engine)

## Project Structure

- `app.py`: Main Flask server.
- `config.py`: System configurations, paths, and mapping. Configurable paths are read from `.env` with hardcoded fallbacks.
- `macos-transcribe/`: Swift project for native transcription.
- `web-app/`: Node.js test application (Express Proxy + UI).

## macOS Speech Recognition Authorization

Both STT engines (legacy and analyzer) depend on Apple's Speech Recognition framework, which requires explicit user authorization for each language used.

### Initial Setup
1. **First run of transcription** may prompt you to allow speech recognition:
  - Allow the prompt by clicking "OK" in the system dialog
  - If you don't see a prompt, continue to the next step

2. **Manual Authorization** (if needed):
  - Open **System Preferences** → **Privacy & Security** → **Speech Recognition**
  - Locate your Python environment or terminal app in the list
  - Ensure the toggle is enabled (green) for it to use Speech Recognition

3. **Troubleshooting Authorization Issues**:
  - If you see "Speech recognizer not available for [language]":
    - Go to **System Settings** → **General** → **Language & Region**
    - Add the desired language (e.g., Italian) to your preferred languages
    - Restart the application
  - If authorization still fails after enabling in Privacy & Security:
    - Restart your Mac
    - Delete the Speech Recognition cache: `rm -rf ~/Library/SpeechRecognition`
    - Retry the transcription

### Supported Languages
Speech Recognition language support depends on your system language settings. Commonly supported languages include:
- English (en-US, en-GB)
- Spanish (es-ES)
- French (fr-FR)
- Italian (it-IT)
- German (de-DE)

### Default Behavior
- If authorization is denied or language unavailable: System returns a descriptive error message
- Both engines have automatic fallback: If the selected engine fails, the system attempts the alternative engine

## Installation and Startup

### 1. Python Environment Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration (optional)
Create a `.env` file in the project root to control server parameters and binary paths:

```bash
# Server port (default: 5050)
PORT=5050

# Server host (default: 0.0.0.0)
HOST=0.0.0.0

# Debug mode (default: True)
DEBUG=True

# USE_HTTP=True uses HTTP (recommended for HA), False uses HTTPS
USE_HTTP=True

# STT Engine: auto, legacy, analyzer (default: auto)
STT_ENGINE=auto

# Path to ffmpeg binary (default: /opt/homebrew/bin/ffmpeg)
FFMPEG_BIN=/opt/homebrew/bin/ffmpeg

# Path to macos-transcribe binary (default: Swift build path)
# MACOS_TRANSCRIBE_BIN=./macos-transcribe/.build/arm64-apple-macosx/release/macos-transcribe

# Path to macos-transcribe-analyzer binary (default: Swift build path)
# MACOS_TRANSCRIBE_ANALYZER_BIN=./macos-transcribe-analyzer/.build/arm64-apple-macosx/release/macos-transcribe-analyzer
```

### 3. Start the API Server
```bash
python app.py
```

- With `USE_HTTP=True`: server on `http://localhost:<PORT>` (default: 5050)
- With `USE_HTTP=False` or omitted: server on `https://localhost:<PORT>` with self-signed certificate (automatically generated in `certs/`)

### 4. Compile STT Tools

#### Legacy Tool (macos-transcribe)
The native transcription tool must be compiled with Swift. Available on macOS 14+:
```bash
cd macos-transcribe
swift build -c release
cd ..
```
The binary will be generated in `macos-transcribe/.build/arm64-apple-macosx/release/macos-transcribe`, which is the default path. To override it, set `MACOS_TRANSCRIBE_BIN` in `.env`.

#### Analyzer Tool (macos-transcribe-analyzer)
**Optional** — Only needed if you want to use the SpeechAnalyzer engine on macOS 26 Tahoe or later:
```bash
cd macos-transcribe-analyzer
swift build -c release
cd ..
```
The binary will be generated in `macos-transcribe-analyzer/.build/arm64-apple-macosx/release/macos-transcribe-analyzer`. To use it, set `STT_ENGINE=analyzer` in `.env`.

### 5. Start the Web Tester
```bash
cd web-app
npm install
npm start
```
The tester will be available on `http://localhost:3000` and respects the `USE_HTTP` configuration from `.env` (default: HTTPS if the `.env` file does not exist or `USE_HTTP` is not set). See `.env.sample` for all available variables.

### 6. Enable Speech Recognition (Important!)

**Before you can transcribe audio**, you must authorize Speech Recognition on your Mac:

**Quick Setup Script** (recommended):
```bash
./setup-speech-recognition.sh
```
This script provides:
- Clear authorization instructions
- Interactive System Settings navigation
- Links to troubleshooting guides

**Test STT Engines** (after setup):
```bash
./test-stt-engines.sh
```
This script tests:
- Binary availability
- Language support on your system
- Diagnosis of Speech Recognition issues

**Manual Setup** (if scripts don't work):
1. Open **System Settings** → **Privacy & Security**
2. Find **Speech Recognition** in the list
3. Locate Terminal or Python in the allowed apps
4. Toggle the switch ON (green)
5. Go to **System Settings** → **General** → **Language & Region**
6. Add your desired language(s) to the list
7. Restart Terminal/IDE and retry transcription
## ⚠️ Important Notes on Speech Recognition Authorization


### Why Authorization is Required

Both STT engines (legacy and analyzer) depend on Apple's Speech Recognition framework (`Speech.framework`), which is a system resource that requires explicit user authorization. This is similar to how apps must request access to Camera, Microphone, or Contacts.

### What Happens Without Authorization

If you try to transcribe audio without granting authorization:

1. **Without Speech Recognition added to allowed apps:**
  - Error: `Speech recognizer not available for [language]`
  - **Solution**: Go to **System Settings** → **Privacy & Security** → **Speech Recognition** and toggle your Python environment/Terminal to ON

2. **Without the language installed:**
  - Error: `Speech recognizer not available for [language]`
  - **Solution**: Add the language in **System Settings** → **General** → **Language & Region**

3. **Analyzer engine fails (exit code -6):**
  - System automatically falls back to legacy engine
  - If legacy also fails, the API returns the error message
  - No further fallback available

### Automatic Fallback Mechanism

The server implements intelligent fallback to maximize reliability:

```
User Request
  ↓
Try Analyzer Engine (if macOS 26+)
  ↓ (if fails with auth or unavailable error)
Try Legacy Engine (macOS 14+)
  ↓ (if also fails)
Return Error Message
```

### Testing Authorization Status

Use the provided test script to check if Speech Recognition is properly authorized:

```bash
./test-stt-engines.sh
```

Expected output for properly authorized system:
```
Testing en-US... ✓ Available
Testing it-IT... ✓ Available
... (languages based on your system settings)
```

### Troubleshooting Checklist

- [ ] Open **System Settings** → **Privacy & Security** → **Speech Recognition**
- [ ] Is Terminal/Python in the allowed list?
- [ ] Is the toggle for Terminal/Python ON (green)?
- [ ] Do you have at least one language installed in **System Settings** → **General** → **Language & Region**?
- [ ] Did you restart Terminal/IDE after changing settings?
- [ ] Try deleting cache: `rm -rf ~/Library/SpeechRecognition` and restart

## API Usage

### Text-to-Speech (TTS)
**Endpoint**: `POST /v1/audio/speech`

Supported parameters:
- `input` (string, required) — text to synthesize
- `voice` (string, default `"alloy"`) — OpenAI voice mapped to macOS voices (alloy, echo, nova, onyx, shimmer, fable)
- `language` (string, optional) — overrides the voice based on language (e.g., `"it"`, `"en"`, `"fr"`)
- `speed` (float, default `1.0`) — reading speed
- `response_format` (string, default `"mp3"`) — audio format: mp3, opus, aac, flac, wav, pcm

```bash
# Base - input only:
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, I am your Mac speaking!"}' \
  --output audio.mp3

# With specific voice and language:
curl -X POST http://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, I am your Mac speaking!","voice": "nova","language": "en","speed": 1.2}' \
  --output audio.mp3

# With HTTPS (add -k for self-signed certificate):
curl -k -X POST https://localhost:5050/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello, I am your Mac speaking!","speed": 1.0}' \
  --output audio.mp3
```

### Speech-to-Text (STT)
**Endpoint**: `POST /v1/audio/transcriptions`

Supported parameters:
- `file` (file, required) — audio file to transcribe
- `model` (string, default `"whisper-1"`) — OpenAI-compatible (identifier value only)
- `language` (string, default `"en-US"`) — spoken language (e.g., `"it-IT"`, `"fr-FR"`, `"de-DE"`)
- `response_format` (string, default `"json"`) — response format: json, verbose_json, text

```bash
# Base - file and explicit language:
curl -X POST http://localhost:5050/v1/audio/transcriptions \
  -F "file=@audio.mp3" \
  -F "model=whisper-1" \
  -F "language=it-IT"

# With HTTPS (add -k for self-signed certificate):
curl -k -X POST https://localhost:5050/v1/audio/transcriptions \
  -F "file=@audio.mp3" \
  -F "model=whisper-1" \
  -F "language=en-US"
```

#### Long Audio Files (Automatic Chunking)

For audio files longer than ~15 seconds, the server automatically switches to async mode:

```bash
# Send a long file → receive a job_id
curl -X POST http://localhost:5050/v1/audio/transcriptions \
  -F "file@=long_interview.mp3" \
  -F "language=en-US"
```
Response (status 202):
```json
{"job_id": "uuid-of-the-transcription"}
```

```bash
# Poll for status (per-chunk progress)
curl http://localhost:5050/v1/audio/transcriptions/<job_id>
```
Response while processing:
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

Response on completion:
```json
{
  "job_id": "uuid...",
  "status": "completed",
  "progress": 1.0,
  "current_chunk": 5,
  "total_chunks": 5,
  "result": {"text": "complete transcription..."},
  "error": null
}
```

How it works:
1. The server converts audio to 16kHz mono WAV
2. `ffmpeg` extracts 15-second chunks by progressive index
3. Each chunk is transcribed individually by `macos-transcribe`
4. Results are concatenated preserving order
5. Jobs expire automatically 5 minutes after completion

### Available Voices
**Endpoint**: `GET /v1/voices`
```bash
curl http://localhost:5050/v1/voices
```
Returns the list of supported OpenAI voices, the mapping to macOS voices, and the custom language mapping.

## Technical Notes
- The `say` command is executed without the `-v` parameter, delegating voice selection to the mapping in `config.py` (API `voice` parameter) which uses Siri/native system voices for superior quality.
- Audio is normalized to 16kHz mono WAV before being processed by the `Speech` framework to maximize accuracy.
- **STT Engines**:
  - **Legacy (SFSpeechRecognizer)**: Automatic 15s chunking. Empirical limit of ~16 seconds per chunk; 15 seconds provides a safety margin.
  - **Analyzer (SpeechAnalyzer)**: Native long-form audio support. Processes entire audio files without forced chunking on macOS 26+.
- **STT Chunking**: The chunking threshold is set to 15 seconds (`CHUNK_DURATION` in `app.py`) for the legacy engine. Duration is detected via `ffprobe`. If `ffprobe` is unavailable, the file is processed directly without chunking.
- **Polling**: Async jobs are automatically removed after 5 minutes. The `error` status is set if any chunk fails.
- **Engine Detection**: The server automatically detects the macOS version and selects the appropriate engine. Use `GET /v1/voices` to check which engine is currently active.

## License

This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for complete details.

```
MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
