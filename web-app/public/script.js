// TTS elements
const generateBtn = document.getElementById('generateBtn');
const textInput = document.getElementById('textInput');
const audioPlayer = document.getElementById('audioPlayer');
const ttsStatus = document.getElementById('ttsStatus');

// STT elements
const transcribeBtn = document.getElementById('transcribeBtn');
const audioFile = document.getElementById('audioFile');
const langSelect = document.getElementById('langSelect');
const sttStatus = document.getElementById('sttStatus');
const sttResult = document.getElementById('sttResult');

// TTS Logic
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
                voice: 'alloy', // server uses system default regardless
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

// STT Logic
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

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('language', language);

        const response = await fetch('/api/transcribe', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || 'Errore nella trascrizione');
        }

        const data = await response.json();
        sttResult.textContent = data.text || "Nessun testo rilevato.";
        sttStatus.textContent = "Completato!";
    } catch (error) {
        console.error(error);
        sttStatus.textContent = "Errore: " + error.message;
        sttResult.textContent = "Errore durante la trascrizione.";
    } finally {
        transcribeBtn.disabled = false;
    }
});
