const generateBtn = document.getElementById('generateBtn');
const textInput = document.getElementById('textInput');
const audioPlayer = document.getElementById('audioPlayer');
const ttsStatus = document.getElementById('ttsStatus');

const transcribeBtn = document.getElementById('transcribeBtn');
const audioFile = document.getElementById('audioFile');
const langSelect = document.getElementById('langSelect');
const sttStatus = document.getElementById('sttStatus');
const sttResult = document.getElementById('sttResult');
const progressContainer = document.getElementById('progressContainer');
const progressBar = document.getElementById('progressBar');
const progressText = document.getElementById('progressText');

generateBtn.addEventListener('click', async () => {
    const text = textInput.value;

    if (!text) {
        alert("Inserisci del testo!");
        return;
    }

    generateBtn.disabled = true;
    ttsStatus.textContent = "Sintesi in corso...";

    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                voice: 'alloy',
                response_format: 'mp3'
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Errore nella generazione');
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        audioPlayer.src = url;
        audioPlayer.play();
        ttsStatus.textContent = "Completato!";
    } catch (error) {
        console.error(error);
        ttsStatus.textContent = "Errore: " + error.message;
    } finally {
        generateBtn.disabled = false;
    }
});

transcribeBtn.addEventListener('click', async () => {
    const file = audioFile.files[0];
    const language = langSelect.value;

    if (!file) {
        alert("Seleziona un file audio!");
        return;
    }

    transcribeBtn.disabled = true;
    sttStatus.textContent = "Trascrizione in corso...";
    sttResult.textContent = "Elaborazione...";
    progressContainer.style.display = 'block';
    updateProgress(0, 0);

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('language', language);

        const response = await fetch('/api/transcribe', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error((await response.text()) || 'Errore nella trascrizione');
        }

        if (response.status === 202) {
            const { job_id } = await response.json();
            await pollJobStatus(job_id);
        } else {
            const data = await response.json();
            sttResult.textContent = data.text || "Nessun testo rilevato.";
            sttStatus.textContent = "Completato!";
        }
    } catch (error) {
        console.error(error);
        sttStatus.textContent = "Errore: " + error.message;
        sttResult.textContent = "Errore durante la trascrizione.";
    } finally {
        transcribeBtn.disabled = false;
        progressContainer.style.display = 'none';
    }
});

async function pollJobStatus(jobId) {
    while (true) {
        const response = await fetch(`/api/transcribe/status/${jobId}`);
        const data = await response.json();

        if (data.status === 'completed') {
            sttResult.textContent = data.result?.text || "Nessun testo rilevato.";
            sttStatus.textContent = "Completato!";
            return;
        }

        if (data.status === 'error') {
            throw new Error(data.error || 'Errore nella trascrizione');
        }

        if (data.total_chunks > 0) {
            updateProgress(data.current_chunk, data.total_chunks);
            sttStatus.textContent = `Trascrizione in corso... (chunk ${data.current_chunk}/${data.total_chunks})`;
        }

        await new Promise(r => setTimeout(r, 600));
    }
}

function updateProgress(current, total) {
    if (total === 0) {
        progressBar.style.width = '30%';
        progressBar.classList.add('indeterminate');
        progressText.textContent = "Preparazione chunk...";
        return;
    }
    progressBar.classList.remove('indeterminate');
    const pct = Math.round((current / total) * 100);
    progressBar.style.width = pct + '%';
    progressText.textContent = `${current}/${total} chunk (${pct}%)`;
}
