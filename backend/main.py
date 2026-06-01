from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import os
import io
import time
import datetime
import re
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from fpdf import FPDF
import requests
from sqlalchemy.orm import Session
from database import engine, Base, get_db
import models
import jwt
import bcrypt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# --- INISIALISASI DATABASE SQLITE ---
models.Base.metadata.create_all(bind=engine)
# ------------------------------------

load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
OCR_API_KEY = os.environ.get("OCR_API_KEY")
OCR_URL = os.environ.get("OCR_URL", "https://api.ocr.space/parse/image")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI(title="Nexus Health Backend API")

# --- JWT AUTH SETUP ---
SECRET_KEY = "NEXUS_SUPER_SECRET_KEY_FOR_JWT"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 hari

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user
# ----------------------

# --- Serve Frontend ---
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
os.makedirs(os.path.join(frontend_dir, "css"), exist_ok=True)
os.makedirs(os.path.join(frontend_dir, "js"), exist_ok=True)

app.mount("/css", StaticFiles(directory=os.path.join(frontend_dir, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="js")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Index.html not found</h1>"

# --- AUTH ENDPOINTS ---
class UserCreate(BaseModel):
    name: str
    email: str
    password: str

@app.post("/api/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar!")
    hashed_pwd = get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_pwd, name=user.name)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Registrasi berhasil!"}

@app.post("/api/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Email atau password salah!")
    
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
    return {"access_token": access_token, "token_type": "bearer", "name": user.name, "user_id": user.id}

@app.get("/api/config")
def get_config():
    return {"google_client_id": GOOGLE_CLIENT_ID}

class GoogleAuthRequest(BaseModel):
    credential: str

@app.post("/api/auth/google")
def google_auth(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google Client ID belum disetting di .env")
    
    try:
        idinfo = id_token.verify_oauth2_token(req.credential, google_requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo['email']
        name = idinfo.get('name', 'User Google')
        picture = idinfo.get('picture', '')

        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            user = models.User(email=email, name=name, picture=picture, hashed_password="")
            db.add(user)
            db.commit()
            db.refresh(user)
        
        access_token = create_access_token(data={"sub": user.email, "user_id": user.id})
        return {"access_token": access_token, "token_type": "bearer", "name": user.name, "user_id": user.id}
        
    except ValueError:
        raise HTTPException(status_code=401, detail="Google Token tidak valid")
# ----------------------

# Pydantic Schemas
class ChatRequest(BaseModel):
    patient_id: int
    name: str
    age: int
    gender: str
    weight: float
    conditions: str
    message: str

def check_emergency(text: str) -> bool:
    emergency_keywords = [r"\bbleeding\b", r"\bchest pain\b", r"\bsevere shortness of breath\b", r"\bheart attack\b", r"\bstroke\b", r"\bunconscious\b", r"\bsuicide\b", r"\bberdarah\b", r"\bnyeri dada\b", r"\bsesak napas\b", r"\bserangan jantung\b"]
    text_lower = text.lower()
    for kw in emergency_keywords:
        if re.search(kw, text_lower):
            return True
    return False

def get_rag_context(query: str):
    if not GEMINI_API_KEY: return ""
    try:
        if not os.path.exists("./chroma_db"):
            return ""
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=GEMINI_API_KEY)
        db = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)
        docs = db.similarity_search(query, k=4)
        return "\n".join([doc.page_content for doc in docs])
    except Exception as e:
        print("RAG Error:", e)
        return ""

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Update or Create Patient profile
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        patient = models.Patient(user_id=current_user.id, name=req.name, age=req.age, gender=req.gender, weight=req.weight, conditions=req.conditions)
        db.add(patient)
    else:
        patient.name = req.name
        patient.age = req.age
        patient.gender = req.gender
        patient.weight = req.weight
        patient.conditions = req.conditions
    db.commit()
    
    # Save User Message to SQLite
    user_msg = models.ChatMessage(patient_id=patient.id, role="user", content=req.message)
    db.add(user_msg)
    db.commit()
    
    if check_emergency(req.message):
        em_msg = "🚨 **EMERGENCY DETECTED**: Kata kunci menunjukkan kondisi kritis. Tolong segera hentikan penggunaan AI dan hubungi layanan darurat medis (Ambulans/119) atau segera ke IGD rumah sakit terdekat!"
        ai_msg = models.ChatMessage(patient_id=patient.id, role="assistant", content=em_msg)
        db.add(ai_msg)
        db.commit()
        return {"response": em_msg, "emergency": True}
        
    context = get_rag_context(req.message)
    
    # Get last 6 messages
    recent_history = db.query(models.ChatMessage).filter(models.ChatMessage.patient_id == patient.id).order_by(models.ChatMessage.timestamp.desc()).limit(6).all()
    recent_history.reverse()
    
    history_text = "\n".join([f"{msg.role.upper()}: {msg.content}" for msg in recent_history if msg.content])
    
    sys_prompt = f"""Anda adalah 'Nexus Health AI', sebuah sistem AI Medis tingkat lanjut yang berbasis pada ribuan database konsultasi dokter di Indonesia.
PROFIL PASIEN: {req.name}, {req.age}thn, {req.gender}, {req.weight}kg.
KONDISI SEBELUMNYA: {req.conditions}

REFERENSI MEDIS (Gunakan informasi ini sebagai basis jawaban Anda):
{context}

RIWAYAT OBROLAN:
{history_text}

INSTRUKSI JAWABAN:
1. Jawab dalam Bahasa Indonesia yang profesional, empatik, dan informatif.
2. Gunakan pola jawaban dokter pada "REFERENSI MEDIS" di atas untuk memberikan saran yang spesifik dan praktis.
3. JANGAN memberikan disclaimer panjang di awal. Berikan edukasi gejala dan tips kesehatan terlebih dahulu secara langsung.
4. Jika ada indikasi nilai medis (seperti tensi atau kadar gula), berikan standar nilai normalnya untuk edukasi.
5. Akhiri dengan satu kalimat penutup yang menyarankan konsultasi ke dokter spesialis jika gejala berlanjut."""

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        full_prompt = f"System: {sys_prompt}\nUser: {req.message}"
        response = model.generate_content(full_prompt)
        ans = response.text
    except Exception as e:
        ans = f"API Error: {str(e)}"
        
    # Save AI Message to SQLite
    ai_msg = models.ChatMessage(patient_id=patient.id, role="assistant", content=ans)
    db.add(ai_msg)
    db.commit()
    return {"response": ans, "emergency": False}


@app.get("/api/history/{patient_id}")
def get_history(patient_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        return {"history": []}
    
    messages = db.query(models.ChatMessage).filter(models.ChatMessage.patient_id == patient.id).order_by(models.ChatMessage.timestamp.asc()).all()
    history = [{"role": msg.role, "content": msg.content} for msg in messages]
    return {"history": history}

@app.delete("/api/history/{patient_id}")
def delete_history(patient_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if patient:
        db.query(models.ChatMessage).filter(models.ChatMessage.patient_id == patient.id).delete()
        db.commit()
    return {"status": "success"}

@app.post("/api/vision")
async def vision_endpoint(
    patient_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not GEMINI_API_KEY:
        return {"error": "API Key not found"}
    try:
        contents = await file.read()
        model = genai.GenerativeModel('gemini-2.5-flash')

        if file.content_type == "application/pdf":
            prompt = """Anda adalah Analis Medis Senior. Ekstrak teks dan data dari dokumen MCU / Lab / Resep ini.
Berikan: 1. Ringkasan temuan. 2. Penjelasan nilai abnormal (jika ada) dalam bahasa awam. 3. Kesimpulan."""
            doc_part = {"mime_type": "application/pdf", "data": contents}
            response = model.generate_content([prompt, doc_part])
            ans = response.text
        elif file.content_type.startswith("image/"):
            try:
                files = {"file": (file.filename, contents, file.content_type)}
                data = { "apikey": OCR_API_KEY, "language": "eng", "isOverlayRequired": False, "detectOrientation": True, "scale": True, "OCREngine": 2 }
                
                res = requests.post(OCR_URL, files=files, data=data)
                res_json = res.json()
                
                if res_json.get("IsErroredOnProcessing"):
                    ans = "Error dari OCR.space: " + str(res_json.get("ErrorMessage"))
                else:
                    parsed_results = res_json.get("ParsedResults", [])
                    raw_text = "".join([result.get("ParsedText", "") + "\n" for result in parsed_results])
                        
                    if not raw_text.strip():
                        raw_text = "Tidak ada teks yang dapat dibaca oleh sistem."

                    bonus_prompt = f"Berikut hasil OCR dokumen medis:\n{raw_text}\n\nJelaskan isi dokumen ini dalam bahasa awam."
                    response_gemini = model.generate_content(bonus_prompt)
                    ans = response_gemini.text
            except Exception as e:
                ans = f"Error OCR: {str(e)}"
        else:
            return {"error": "Format file tidak didukung."}

        patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
        if not patient:
            patient = models.Patient(user_id=current_user.id, name="Guest", age=30, gender="Pria", weight=70.0, conditions="None")
            db.add(patient)
            db.commit()

        sync_msg = f"📄 **[DOKUMEN LAB/MCU/RESEP]**\n\nHasil:\n\n{ans}"
        user_msg = models.ChatMessage(patient_id=patient.id, role="user", content=sync_msg)
        ai_msg = models.ChatMessage(patient_id=patient.id, role="assistant", content="Dokumen medis telah disimpan dan dianalisis.")
        db.add(user_msg)
        db.add(ai_msg)
        db.commit()

        return {"result": ans}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/pdf/{patient_id}")
def download_pdf(patient_id: int, token: str, db: Session = Depends(get_db)):
    # Since download_pdf is via window.open, token must be in query string
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    patient = db.query(models.Patient).filter(models.Patient.user_id == user_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    messages = db.query(models.ChatMessage).filter(models.ChatMessage.patient_id == patient.id).order_by(models.ChatMessage.timestamp.asc()).all()
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 24)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(0, 15, "NEXUS HEALTH AI", ln=True, align='C')
    pdf.set_font("Helvetica", 'I', 11)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 8, "Official Patient Medical Record", ln=True, align='C')
    pdf.cell(0, 6, f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
    pdf.line(10, 40, 200, 40)
    pdf.ln(15)
    
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, "  PATIENT PROFILE", ln=True, fill=True)
    pdf.ln(5)
    
    pdf.set_font("Helvetica", '', 11)
    pdf.cell(100, 8, f"Name: {patient.name}")
    pdf.cell(90, 8, f"Age / Gender: {patient.age} years / {patient.gender}", ln=True)
    pdf.ln(10)
    
    for m in messages:
        safe_text = m.content.encode('latin-1', 'replace').decode('latin-1')
        role_title = "Patient:" if m.role == "user" else "Nexus AI:"
        pdf.set_font("Helvetica", 'B', 11)
        pdf.cell(0, 8, role_title, ln=True)
        pdf.set_font("Helvetica", '', 11)
        pdf.multi_cell(0, 6, safe_text)
        pdf.ln(4)
        
    pdf_file_path = f"summary_{patient_id}.pdf"
    pdf.output(pdf_file_path)
    return FileResponse(path=pdf_file_path, filename=f"Nexus_Health_Report_{patient_id}.pdf", media_type='application/pdf')
