import os
import subprocess
import uuid
import ssl
from flask import Flask, request, jsonify, send_file, Response
import config

app = Flask(__name__)

def generate_self_signed_cert():
    if not os.path.exists(config.CERT_FILE) or not os.path.exists(config.KEY_FILE):
        print("Generating self-signed certificate...")
        try:
            subprocess.run([
                'openssl', 'req', '-x509', '-newkey', 'rsa:2048', 
                '-keyout', config.KEY_FILE, '-out', config.CERT_FILE, 
                '-days', '365', '-nodes', '-subj', '/CN=localhost'
            ], check=True)
            print("Certificate generated successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error generating certificate: {e}")

@app.route('/v1/audio/speech', methods=['POST'])
def text_to_speech():
    data = request.json
    if not data or 'input' not in data:
        return jsonify({"error": "Missing 'input' parameter"}), 400

    text = data.get('input')
    voice_name = data.get('voice', 'alloy').lower()
    response_format = data.get('response_format', 'mp3').lower()
    speed = data.get('speed', 1.0)
    language = data.get('language') # Custom param

    # Map voice
    macos_voice = config.VOICE_MAPPING.get(voice_name, config.VOICE_MAPPING['default'])
    
    # Override if language is provided and we have a mapping
    if language and language in config.LANG_VOICE_MAPPING:
        macos_voice = config.LANG_VOICE_MAPPING[language]

    job_id = str(uuid.uuid4())
    temp_aiff = os.path.join(config.TEMP_DIR, f"{job_id}.aiff")
    output_file = os.path.join(config.TEMP_DIR, f"{job_id}.{response_format}")

    try:
        # 1. Run 'say' to generate AIFF
        # Removed -v to use system default (Siri) as requested
        say_cmd = ['say', '-o', temp_aiff]
        
        # Handle speed (OpenAI 1.0 is default, macOS 'say' uses wpm, default around 180-200)
        # Simple linear mapping: 1.0 -> 200 wpm
        wpm = int(200 * speed)
        say_cmd.extend(['-r', str(wpm)])
        
        say_cmd.append(text)
        
        subprocess.run(say_cmd, check=True)

        # 2. Convert to target format using ffmpeg
        # ffmpeg -i input.aiff output.mp3
        ffmpeg_cmd = [config.FFMPEG_BIN, '-i', temp_aiff, '-y', output_file]
        
        # Handle specific formats if needed (e.g. opus/aac)
        if response_format == 'opus':
            ffmpeg_cmd.extend(['-c:a', 'libopus'])
        elif response_format == 'aac':
            ffmpeg_cmd.extend(['-c:a', 'aac'])
        
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

        # 3. Send file
        mime_types = {
            'mp3': 'audio/mpeg',
            'opus': 'audio/opus',
            'aac': 'audio/aac',
            'flac': 'audio/flac',
            'wav': 'audio/wav',
            'pcm': 'audio/l16'
        }
        
        return send_file(
            output_file, 
            mimetype=mime_types.get(response_format, 'application/octet-stream'),
            as_attachment=False
        )

    except Exception as e:
        print(f"[TTS Error] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        pass

@app.route('/v1/audio/transcriptions', methods=['POST'])
def speech_to_text():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    model = request.form.get('model', 'whisper-1')
    language = request.form.get('language', 'en-US')
    response_format = request.form.get('response_format', 'json').lower()

    job_id = str(uuid.uuid4())
    input_path = os.path.join(config.TEMP_DIR, f"{job_id}.tmp")
    wav_path = os.path.join(config.TEMP_DIR, f"{job_id}.wav")
    
    try:
        file.save(input_path)

        # Convert to WAV (macos-transcribe works best with standard wav)
        subprocess.run([
            config.FFMPEG_BIN, '-i', input_path, 
            '-ar', '16000', '-ac', '1', '-y', wav_path
        ], check=True, capture_output=True)

        # Run macos-transcribe
        transcribe_cmd = [config.MACOS_TRANSCRIBE_BIN, wav_path, '--locale', language]
        if response_format in ['json', 'verbose_json']:
            transcribe_cmd.append('--json')
        
        result = subprocess.run(transcribe_cmd, capture_output=True, text=True, check=True)
        output_text = result.stdout.strip()

        # If macos-transcribe returned JSON, we need to process it
        is_json_output = False
        parsed_json = None
        try:
            import json
            parsed_json = json.loads(output_text)
            is_json_output = True
        except:
            pass

        if response_format == 'json':
            if is_json_output and isinstance(parsed_json, list):
                full_text = " ".join([s.get('text', '') for s in parsed_json])
                return jsonify({"text": full_text.strip()})
            return jsonify({"text": output_text})
        elif response_format == 'verbose_json':
            if is_json_output and isinstance(parsed_json, list):
                full_text = " ".join([s.get('text', '') for s in parsed_json])
                return jsonify({
                    "task": "transcribe",
                    "language": language,
                    "duration": parsed_json[-1].get('start', 0) + parsed_json[-1].get('duration', 0) if parsed_json else 0,
                    "text": full_text.strip(),
                    "segments": parsed_json
                })
            return jsonify({"text": output_text, "segments": []})
        else:
            if is_json_output and isinstance(parsed_json, list):
                full_text = " ".join([s.get('text', '') for s in parsed_json])
                return Response(full_text.strip(), mimetype='text/plain')
            return Response(output_text, mimetype='text/plain')

    except Exception as e:
        print(f"[STT Error] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/v1/voices', methods=['GET'])
def list_voices():
    return jsonify({
        "openai_voices": list(config.VOICE_MAPPING.keys()),
        "mapping": config.VOICE_MAPPING,
        "custom_lang_mapping": config.LANG_VOICE_MAPPING
    })

if __name__ == '__main__':
# Check if we should use HTTP (insecure) or HTTPS (secure) based on env/config
    use_http = getattr(config, 'USE_HTTP', False)
    # Gestione stringa booleana (se arriva da .env come stringa "true")
    if isinstance(use_http, str):
        use_http = use_http.lower() == 'true'
    
    if not use_http:
        generate_self_signed_cert()
        ssl_context = (config.CERT_FILE, config.KEY_FILE)
        print(f"Starting server with HTTPS on port {config.PORT}")
    else:
        ssl_context = None
        print(f"Starting server with HTTP on port {config.PORT} (Insecure)")

    app.run(
        host=config.HOST, 
        port=config.PORT, 
        debug=config.DEBUG,
        ssl_context=ssl_context
    )
