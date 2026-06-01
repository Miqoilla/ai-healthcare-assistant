---
title: Nexus Health AI
emoji: ⚕️
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---
# Nexus Health AI - Healthcare Assistant

**Nexus Health AI** adalah asisten medis cerdas berbasis Artificial Intelligence yang dirancang untuk memberikan panduan gejala, tips kesehatan preventif, analisis dokumen medis (Lab/Resep), dan edukasi kesehatan kepada pasien.

Aplikasi ini menggunakan teknologi *Large Language Models* (LLM) melalui Google Gemini API, dengan infrastruktur basis data lokal (*zero external database dependency*) yang sangat aman.

⚠️ **Disclaimer:** *Sistem ini dirancang murni untuk tujuan informasi dan edukasi. Aplikasi ini BUKAN pengganti diagnosis medis profesional dari dokter.*

## ✨ Fitur Utama

1. **Symptom-Based Guidance System**: AI menganalisis gejala berdasarkan profil unik pasien (umur, berat badan, gender, riwayat medis).
2. **AI Medical Scanner (Vision)**: Fitur *Optical Character Recognition* (OCR) dan AI Vision untuk mengekstrak dan menjelaskan teks dari dokumen medis seperti PDF hasil MCU, Resep Dokter, atau gambar Hasil Lab.
3. **Advanced Voice Interactions**: Terintegrasi dengan *Web Speech API* untuk fitur *Speech-to-Text* (input suara pasien) dan *Text-to-Speech* (AI merespons dengan suara bahasa Indonesia).
4. **Secure Authentication**: Sistem otentikasi ganda menggunakan email terenkripsi (AES-256/Bcrypt) dan Google OAuth 2.0.
5. **Emergency Detection**: Secara otomatis mendeteksi kata kunci darurat (seperti serangan jantung, stroke, depresi) dan memberikan peringatan IGD.
6. **Ekspor Rekam Medis**: Fitur untuk mengunduh seluruh sesi konsultasi ke dalam format dokumen PDF yang rapi.
7. **Premium UI/UX**: Antarmuka *glassmorphism* modern dengan dukungan Mode Terang (*Light Mode*) dan Mode Gelap (*Dark Mode*).

## 🛠️ Teknologi yang Digunakan

*   **Backend:** Python 3, FastAPI, Uvicorn, SQLAlchemy
*   **Frontend:** Vanilla HTML5, CSS3 (Custom Variables), JavaScript (ES6)
*   **Database:** SQLite (Relational), ChromaDB (Vector Search / RAG)
*   **AI Engine:** Google Gemini 2.5 Flash, Gemini Embedding 001
*   **Integrations:** Google OAuth 2.0, OCR.Space API, Web Speech API

## 🚀 Cara Instalasi & Menjalankan Aplikasi

Karena aplikasi ini didesain beroperasi secara penuh di *localhost* tanpa *database dependency*, cara menjalankannya sangat mudah.

### 1. Prasyarat
Pastikan Python 3.9+ sudah terinstal di komputer Anda.

### 2. Instalasi Library
Buka terminal dan jalankan perintah berikut di direktori project:
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Environment (Variabel Lingkungan)
Edit atau buat file `.env` di folder utama aplikasi, dan isi dengan kredensial API Anda:
```env
GEMINI_API_KEY=KODE_API_GEMINI_ANDA
GOOGLE_CLIENT_ID=KODE_OAUTH_GOOGLE_ANDA.apps.googleusercontent.com
OCR_API_KEY=KODE_API_OCR_ANDA
OCR_URL=https://api.ocr.space/parse/image
```

### 4. Menjalankan Server
Buka terminal, masuk ke folder `backend`, lalu jalankan *server* Uvicorn:
```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 5. Akses Aplikasi
Buka web browser dan kunjungi:
**http://localhost:8000**
