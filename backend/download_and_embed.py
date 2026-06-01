import os
import urllib.request
import csv
import io
import time
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("❌ ERROR: GEMINI_API_KEY tidak ditemukan di file .env")
    exit()

print("--- Memulai Injeksi 'Otak' Medis dari Dataset hermanshid/doctor-id-qa ---")
url = "https://huggingface.co/datasets/hermanshid/doctor-id-qa/resolve/main/train.csv"

try:
    print(f"[*] Mengunduh data dari: {url}")
    req = urllib.request.urlopen(url)
    # Gunakan TextIOWrapper dengan encoding utf-8
    reader = csv.reader(io.TextIOWrapper(req, encoding='utf-8'))
    header = next(reader) # skip header
    print(f"[OK] Data terhubung. Header ditemukan: {header}")
except Exception as e:
    print(f"[ERROR] Gagal mengunduh dataset: {e}")
    exit()

documents = []
metadatas = []

# Mengambil semua data (sekitar 6.300+)
MAX_DATA = 7000 
count = 0

print("[*] Mengekstrak tanya-jawab medis...")
for row in reader:
    if len(row) >= 2:
        question = row[0]
        answer = row[1]
        
        # Format dokumen agar RAG memiliki konteks yang jelas
        doc_text = f"RIWAYAT KONSULTASI MEDIS:\nPasien: {question}\nDokter: {answer}"
        documents.append(doc_text)
        metadatas.append({"source": "hermanshid/doctor-id-qa", "row": count})
        
        count += 1
        if count >= MAX_DATA:
            break

print(f"[SUCCESS] Berhasil mengekstrak {count} kasus medis!")

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=api_key)
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")

print(f"[*] Memulai proses Embedding ke ChromaDB ({db_path})...")
print("Ini mungkin memakan waktu beberapa menit karena jumlah data yang besar.")

# Pecah menjadi batch agar stabil dan menghindari limit API
batch_size = 200
for i in range(0, len(documents), batch_size):
    batch_docs = documents[i:i+batch_size]
    batch_metas = metadatas[i:i+batch_size]
    
    print(f"[*] Memproses batch {i // batch_size + 1} ({i} sampai {min(i + batch_size, len(documents))})...")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            vectorstore = Chroma.from_texts(
                texts=batch_docs,
                embedding=embeddings,
                metadatas=batch_metas,
                persist_directory=db_path
            )
            vectorstore.persist()
            break
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                print(f"[!] Rate limit (429) terdeteksi. Menunggu 60 detik sebelum mencoba lagi... (Percobaan {attempt + 1})")
                time.sleep(60)
            else:
                print(f"[ERROR] Gagal memproses batch {i}: {e}")
                # Jangan exit agar batch lain bisa dicoba (atau exit jika kritis)
                break
    
    # Delay antar batch untuk keamanan kuota
    time.sleep(10)


print("\n" + "="*60)
print("SELESAI! Nexus Health AI kini memiliki 6.300+ referensi medis.")
print("Sekarang AI Anda jauh lebih pintar dalam menjawab kasus medis nyata.")
print("="*60)


