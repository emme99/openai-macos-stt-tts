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
- **Configurable via `.env`**: Flask server with port, host, debug mode, HTTPS/HTTP protocol, and configurable `ffmpeg` and `macos-transcribe` binary paths via environment variables.
- **Web Tester**: Modern web interface to quickly test both synthesis and transcription.
- **Zero Cloud**: All processing happens locally on your Mac.

## Requirements

- macOS (tested on macOS 14+ Sonoma)
- Python 3.8+
- `ffmpeg` installed (e.g., via Homebrew: `brew install ffmpeg`)
- Xcode Command Line Tools (`xcode-select --install`)
- `macos-transcribe` tool: must be compiled (see dedicated section below)

## Project Structure

- `app.py`: Main Flask server.
- `config.py`: System configurations, paths, and mapping. Configurable paths are read from `.env` with hardcoded fallbacks.
- `macos-transcribe/`: Swift project for native transcription.
- `web-app/`: Node.js test application (Express Proxy + UI).

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

# Path to ffmpeg binary (default: /opt/homebrew/bin/ffmpeg)
FFMPEG_BIN=/opt/homebrew/bin/ffmpeg

# Path to macos-transcribe binary (default: Swift build path)
# MACOS_TRANSCRIBE_BIN=./macos-transcribe/.build/arm64-apple-macosx/release/macos-transcribe
```

### 3. Start the API Server
```bash
python app.py
```

- With `USE_HTTP=True`: server on `http://localhost:<PORT>` (default: 5050)
- With `USE_HTTP=False` or omitted: server on `https://localhost:<PORT>` with self-signed certificate (automatically generated in `certs/`)

### 4. Compile macos-transcribe

The native transcription tool must be compiled with Swift:
```bash
cd macos-transcribe
swift build -c release
cd ..
```
The binary will be generated in `macos-transcribe/.build/arm64-apple-macosx/release/macos-transcribe`, which is the default path. To override it, set `MACOS_TRANSCRIBE_BIN` in `.env`.

### 5. Start the Web Tester
```bash
cd web-app
npm install
npm start
```
The tester will be available on `http://localhost:3000` and respects the `USE_HTTP` configuration from `.env` (default: HTTPS if the `.env` file does not exist or `USE_HTTP` is not set). See `.env.sample` for all available variables.

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

### Available Voices
**Endpoint**: `GET /v1/voices`
```bash
curl http://localhost:5050/v1/voices
```
Returns the list of supported OpenAI voices, the mapping to macOS voices, and the custom language mapping.

## Technical Notes
- The `say` command is executed without the `-v` parameter, delegating voice selection to the mapping in `config.py` (API `voice` parameter) which uses Siri/native system voices for superior quality.
- Audio is normalized to 16kHz mono WAV before being processed by the `Speech` framework to maximize accuracy.

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
