# Menggunakan image Python 3.10 yang ringan
FROM python:3.10-slim

# Menghindari buffering log
ENV PYTHONUNBUFFERED=1

# Syarat Wajib Hugging Face: Menjalankan aplikasi sebagai non-root (User ID 1000)
RUN useradd -m -u 1000 user

# Beralih ke user baru
USER user

# Mendaftarkan path lokal agar pip install dikenali
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Menyalin file requirements
COPY --chown=user ./requirements.txt requirements.txt

# Menginstal semua library yang dibutuhkan
RUN pip install --no-cache-dir -r requirements.txt

# Menyalin seluruh file project ke dalam direktori kerja (/app) dengan hak akses user
COPY --chown=user . /app

# Hugging Face Spaces mewajibkan aplikasi berjalan di port 7860
EXPOSE 7860

# Perintah untuk menjalankan server FastAPI Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
