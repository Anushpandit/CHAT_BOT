# 🚀 DriveChat: Multi-Modal AI Knowledge Agent

DriveChat is an end-to-end Retrieval-Augmented Generation (RAG) pipeline and web application designed to turn your Google Drive folders and local files into an interactive, highly intelligent knowledge base. 

Unlike standard text-based RAG systems, DriveChat is **Multi-Modal**. It can read plain text, parse complex spreadsheets, extract text from PDFs, and use **Vision AI** to actually "see" and describe images, charts, and scanned documents.

---

## ✨ Key Features

- **📂 Seamless Google Drive Integration:** Simply paste a Google Drive folder or file link. The backend securely authenticates, recursively traverses folders, and downloads files for indexing.
- **💻 Local File Uploads:** Drop files directly from your computer into the web UI for instant processing.
- **👁️ Multi-Modal Vision Extraction:** Uses `Llama-3.2-Vision` (via Groq) to analyze images and diagrams. If vision fails, it falls back to native Tesseract OCR.
- **📊 Native Spreadsheet & Word Parsing:** Intelligently reads `.xlsx`, `.csv`, and `.docx` files, preserving tabular structures so the LLM can answer data-driven questions.
- **⚡ Ultra-Fast Inference:** Powered by Groq's LPU hardware, fetching answers from `Llama-3.3-70B` or `Mixtral-8x7B` in milliseconds.
- **🧠 Semantic Vector Search:** Chunks and embeds documents using `sentence-transformers` (`all-MiniLM-L6-v2`) and stores them locally in **ChromaDB**.
- **🎨 Modern React UI:** A sleek, responsive chat interface featuring interactive source-tag citations, document-specific filtering, and dynamic Markdown rendering.

---

## 🛠️ Tech Stack

**Frontend:**
- React.js + Vite
- Vanilla CSS (Custom modern styling)

**Backend:**
- FastAPI (Asynchronous REST API)
- Python 3.10+
- Uvicorn

**AI & Data Pipeline:**
- **LLM / Vision:** Groq Cloud API
- **Vector Database:** ChromaDB (Local embedded)
- **Embeddings:** HuggingFace `sentence-transformers`
- **Extraction Tools:** PyMuPDF (`fitz`), `pytesseract`, `python-docx`, `pandas`, `Pillow`

---

## 🏗️ Architecture & Pipeline

DriveChat operates in 4 distinct phases under the hood:

1. **Phase 1: Fetcher (`fetcher.py`)** 
   Connects to Google Drive via OAuth2 or Service Accounts. It parses Drive URLs, resolves folder trees, and handles Google-native exports (converting Google Docs to DOCX, Google Sheets to XLSX).
   
2. **Phase 2: Content Extractor (`extractor.py`)** 
   The master dispatcher. It checks MIME types and routes files to specialized parsers:
   - *PDFs:* PyMuPDF (with Tesseract OCR fallback for scanned pages).
   - *Images:* Groq Vision API (with Tesseract fallback).
   - *Office Docs:* `python-docx` and `pandas`.
   - *Text:* Native UTF-8 decoding.

3. **Phase 3: Ingestion & Vectorization (`chunker.py`, `embedder.py`, `vector_store.py`)** 
   Text is intelligently chunked with dynamic overlap to preserve context. Chunks are hashed (MD5) to prevent duplicates, embedded into numerical vectors, and persisted to `./chroma_db`.

4. **Phase 4: Chatbot & API (`main.py`, `chatbot.py`)** 
   The FastAPI layer orchestrates the retrieval. When a user asks a question, the backend embeds the query, searches ChromaDB for the Top-K chunks, and constructs a strict prompt for the LLM. It returns the answer along with exact source citations.

---

## 🚀 Setup Instructions

### 1. Prerequisites
- **Python 3.10+** installed.
- **Node.js (v18+)** installed.
- **Tesseract OCR** installed on your system:
  - macOS: `brew install tesseract`
  - Linux: `sudo apt-get install tesseract-ocr`
  - Windows: Download the installer from the UB-Mannheim repository.

### 2. Backend Setup
Clone the repository and set up your Python environment:
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

### 4. Environment Variables & Authentication
1. Create a `.env` file in the root directory based on `.env.example`:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```
2. **Google Drive Auth:** To use the Drive link ingestion, you need Google Cloud credentials. Place your `service_account.json` OR OAuth `credentials.json` in the root folder.

---

## 🕹️ Usage

**1. Start the Backend Server**
Open a terminal in the root directory:
```bash
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**2. Start the Frontend Server**
Open a second terminal:
```bash
cd frontend
npm run dev
```

**3. Start Chatting!**
- Open your browser to `http://localhost:5173`.
- Paste a Google Drive link in the sidebar or click **Upload Local File**.
- Wait a few seconds for the ingestion pipeline to process and vectorize your documents.
- Ask questions, ask for summaries, and click on the source tags to filter the chat by specific documents!

---

## 📝 License
MIT License. Feel free to fork and build upon this knowledge agent!
