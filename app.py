import os
import math
import subprocess
import uuid
import ssl
import threading
import time
import json
from flask import Flask, request, jsonify, send_file, Response
import config

app = Flask(__name__)

CHUNK_DURATION = 15

jobs = {}
jobs_lock = threading.Lock()

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

def get_ffprobe_path():
    ffmpeg = config.FFMPEG_BIN
    if ffmpeg.endswith('ffmpeg'):
        return ffmpeg[:-6] + 'ffprobe'
    return 'ffprobe'

def get_audio_duration(filepath):
    result = subprocess.run([
        get_ffprobe_path(), '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', filepath
    ], capture_output=True, text=True)
    return float(result.stdout.strip())

def run_transcription(wav_path, language):
    transcribe_cmd = [config.MACOS_TRANSCRIBE_BIN, wav_path, '--locale', language, '--json']
    result = subprocess.run(transcribe_cmd, capture_output=True, text=True, check=True)
    parsed = json.loads(result.stdout.strip())
    if isinstance(parsed, list):
        return " ".join(s.get('text', '') for s in parsed).strip()
    return result.stdout.strip()

def cleanup_temp(filepath):
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except:
        pass

def format_transcription_response(full_text, language, response_format, segments_data=None):
    if response_format == 'json':
        return jsonify({"text": full_text})
    elif response_format == 'verbose_json':
        return jsonify({
            "task": "transcribe",
            "language": language,
            "text": full_text,
            "segments": segments_data or []
        })
    else:
        return Response(full_text, mimetype='text/plain')

def process_long_audio(job_id):
    with jobs_lock:
        job = jobs[job_id].copy()
        wav_path = job['wav_path']
        language = job['language']
        total_chunks = job['total_chunks']

    try:
        all_texts = []
        for i in range(total_chunks):
            start = i * CHUNK_DURATION
            chunk_path = os.path.join(config.TEMP_DIR, f"{job_id}_chunk_{i:03d}.wav")

            subprocess.run([
                config.FFMPEG_BIN, '-ss', str(start), '-i', wav_path,
                '-t', str(CHUNK_DURATION),
                '-ar', '16000', '-ac', '1',
                '-y', chunk_path
            ], check=True, capture_output=True)

            try:
                text = run_transcription(chunk_path, language)
                all_texts.append(text)
            except Exception as e:
                print(f"[Chunk {i+1}/{total_chunks}] Error: {e}")
                all_texts.append("")

            with jobs_lock:
                jobs[job_id]['progress'] = (i + 1) / total_chunks
                jobs[job_id]['current_chunk'] = i + 1

            cleanup_temp(chunk_path)

        full_text = " ".join(t for t in all_texts if t).strip()

        with jobs_lock:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['result'] = {"text": full_text}

    except Exception as e:
        print(f"[STT Chunking Error] {e}")
        import traceback
        traceback.print_exc()
        with jobs_lock:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = str(e)
    finally:
        cleanup_temp(wav_path)

def cleanup_expired_jobs():
    now = time.time()
    with jobs_lock:
        expired = [jid for jid, j in jobs.items() if now - j.get('created_at', 0) > 300]
        for jid in expired:
            del jobs[jid]

@app.route('/v1/audio/speech', methods=['POST'])
def text_to_speech():
    data = request.json
    if not data or 'input' not in data:
        return jsonify({"error": "Missing 'input' parameter"}), 400

    text = data.get('input')
    voice_name = data.get('voice', 'alloy').lower()
    response_format = data.get('response_format', 'mp3').lower()
    speed = data.get('speed', 1.0)
    language = data.get('language')

    macos_voice = config.VOICE_MAPPING.get(voice_name, config.VOICE_MAPPING['default'])
    
    if language and language in config.LANG_VOICE_MAPPING:
        macos_voice = config.LANG_VOICE_MAPPING[language]

    job_id = str(uuid.uuid4())
    temp_aiff = os.path.join(config.TEMP_DIR, f"{job_id}.aiff")
    output_file = os.path.join(config.TEMP_DIR, f"{job_id}.{response_format}")

    try:
        say_cmd = ['say', '-o', temp_aiff]
        
        wpm = int(200 * speed)
        say_cmd.extend(['-r', str(wpm)])
        
        say_cmd.append(text)
        
        subprocess.run(say_cmd, check=True)

        ffmpeg_cmd = [config.FFMPEG_BIN, '-i', temp_aiff, '-y', output_file]
        
        if response_format == 'opus':
            ffmpeg_cmd.extend(['-c:a', 'libopus'])
        elif response_format == 'aac':
            ffmpeg_cmd.extend(['-c:a', 'aac'])
        
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

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
    language = request.form.get('language', 'en-US')
    response_format = request.form.get('response_format', 'json').lower()

    job_id = str(uuid.uuid4())
    input_path = os.path.join(config.TEMP_DIR, f"{job_id}.tmp")
    wav_path = os.path.join(config.TEMP_DIR, f"{job_id}.wav")
    
    try:
        file.save(input_path)

        subprocess.run([
            config.FFMPEG_BIN, '-i', input_path, 
            '-ar', '16000', '-ac', '1', '-y', wav_path
        ], check=True, capture_output=True)

        cleanup_temp(input_path)

        try:
            duration = get_audio_duration(wav_path)
        except Exception:
            duration = 0

        if duration <= CHUNK_DURATION:
            text = run_transcription(wav_path, language)
            cleanup_temp(wav_path)
            return format_transcription_response(text, language, response_format)
        else:
            total_chunks = math.ceil(duration / CHUNK_DURATION)
            with jobs_lock:
                jobs[job_id] = {
                    'status': 'processing',
                    'progress': 0.0,
                    'current_chunk': 0,
                    'total_chunks': total_chunks,
                    'language': language,
                    'response_format': response_format,
                    'wav_path': wav_path,
                    'result': None,
                    'error': None,
                    'created_at': time.time(),
                }

            thread = threading.Thread(target=process_long_audio, args=(job_id,))
            thread.daemon = True
            thread.start()

            return jsonify({'job_id': job_id}), 202

    except Exception as e:
        print(f"[STT Error] {e}")
        import traceback
        traceback.print_exc()
        cleanup_temp(input_path)
        cleanup_temp(wav_path)
        return jsonify({"error": str(e)}), 500

@app.route('/v1/audio/transcriptions/<job_id>', methods=['GET'])
def transcription_status(job_id):
    cleanup_expired_jobs()
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        return jsonify({
            'job_id': job_id,
            'status': job['status'],
            'progress': job['progress'],
            'current_chunk': job['current_chunk'],
            'total_chunks': job['total_chunks'],
            'result': job['result'],
            'error': job['error'],
        })

@app.route('/v1/voices', methods=['GET'])
def list_voices():
    return jsonify({
        "openai_voices": list(config.VOICE_MAPPING.keys()),
        "mapping": config.VOICE_MAPPING,
        "custom_lang_mapping": config.LANG_VOICE_MAPPING
    })

if __name__ == '__main__':
    use_http = getattr(config, 'USE_HTTP', False)
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
