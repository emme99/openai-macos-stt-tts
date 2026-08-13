import os
import math
import subprocess
import uuid
import ssl
import threading
import time
import json
import tempfile
import re
from flask import Flask, request, jsonify, send_file
import config

app = Flask(__name__)

CHUNK_DURATION = 15
JOB_TTL = getattr(config, 'JOB_TTL', 900)
SUBPROCESS_TIMEOUT = getattr(config, 'SUBPROCESS_TIMEOUT', 60)
MAX_CONCURRENT_JOBS = getattr(config, 'MAX_CONCURRENT_JOBS', 2)

jobs = {}
jobs_lock = threading.Lock()
active_threads = []
active_lock = threading.Lock()
semaphore = threading.BoundedSemaphore(MAX_CONCURRENT_JOBS)

TTS_FORMATS = {'mp3', 'opus', 'aac', 'flac', 'wav', 'pcm'}
STT_FORMATS = {'json', 'text', 'verbose_json', 'srt', 'vtt'}

def generate_self_signed_cert():
    if not os.path.exists(config.CERT_FILE) or not os.path.exists(config.KEY_FILE):
        print("Generating self-signed certificate...")
        try:
            subprocess.run([
                'openssl', 'req', '-x509', '-newkey', 'rsa:2048', 
                '-keyout', config.KEY_FILE, '-out', config.CERT_FILE, 
                '-days', '365', '-nodes', '-subj', '/CN=localhost'
            ], check=True, timeout=SUBPROCESS_TIMEOUT)
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
    ], capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
    return float(result.stdout.strip())

def run_transcription(wav_path, language):
    transcribe_cmd = [config.MACOS_TRANSCRIBE_BIN, wav_path, '--locale', language, '--json']
    result = subprocess.run(transcribe_cmd, capture_output=True, text=True, check=True, timeout=SUBPROCESS_TIMEOUT)
    try:
        parsed = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"macos-transcribe returned invalid JSON: {result.stdout[:200]}") from e
    if isinstance(parsed, list):
        texts = [s.get('text', '') for s in parsed]
        result_text = " ".join(texts)
        # Normalize multiple spaces at chunk boundaries
        result_text = re.sub(r' +', ' ', result_text).strip()
        return result_text
    return result.stdout.strip()

def cleanup_temp(filepath):
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
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
    try:
        semaphore.acquire(timeout=30)
    except TimeoutError:
        with jobs_lock:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = 'Could not acquire processing slot (max concurrent jobs reached)'
        return

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
            ], check=True, capture_output=True, timeout=SUBPROCESS_TIMEOUT)

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
        # Normalize multiple spaces at chunk boundaries (Item #7)
        full_text = re.sub(r' +', ' ', full_text)

        with jobs_lock:
            jobs[job_id]['status'] = 'completed'
            jobs[job_id]['result'] = {"text": full_text}

    except subprocess.TimeoutExpired as e:
        print(f"[STT Timeout] Chunk process timed out: {e}")
        with jobs_lock:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = f'Transcription chunk timed out after {SUBPROCESS_TIMEOUT}s'
    except Exception as e:
        print(f"[STT Chunking Error] {e}")
        import traceback
        traceback.print_exc()
        with jobs_lock:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = str(e)
    finally:
        cleanup_temp(wav_path)
        semaphore.release()

def cleanup_expired_jobs():
    now = time.time()
    with jobs_lock:
        expired = [jid for jid, j in jobs.items() if now - j.get('created_at', 0) > JOB_TTL]
        for jid in expired:
            del jobs[jid]

def background_job_cleaner():
    """Periodically clean up expired jobs in a separate thread."""
    while True:
        time.sleep(60)
        cleanup_expired_jobs()

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

    # Item #5: Whitelist allowed TTS response formats
    if response_format not in TTS_FORMATS:
        return jsonify({"error": f"Unsupported response format '{response_format}'. Allowed: {', '.join(sorted(TTS_FORMATS))}"}), 400

    job_id = str(uuid.uuid4())
    temp_aiff = os.path.join(config.TEMP_DIR, f"{job_id}.aiff")
    output_file = os.path.join(config.TEMP_DIR, f"{job_id}.{response_format}")

    try:
        # Item #6: Write text to a temporary file instead of passing as CLI argument
        text_fd, text_tmp_path = tempfile.mkstemp(suffix='.txt')
        try:
            with os.fdopen(text_fd, 'w') as f:
                f.write(text)
            
            say_cmd = ['say', '-f', text_tmp_path, '-o', temp_aiff]
            
            wpm = int(200 * speed)
            say_cmd.extend(['-r', str(wpm)])
            
            subprocess.run(say_cmd, check=True, timeout=SUBPROCESS_TIMEOUT)
        finally:
            cleanup_temp(text_tmp_path)

        ffmpeg_cmd = [config.FFMPEG_BIN, '-i', temp_aiff, '-y', output_file]
        
        if response_format == 'opus':
            ffmpeg_cmd.extend(['-c:a', 'libopus'])
        elif response_format == 'aac':
            ffmpeg_cmd.extend(['-c:a', 'aac'])
        
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, timeout=SUBPROCESS_TIMEOUT)

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
        # Item #1: Clean up temp files after every request
        cleanup_temp(temp_aiff)
        cleanup_temp(output_file)

@app.route('/v1/audio/transcriptions', methods=['POST'])
def speech_to_text():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    language = request.form.get('language', 'en-US')
    response_format = request.form.get('response_format', 'json').lower()

    # Item #5: Whitelist allowed STT response formats
    if response_format not in STT_FORMATS:
        return jsonify({"error": f"Unsupported response format '{response_format}'. Allowed: {', '.join(sorted(STT_FORMATS))}"}), 400

    job_id = str(uuid.uuid4())
    input_path = os.path.join(config.TEMP_DIR, f"{job_id}.tmp")
    wav_path = os.path.join(config.TEMP_DIR, f"{job_id}.wav")
    
    try:
        file.save(input_path)

        subprocess.run([
            config.FFMPEG_BIN, '-i', input_path, 
            '-ar', '16000', '-ac', '1', '-y', wav_path
        ], check=True, capture_output=True, timeout=SUBPROCESS_TIMEOUT)

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

            # Item #9: Non-daemon thread instead of daemon
            thread = threading.Thread(target=process_long_audio, args=(job_id,), daemon=False)
            with active_lock:
                # Clean up finished threads periodically
                active_threads[:] = [t for t in active_threads if t.is_alive()]
                active_threads.append(thread)
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
    # Start background job cleaner (Item #4)
    cleaner_thread = threading.Thread(target=background_job_cleaner, daemon=True)
    cleaner_thread.start()

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
