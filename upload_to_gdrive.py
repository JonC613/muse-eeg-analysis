#!/usr/bin/env python3
"""
Upload research files to Google Drive
"""
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    """Authenticate and return Google Drive service"""
    creds = None
    
    # Load existing token (using from_authorized_user_file like gdrive_mindmonitor_importer.py)
    if os.path.exists('gdrive_token.json'):
        creds = Credentials.from_authorized_user_file('gdrive_token.json', SCOPES)
    
    # Refresh if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'gdrive_credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials
        with open('gdrive_token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)

def create_folder(service, folder_name, parent_id=None):
    """Create a folder in Google Drive"""
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    folder = service.files().create(body=file_metadata, fields='id, name').execute()
    print(f"✓ Created folder: {folder.get('name')} (ID: {folder.get('id')})")
    return folder.get('id')

def upload_file(service, file_path, folder_id=None):
    """Upload a file to Google Drive"""
    file_name = os.path.basename(file_path)
    file_metadata = {'name': file_name}
    
    if folder_id:
        file_metadata['parents'] = [folder_id]
    
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink'
    ).execute()
    
    print(f"✓ Uploaded: {file.get('name')}")
    print(f"  Link: {file.get('webViewLink')}")
    return file.get('id')

def main():
    print("=" * 60)
    print("GOOGLE DRIVE RESEARCH UPLOAD")
    print("=" * 60)
    
    # Authenticate
    print("\nAuthenticating with Google Drive...")
    service = get_drive_service()
    print("✓ Successfully authenticated!")
    
    # Create folder with date
    folder_name = "Cannabis EEG Study - 2025-12-18"
    print(f"\nCreating folder: {folder_name}")
    folder_id = create_folder(service, folder_name)
    
    # Upload LLM analysis document
    print("\nUploading research files...")
    llm_file = "research/cannabis-study-2025-12-18/LLM_ANALYSIS_INPUT.md"
    
    if os.path.exists(llm_file):
        upload_file(service, llm_file, folder_id)
    else:
        print(f"❌ File not found: {llm_file}")
    
    print("\n" + "=" * 60)
    print("Upload complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
