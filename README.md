# DriveChat - Multi-Modal AI Knowledge Agent

An end-to-end RAG pipeline and web application to fetch documents from Google Drive or local uploads, extract content (including OCR and Vision for images), chunk the text, embed it into a local vector database, and chat with it using Groq's fast LLMs.

## Features

- **Multi-Modal Ingestion:** Supports PDFs, Images, Word Docs, Spreadsheets, and plain text.
- **Google Drive Integration:** Simply paste a Google Drive folder or file link to index entire directories securely.
- **Local File Uploads:** Upload documents directly from your computer.
- **Advanced Extraction:** Uses PyMuPDF for PDFs, `pandas` for spreadsheets, and Groq Vision (Llama-4-Vision) + Tesseract OCR for images and scanned documents.
- **Vector Search:** Powered by `sentence-transformers` and `ChromaDB` for accurate semantic retrieval.
- **FastAPI Backend:** Robust REST API handling asynchronous ingestion and RAG querying.
- **React Frontend:** Beautiful, modern UI with source-tag citations, dynamic theme support, and document filtering.

## Setup Instructions

1. **Clone and Install Backend Dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install Frontend Dependencies**
   ```bash
   cd frontend
   npm install
   ```

3. **System Dependencies**
   - You must install Tesseract OCR on your system for image/scanned PDF fallbacks to work. On macOS: `brew install tesseract`.

4. **Authentication & API Keys**
   - Create a `.env` file in the root directory: `GROQ_API_KEY=your_key_here`.
   - To use Google Drive ingestion, place your Google Cloud `credentials.json` (OAuth) or `service_account.json` in the root directory.

## Usage

**1. Start the Backend**
```bash
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**2. Start the Frontend**
```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser. Paste a Drive link or upload a local file to start indexing, and then ask questions about your documents!
