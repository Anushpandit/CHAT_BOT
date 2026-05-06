# Google Drive AI Chatbot Pipeline

An end-to-end pipeline to fetch documents from Google Drive, extract content (including OCR and Vision for images), chunk the text, embed it into a local vector database, and chat with it using Groq.

## Architecture

*   **Phase 1: Fetcher (`fetcher.py`)** - Connects to Google Drive using OAuth2/Service Accounts, parses Drive URLs, and downloads files recursively. Exports Google Docs/Sheets to DOCX/XLSX.
*   **Phase 2: Content Extractor (`extractor.py`, `extraction_pipeline.py`)** - Parses text from PDFs (PyMuPDF), scanned documents (Tesseract OCR), images (Groq Vision API + Tesseract fallback), Word documents (`python-docx`), and Spreadsheets (`pandas`).
*   **Phase 3: Ingestion & Vector Store (`chunker.py`, `embedder.py`, `vector_store.py`, `ingestion_pipeline.py`)** - Intelligently chunks extracted text by format type, embeds them using `sentence-transformers` (`all-MiniLM-L6-v2`), and stores them locally using `ChromaDB`.
*   **Phase 4: Chatbot (`chat.py`)** - (In progress) A retrieval-augmented generation (RAG) chatbot using the Groq API.

## Setup Instructions

1.  **Clone and Install Dependencies**
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **System Dependencies**
    *   You must install Tesseract OCR on your system for image/scanned PDF fallbacks to work. On macOS: `brew install tesseract`.
3.  **Authentication & API Keys**
    *   Create a `.env` file and add your Groq API key: `GROQ_API_KEY=your_key_here`.
    *   Place your Google Cloud `credentials.json` (OAuth) or `service_account.json` in the root directory to access private Drive files.

## Usage

**1. Fetch files from Drive**
```bash
python fetcher.py "YOUR_GOOGLE_DRIVE_LINK" --out ./my_downloads
```

**2. Test Extraction locally**
Place a file in `./test_files/` and run:
```bash
python test_extractor.py
```

**3. Ingest files to ChromaDB**
```bash
python ingestion_pipeline.py
```
