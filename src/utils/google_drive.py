import json
import logging
from io import BytesIO
import os

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive']
ROOT_DRIVE_ID = os.getenv("DRIVE_ROOT_ID", "1b5S0KHTlGbSYHEppPejgXWu9aUdajvKt")

# Globals to cache folder IDs to avoid multiple API calls
_folder_ids = {
    "KYC": None,
    "Origen": None,
    "Pagos": None,
    "Perfiles": None
}

def get_drive_service():
    """Builds and returns the Drive API service from GOOGLE_CREDENTIALS_JSON environment variable."""
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        logger.error("GOOGLE_CREDENTIALS_JSON environment variable is missing.")
        # Return none instead of crashing hard to allow bot to start without drive
        return None
    try:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        logger.error(f"Failed to authenticate Drive service: {e}")
        return None

def _create_folder(service, parent_id, folder_name):
    """Creates a folder in Drive and returns its ID."""
    file_metadata = {
        'name': folder_name,
        'parents': [parent_id],
        'mimeType': 'application/vnd.google-apps.folder'
    }
    try:
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    except Exception as e:
        logger.error(f"Error creating folder {folder_name}: {e}")
        return None

def init_folders():
    """Ensures the required Multi-folder Vault structure exists under ROOT_DRIVE_ID."""
    service = get_drive_service()
    if not service:
        logger.warning("Drive service not available. Skipper folder init.")
        return

    try:
        # Search for existing folders in root
        query = f"'{ROOT_DRIVE_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])

        existing_folders = {item['name']: item['id'] for item in items}

        for folder_name in _folder_ids.keys():
            if folder_name in existing_folders:
                _folder_ids[folder_name] = existing_folders[folder_name]
                logger.info(f"Directory /{folder_name} already exists (ID: {_folder_ids[folder_name]})")
            else:
                new_id = _create_folder(service, ROOT_DRIVE_ID, folder_name)
                if new_id:
                    _folder_ids[folder_name] = new_id
                    logger.info(f"Directory /{folder_name} created successfully (ID: {new_id})")
    except Exception as e:
        logger.error(f"Error initializing drive folders: {e}")

def upload_image_to_drive(file_stream: BytesIO, folder_name: str, file_name: str, mime_type: str = 'image/jpeg') -> str | None:
    """
    Uploads an image from memory to the specified Drive folder.
    Returns the Drive File ID.
    """
    service = get_drive_service()
    if not service:
        logger.error("Cannot upload: Drive service unavailable.")
        return None

    folder_id = _folder_ids.get(folder_name)
    if not folder_id:
        logger.error(f"Cannot upload: Target folder /{folder_name} ID is not known (run init_folders first).")
        return None

    try:
        # Important: Make sure stream is reset to the beginning
        file_stream.seek(0)
        
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        media = MediaIoBaseUpload(file_stream, mimetype=mime_type, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        logger.info(f"Successfully uploaded {file_name} to /{folder_name} (File ID: {file.get('id')})")
        return file.get('id')
    except Exception as e:
        logger.error(f"Error uploading {file_name} to {folder_name}: {e}")
        return None
