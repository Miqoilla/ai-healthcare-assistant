import os
from fpdf import FPDF
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

load_dotenv()

def create_mock_medical_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    
    text = """CLINICAL MEDICAL GUIDELINES:
1. Hypertension (High Blood Pressure): Standard treatment includes ACE inhibitors or Calcium Channel Blockers like Amlodipine. Side effects may include dizziness or ankle swelling. Patients should reduce sodium intake and monitor BP regularly.
2. Diabetes Type 2: First-line medication is Metformin. Side effects can include gastrointestinal issues. Monitor blood sugar regularly and limit simple carbohydrates.
3. Common Cold / Viral URTI: Antibiotics are ineffective against viruses. Treatment includes rest, hydration, and acetaminophen or ibuprofen for fever.
4. Asthma: Albuterol is used as a rescue inhaler for acute shortness of breath. Corticosteroids are used for long-term maintenance.
5. Peptic Ulcer Disease: Often treated with Proton Pump Inhibitors (PPIs) like Omeprazole. Patients should avoid spicy foods, alcohol, and NSAIDs.
6. Mental Health & Basic Psychological Support: Mild stress and anxiety can be managed with mindfulness breathing exercises, maintaining a regular sleep schedule, and digital detox. Professional psychological counseling is recommended for persistent depression.
"""
    pdf.multi_cell(0, 8, text=text)
    pdf.output("medical_knowledge.pdf")
    print("[1/3] Created real medical PDF: medical_knowledge.pdf")

def setup_persistent_rag():
    if not os.path.exists("medical_knowledge.pdf"):
        create_mock_medical_pdf()
        
    print("[2/3] Loading and Chunking PDF...")
    loader = PyPDFLoader("medical_knowledge.pdf")
    docs = loader.load()
    
    # Chunking
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(docs)
    
    print("[3/3] Embedding and Storing in Persistent ChromaDB...")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=os.environ.get("GEMINI_API_KEY"))
    
    # Store with persist_directory
    db = Chroma.from_documents(chunks, embeddings, persist_directory="./chroma_db")
    print("✅ Success: Persistent ChromaDB created successfully.")

if __name__ == "__main__":
    setup_persistent_rag()
