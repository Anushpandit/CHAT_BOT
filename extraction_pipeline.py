import os
import logging
from typing import List, Dict, Any
from extractor import extract_content, ExtractedContent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")


# ─────────────────────────────────────────────
# Simulated Drive file list (replace with real
# Google Drive API output from Phase 1)
# ─────────────────────────────────────────────

SAMPLE_DRIVE_FILES: List[Dict[str, Any]] = [
    {
        "id": "file_001",
        "name": "report.pdf",
        "mimeType": "application/pdf",
        "size": 204800,
    },
    {
        "id": "file_002",
        "name": "invoice_scan.png",
        "mimeType": "image/png",
        "size": 512000,
    },
    {
        "id": "file_003",
        "name": "notes.txt",
        "mimeType": "text/plain",
        "size": 2048,
    },
    {
        "id": "file_004",
        "name": "project_spec.docx",
        "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "size": 30720,
    },
    {
        "id": "file_005",
        "name": "data.xlsx",
        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "size": 10240,
    },
]


# ─────────────────────────────────────────────
# Drive Downloader (from Phase 1)
# ─────────────────────────────────────────────

def download_file_bytes(file_id: str, drive_service) -> bytes:
    """
    Download raw bytes for a file from Google Drive.
    """
    from googleapiclient.http import MediaIoBaseDownload
    import io

    request = drive_service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    return buffer.getvalue()


def download_gdoc_as_docx(file_id: str, drive_service) -> bytes:
    """Export Google Doc as .docx bytes."""
    import io
    request = drive_service.files().export_media(
        fileId=file_id,
        mimeType="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    buffer = io.BytesIO()
    from googleapiclient.http import MediaIoBaseDownload
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


# ─────────────────────────────────────────────
# Main Pipeline Function
# ─────────────────────────────────────────────

def run_extraction_pipeline(
    drive_files: List[Dict[str, Any]],
    drive_service=None,               # Pass real Drive service from Phase 1
    use_vision_for_images: bool = True,
    use_local_files: bool = False,    # For local testing without Drive
    local_file_dir: str = "./test_files",
) -> List[ExtractedContent]:
    """
    Process a list of Drive file metadata through the extraction pipeline.
    """
    results: List[ExtractedContent] = []

    for file_meta in drive_files:
        file_id   = file_meta.get("id", "")
        file_name = file_meta.get("name", "")
        mime_type = file_meta.get("mimeType", "")

        logger.info(f"Processing: {file_name} ({mime_type})")

        try:
            # ── Fetch bytes ──────────────────────────────────────
            if use_local_files:
                # Local testing mode
                local_path = os.path.join(local_file_dir, file_name)
                with open(local_path, "rb") as f:
                    file_bytes = f.read()

            elif mime_type == "application/vnd.google-apps.document":
                # Google Docs must be exported
                file_bytes = download_gdoc_as_docx(file_id, drive_service)
                mime_type  = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

            elif mime_type == "application/vnd.google-apps.spreadsheet":
                # Google Sheets must be exported
                import io
                from googleapiclient.http import MediaIoBaseDownload
                req = drive_service.files().export_media(
                    fileId=file_id,
                    mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                buf = io.BytesIO()
                dl = MediaIoBaseDownload(buf, req)
                done = False
                while not done:
                    _, done = dl.next_chunk()
                file_bytes = buf.getvalue()
                mime_type  = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            else:
                file_bytes = download_file_bytes(file_id, drive_service)

            # ── Extract content ──────────────────────────────────
            content = extract_content(
                file_bytes=file_bytes,
                file_name=file_name,
                mime_type=mime_type,
                use_vision_for_images=use_vision_for_images,
            )

            # ── Log result ───────────────────────────────────────
            if content.error:
                logger.warning(f"  ⚠ Error in '{file_name}': {content.error}")
            else:
                preview = content.text[:80].replace("\n", " ")
                logger.info(f"  ✓ Extracted {len(content.text)} chars | Preview: {preview}...")

            results.append(content)

        except FileNotFoundError:
            logger.error(f"  ✗ Local file not found: {file_name}")
            results.append(ExtractedContent(
                file_name=file_name, file_type="unknown", text="",
                error=f"File not found locally: {file_name}"
            ))
        except Exception as e:
            logger.error(f"  ✗ Unexpected error for '{file_name}': {e}")
            results.append(ExtractedContent(
                file_name=file_name, file_type="unknown", text="", error=str(e)
            ))

    return results


# ─────────────────────────────────────────────
# Summary Reporter
# ─────────────────────────────────────────────

def print_extraction_summary(results: List[ExtractedContent]) -> None:
    """Print a summary table of all extracted files."""
    print("\n" + "=" * 65)
    print(f"{'FILE':<30} {'TYPE':<12} {'CHARS':>6}  {'OCR':>4}  {'VIS':>4}  STATUS")
    print("=" * 65)
    for r in results:
        status = "✗ " + r.error[:20] if r.error else "✓ OK"
        print(
            f"{r.file_name:<30} {r.file_type:<12} "
            f"{len(r.text):>6}  {'Y' if r.used_ocr else 'N':>4}  "
            f"{'Y' if r.used_vision else 'N':>4}  {status}"
        )
    print("=" * 65)
    successful = sum(1 for r in results if not r.error)
    print(f"Total: {len(results)} files | Success: {successful} | Failed: {len(results)-successful}\n")


# ─────────────────────────────────────────────
# Entry point (local testing)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("Phase 2 — Content Extraction Pipeline")
    print("To test locally: place files in ./test_files/ and run this script.")
    print("For real Drive integration, pass drive_service from Phase 1.\n")

    # Example: local testing
    # results = run_extraction_pipeline(
    #     drive_files=SAMPLE_DRIVE_FILES,
    #     use_local_files=True,
    #     local_file_dir="./test_files",
    #     use_vision_for_images=True,
    # )
    # print_extraction_summary(results)
