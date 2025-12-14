"""
Google Drive Importer for Mind Monitor Files
Downloads Mind Monitor CSV files from Google Drive and converts them to Muse format
"""

import os
import io
from pathlib import Path
from datetime import datetime
import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# If modifying these scopes, delete the token file
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class GoogleDriveImporter:
    """Import Mind Monitor files from Google Drive."""
    
    def __init__(self, credentials_file='gdrive_credentials.json', token_file='gdrive_token.json'):
        """
        Initialize Google Drive importer.
        
        Args:
            credentials_file: Path to Google Drive API credentials
            token_file: Path to save/load OAuth token
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API."""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    print("ERROR: Google Drive credentials not found!")
                    print("\nTo set up:")
                    print("1. Go to https://console.cloud.google.com/")
                    print("2. Create a new project or select existing")
                    print("3. Enable Google Drive API")
                    print("4. Create OAuth 2.0 credentials (Desktop app)")
                    print("5. Download credentials as 'gdrive_credentials.json'")
                    print("6. Place in this directory")
                    return
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=8080)
            
            # Save credentials
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('drive', 'v3', credentials=creds)
        print("✓ Authenticated with Google Drive")
    
    def list_mind_monitor_files(self, folder_id=None, max_results=50):
        """
        List Mind Monitor CSV files in Google Drive.
        
        Args:
            folder_id: Specific folder ID to search (None = search all)
            max_results: Maximum number of files to return
            
        Returns:
            List of file dictionaries with id, name, modifiedTime
        """
        if not self.service:
            print("Not authenticated")
            return []
        
        try:
            # Build query - only Mind Monitor ZIP files
            query = "name contains 'mindMonitor' and name contains '.zip'"
            if folder_id:
                query += f" and '{folder_id}' in parents"
            
            query += " and trashed=false"
            
            # Search for files
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="files(id, name, modifiedTime, size, mimeType)",
                orderBy="modifiedTime desc"
            ).execute()
            
            files = results.get('files', [])
            
            # Filter to only Mind Monitor ZIP files
            mind_monitor_files = [
                f for f in files 
                if 'mindMonitor' in f['name'] and f['name'].endswith('.zip')
            ]
            
            if not mind_monitor_files:
                print("No Mind Monitor files found")
                return []
            
            print(f"\nFound {len(mind_monitor_files)} Mind Monitor file(s):")
            print("-" * 80)
            for i, file in enumerate(mind_monitor_files, 1):
                size_mb = int(file.get('size', 0)) / 1024 / 1024
                modified = file.get('modifiedTime', 'Unknown')[:10]
                print(f"{i}. {file['name']:<50} {size_mb:>6.2f} MB  {modified}")
            
            return mind_monitor_files
        
        except Exception as e:
            print(f"Error listing files: {e}")
            return []
    
    def download_file(self, file_id, output_path):
        """
        Download file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            output_path: Local path to save file
            
        Returns:
            Path to downloaded file or None
        """
        if not self.service:
            print("Not authenticated")
            return None
        
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            fh = io.FileIO(output_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            print(f"Downloading {output_path.name}...", end=" ")
            
            while done is False:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"\r{progress}%", end="", flush=True)
            
            print("\r✓ Downloaded")
            return output_path
        
        except Exception as e:
            print(f"\n✗ Error downloading: {e}")
            return None
    
    def convert_mind_monitor_to_muse(self, csv_path, output_path=None):
        """
        Convert Mind Monitor CSV format to Muse recorder format.
        
        Args:
            csv_path: Path to Mind Monitor CSV file
            output_path: Optional output path (default: same dir, renamed)
            
        Returns:
            Path to converted file
        """
        print(f"\nConverting: {Path(csv_path).name}")
        
        try:
            # Read Mind Monitor CSV
            df = pd.read_csv(csv_path)
            
            print(f"✓ Loaded {len(df)} samples")
            
            # Mind Monitor column mapping
            # Typical columns: TimeStamp, Delta_TP9, Theta_TP9, Alpha_TP9, etc.
            # or: timestamp, TP9, AF7, AF8, TP10, etc.
            
            # Create Muse format DataFrame
            muse_df = pd.DataFrame()
            
            # Determine timestamp column
            time_col = None
            for col in ['TimeStamp', 'timestamp', 'Timestamp', 'time']:
                if col in df.columns:
                    time_col = col
                    break
            
            if time_col:
                # Parse timestamp
                try:
                    timestamps = pd.to_datetime(df[time_col])
                    start_time = timestamps.iloc[0]
                    
                    # Calculate elapsed time
                    muse_df['elapsed_time'] = (timestamps - start_time).dt.total_seconds()
                    muse_df['timestamp_unix'] = timestamps.astype(int) / 10**9
                    muse_df['timestamp_iso'] = timestamps.astype(str)
                except:
                    # Assume already in seconds
                    muse_df['elapsed_time'] = df[time_col]
                    start_time = datetime.now()
                    muse_df['timestamp_unix'] = start_time.timestamp() + df[time_col]
                    muse_df['timestamp_iso'] = pd.to_datetime(muse_df['timestamp_unix'], unit='s').astype(str)
            else:
                # Generate timestamps
                print("  No timestamp column, generating from sample count...")
                muse_df['elapsed_time'] = pd.Series(range(len(df))) / 256.0
                start_time = datetime.now()
                muse_df['timestamp_unix'] = start_time.timestamp() + muse_df['elapsed_time']
                muse_df['timestamp_iso'] = pd.to_datetime(muse_df['timestamp_unix'], unit='s').astype(str)
            
            # Map EEG channels
            eeg_mapping = {
                'TP9': 'eeg_tp9',
                'AF7': 'eeg_af7',
                'AF8': 'eeg_af8',
                'TP10': 'eeg_tp10',
                'RAW_TP9': 'eeg_tp9',
                'RAW_AF7': 'eeg_af7',
                'RAW_AF8': 'eeg_af8',
                'RAW_TP10': 'eeg_tp10'
            }
            
            for mind_col, muse_col in eeg_mapping.items():
                if mind_col in df.columns:
                    muse_df[muse_col] = df[mind_col]
            
            # Map PPG if available
            ppg_cols = [col for col in df.columns if 'ppg' in col.lower() or 'heart' in col.lower()]
            if ppg_cols:
                muse_df['ppg_avg'] = df[ppg_cols[0]]
            else:
                muse_df['ppg_avg'] = 0
            
            # Map gyroscope
            gyro_mapping = {
                'Gyro_X': 'gyro_x', 'gyro_x': 'gyro_x',
                'Gyro_Y': 'gyro_y', 'gyro_y': 'gyro_y',
                'Gyro_Z': 'gyro_z', 'gyro_z': 'gyro_z'
            }
            
            for mind_col, muse_col in gyro_mapping.items():
                if mind_col in df.columns:
                    muse_df[muse_col] = df[mind_col]
            
            # Fill missing gyro with zeros
            for col in ['gyro_x', 'gyro_y', 'gyro_z']:
                if col not in muse_df.columns:
                    muse_df[col] = 0.0
            
            # Map accelerometer
            acc_mapping = {
                'Acc_X': 'acc_x', 'acc_x': 'acc_x',
                'Acc_Y': 'acc_y', 'acc_y': 'acc_y',
                'Acc_Z': 'acc_z', 'acc_z': 'acc_z'
            }
            
            for mind_col, muse_col in acc_mapping.items():
                if mind_col in df.columns:
                    muse_df[muse_col] = df[mind_col]
            
            # Fill missing acc with zeros
            for col in ['acc_x', 'acc_y', 'acc_z']:
                if col not in muse_df.columns:
                    muse_df[col] = 0.0
            
            # Ensure all EEG channels exist
            for col in ['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']:
                if col not in muse_df.columns:
                    muse_df[col] = 0.0
            
            # Determine output path
            if output_path is None:
                csv_path = Path(csv_path)
                # Extract date from filename or use current
                date_str = datetime.now().strftime("%Y-%m-%d")
                date_folder = Path("recordings") / date_str
                date_folder.mkdir(parents=True, exist_ok=True)
                
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = date_folder / f"muse_mindmonitor_{timestamp_str}.csv"
            
            # Save
            muse_df.to_csv(output_path, index=False)
            print(f"✓ Converted to Muse format: {output_path}")
            
            # Create metadata
            metadata = {
                'source': 'Mind Monitor (Google Drive)',
                'original_file': str(csv_path),
                'start_time_unix': float(muse_df['timestamp_unix'].iloc[0]),
                'start_time_iso': muse_df['timestamp_iso'].iloc[0],
                'duration_seconds': float(muse_df['elapsed_time'].max()),
                'sample_count': len(muse_df),
                'device': 'Muse (Mind Monitor)',
                'sampling_rate_hz': len(muse_df) / muse_df['elapsed_time'].max() if muse_df['elapsed_time'].max() > 0 else 256
            }
            
            metadata_file = Path(output_path).with_suffix('.metadata.json')
            import json
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✓ Created metadata: {metadata_file}")
            
            return output_path
        
        except Exception as e:
            print(f"✗ Error converting file: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def import_from_drive(self, file_id=None, search_query=None):
        """
        Import Mind Monitor files from Google Drive.
        
        Args:
            file_id: Specific file ID to download
            search_query: Search for files (if file_id not provided)
        """
        if file_id:
            # Download specific file
            temp_path = Path("temp_mindmonitor.csv")
            downloaded = self.download_file(file_id, temp_path)
            
            if downloaded:
                converted = self.convert_mind_monitor_to_muse(downloaded)
                temp_path.unlink()  # Delete temp file
                return converted
        else:
            # List files and automatically grab latest
            files = self.list_mind_monitor_files()
            
            if not files:
                return None
            
            # Automatically select latest file (first in list, sorted by modifiedTime desc)
            print(f"\n✓ Auto-selecting latest: {files[0]['name']}")
            file = files[0]
            temp_path = Path(f"temp_{file['name']}")
            downloaded = self.download_file(file['id'], temp_path)
            if downloaded:
                converted = self.convert_mind_monitor_to_muse(downloaded)
                temp_path.unlink()
                return converted


def main():
    """Main function."""
    print("="*60)
    print("GOOGLE DRIVE MIND MONITOR IMPORTER")
    print("="*60)
    
    importer = GoogleDriveImporter()
    
    if importer.service:
        importer.import_from_drive()
    else:
        print("\n✗ Setup required - see instructions above")


if __name__ == "__main__":
    main()
