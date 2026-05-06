import os
import re
import io
from urllib.parse import urlparse, parse_qs
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Mime types for Google Workspace documents to export formats
EXPORT_MIME_TYPES = {
    'application/vnd.google-apps.document': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
    'application/vnd.google-apps.spreadsheet': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx'),
    'application/vnd.google-apps.presentation': ('application/pdf', '.pdf'),
}

class GoogleDriveFetcher:
    def __init__(self, download_dir='./downloads'):
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        self.service = self._authenticate()

    def _authenticate(self):
        """Authenticates with Google Drive API."""
        creds = None
        
        # Check for service account first
        if os.path.exists('service_account.json'):
            print("Authenticating with service_account.json...")
            creds = service_account.Credentials.from_service_account_file(
                'service_account.json', scopes=SCOPES)
            return build('drive', 'v3', credentials=creds)

        # Then check for OAuth2 credentials
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif os.path.exists('credentials.json'):
                print("Authenticating with credentials.json...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            else:
                raise FileNotFoundError("Authentication file not found. Please provide 'service_account.json' or 'credentials.json'.")
                
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        return build('drive', 'v3', credentials=creds)

    def parse_link(self, url):
        """
        Parses a Google Drive URL and returns the ID and whether it's explicitly a folder.
        """
        # https://drive.google.com/file/d/FILE_ID/view
        file_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
        if file_match:
            return file_match.group(1), False

        # https://drive.google.com/drive/folders/FOLDER_ID
        folder_match = re.search(r'/folders/([a-zA-Z0-9_-]+)', url)
        if folder_match:
            return folder_match.group(1), True

        # https://drive.google.com/open?id=ID
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if 'id' in query_params:
            return query_params['id'][0], None

        raise ValueError(f"Could not parse Google Drive URL: {url}")

    def fetch(self, url):
        """Fetches a file or folder from a Google Drive URL."""
        item_id, is_folder_hint = self.parse_link(url)
        print(f"Parsed ID: {item_id}")
        self._process_item(item_id)

    def _process_item(self, item_id, path=''):
        """Processes an item by its ID, handles files and folders."""
        try:
            # supportsAllDrives allows access to shared drives
            file_meta = self.service.files().get(
                fileId=item_id,
                fields='id, name, mimeType, size, modifiedTime',
                supportsAllDrives=True
            ).execute()
        except Exception as e:
            print(f"Failed to fetch metadata for ID {item_id}: {e}")
            return

        name = file_meta.get('name')
        mime_type = file_meta.get('mimeType')
        print(f"Found item: {name} ({mime_type})")

        if mime_type == 'application/vnd.google-apps.folder':
            folder_path = os.path.join(path, name)
            self._download_folder(item_id, folder_path)
        else:
            self._download_file(file_meta, path)

    def _download_file(self, file_meta, path=''):
        """Downloads a single file."""
        file_id = file_meta['id']
        name = file_meta['name']
        mime_type = file_meta['mimeType']
        
        target_dir = os.path.join(self.download_dir, path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # Handle Workspace files
        request = None
        if mime_type in EXPORT_MIME_TYPES:
            export_mime, ext = EXPORT_MIME_TYPES[mime_type]
            name += ext
            request = self.service.files().export_media(fileId=file_id, mimeType=export_mime)
        else:
            request = self.service.files().get_media(fileId=file_id, supportsAllDrives=True)

        file_path = os.path.join(target_dir, name)
        
        print(f"Downloading {name}...")
        try:
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                # print(f"Download {int(status.progress() * 100)}%.")

            with open(file_path, 'wb') as f:
                f.write(fh.getvalue())
            print(f"Successfully saved to {file_path}")
        except Exception as e:
            print(f"Failed to download {name}: {e}")

    def _download_folder(self, folder_id, path=''):
        """Recursively lists and downloads items in a folder."""
        print(f"Entering folder: {path}")
        page_token = None
        while True:
            try:
                response = self.service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, size, modifiedTime)',
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                
                for file_meta in response.get('files', []):
                    mime_type = file_meta.get('mimeType')
                    name = file_meta.get('name')
                    if mime_type == 'application/vnd.google-apps.folder':
                        new_path = os.path.join(path, name)
                        self._download_folder(file_meta['id'], new_path)
                    else:
                        self._download_file(file_meta, path)
                        
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
            except Exception as e:
                print(f"Error fetching folder contents for ID {folder_id}: {e}")
                break

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch Google Drive Files and Folders.")
    parser.add_argument("url", help="Google Drive Link (File, Folder, or Shared Link)")
    parser.add_argument("--out", default="./downloads", help="Output directory")
    args = parser.parse_args()

    try:
        fetcher = GoogleDriveFetcher(download_dir=args.out)
        fetcher.fetch(args.url)
    except Exception as e:
        print(f"Error: {e}")
