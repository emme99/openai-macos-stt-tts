const express = require('express');
const axios = require('axios');
const cors = require('cors');
const path = require('path');

const https = require('https');

const multer = require('multer');
const FormData = require('form-data');
const fs = require('fs');

const app = express();
const PORT = 3000;

// Read USE_HTTP from parent .env
function useHttp() {
    try {
        const envPath = path.join(__dirname, '..', '.env');
        const envContent = fs.readFileSync(envPath, 'utf-8');
        const match = envContent.match(/^USE_HTTP=(.+)$/m);
        if (match) return match[1].trim().toLowerCase() === 'true';
    } catch (_) {}
    return false; // default HTTPS (matching config.py)
}

const USE_HTTP = useHttp();
const protocol = USE_HTTP ? 'http' : 'https';
const API_BASE_URL = `${protocol}://localhost:5050/v1/audio`;

// Only use custom https agent when using HTTPS with self-signed cert
const httpsAgent = USE_HTTP ? undefined : new https.Agent({ rejectUnauthorized: false });

// Multer for file uploads
const upload = multer({ dest: 'uploads/' });

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// TTS Proxy endpoint
app.post('/api/generate', async (req, res) => {
    try {
        const { text, voice, language, response_format } = req.body;

        const axiosConfig = {
            responseType: 'arraybuffer',
            headers: { 'Content-Type': 'application/json' },
        };
        if (httpsAgent) axiosConfig.httpsAgent = httpsAgent;

        const response = await axios.post(`${API_BASE_URL}/speech`, {
            model: "macos-native",
            input: text,
            voice: voice || 'alloy',
            language: language || 'it',
            response_format: response_format || 'mp3'
        }, axiosConfig);

        const contentType = response.headers['content-type'];
        res.set('Content-Type', contentType);
        res.send(response.data);
    } catch (error) {
        console.error('Error proxying to TTS service:', error.message);
        res.status(error.response?.status || 500).send(error.response?.data || 'Error communicating with TTS service');
    }
});

// STT Proxy endpoint
app.post('/api/transcribe', upload.single('file'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).send('No file uploaded');
        }

        const formData = new FormData();
        formData.append('file', fs.createReadStream(req.file.path), {
            filename: req.file.originalname,
            contentType: req.file.mimetype
        });
        formData.append('model', 'whisper-1');
        formData.append('language', req.body.language || 'it-IT');
        formData.append('response_format', 'json');

        const axiosConfig = {
            headers: { ...formData.getHeaders() },
        };
        if (httpsAgent) axiosConfig.httpsAgent = httpsAgent;

        const response = await axios.post(`${API_BASE_URL}/transcriptions`, formData, axiosConfig);

        // Cleanup temp upload
        fs.unlinkSync(req.file.path);

        res.json(response.data);
    } catch (error) {
        console.error('Error proxying to STT service:', error.message);
        if (req.file && fs.existsSync(req.file.path)) fs.unlinkSync(req.file.path);
        res.status(error.response?.status || 500).send(error.response?.data || 'Error communicating with STT service');
    }
});

app.listen(PORT, () => {
    console.log(`Web tester running at http://localhost:${PORT}`);
});
