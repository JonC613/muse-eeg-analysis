# Google Drive Mind Monitor Importer Setup

Import Mind Monitor CSV files directly from Google Drive into Muse format.

## Setup Instructions

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name it "Muse Mind Monitor Importer"
4. Click "Create"

### 2. Enable Google Drive API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click on it and press "Enable"

### 3. Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure OAuth consent screen:
   - User Type: External
   - App name: Muse Mind Monitor Importer
   - User support email: your email
   - Developer contact: your email
   - Scopes: Add `../auth/drive.readonly`
   - Test users: Add your Google account email
   - Save and Continue
4. Back to Credentials:
   - Application type: Desktop app
   - Name: Mind Monitor Importer
   - Click "Create"
5. Download the JSON file
6. Rename it to `gdrive_credentials.json`
7. Place it in `c:\dev\musepython\`

### 4. Install Dependencies

```powershell
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

Or update from requirements:
```powershell
pip install -r requirements.txt
```

### 5. First Run

```powershell
python gdrive_mindmonitor_importer.py
```

- Browser will open for Google authentication
- Select your Google account
- Click "Continue" (it may show "unverified app" warning)
- Click "Continue" again to allow access
- The tool will save a token for future use

## Usage

### Interactive Mode

```powershell
python gdrive_mindmonitor_importer.py
```

- Lists all Mind Monitor files in your Google Drive
- Select file number to import
- Or type 'all' to import all files

### Programmatic Usage

```python
from gdrive_mindmonitor_importer import GoogleDriveImporter

# Initialize
importer = GoogleDriveImporter()

# List files
files = importer.list_mind_monitor_files()

# Download specific file
importer.download_file(file_id='YOUR_FILE_ID', output_path='temp.csv')

# Convert to Muse format
importer.convert_mind_monitor_to_muse('temp.csv')

# Or do it all at once
importer.import_from_drive(file_id='YOUR_FILE_ID')
```

## Mind Monitor Format Compatibility

The importer automatically detects and converts these Mind Monitor column formats:

### Raw EEG Data
- `TP9`, `AF7`, `AF8`, `TP10` → `eeg_tp9`, `eeg_af7`, `eeg_af8`, `eeg_tp10`
- `RAW_TP9`, `RAW_AF7`, etc. → Same mapping

### Timestamps
- `TimeStamp`, `timestamp`, `Timestamp`, `time` → `timestamp_unix`, `timestamp_iso`, `elapsed_time`

### PPG Heart Rate
- Any column with `ppg` or `heart` → `ppg_avg`

### Motion Sensors
- `Gyro_X`, `Gyro_Y`, `Gyro_Z` → `gyro_x`, `gyro_y`, `gyro_z`
- `Acc_X`, `Acc_Y`, `Acc_Z` → `acc_x`, `acc_y`, `acc_z`

## Output

Converted files are saved to:
```
recordings/YYYY-MM-DD/muse_mindmonitor_YYYYMMDD_HHMMSS.csv
recordings/YYYY-MM-DD/muse_mindmonitor_YYYYMMDD_HHMMSS.metadata.json
```

Compatible with all Muse analysis tools:
- `muse_ai_analyzer.py`
- `muse_visualizer.py`
- `muse_compare_sessions.py`
- `ppg_to_bpm.py`

## Troubleshooting

### "No files found"
- Check your Google Drive for CSV files
- Mind Monitor files usually contain "muse", "mind", or end in ".csv"
- Files must not be in trash

### "Authentication failed"
- Delete `gdrive_token.json` and re-authenticate
- Verify `gdrive_credentials.json` is correct

### "API not enabled"
- Enable Google Drive API in Cloud Console
- Wait a few minutes for it to propagate

### "Access denied"
- Add your email as test user in OAuth consent screen
- Publishing the app (not required for personal use)

## Security Notes

- `gdrive_credentials.json` - OAuth client credentials (safe to commit if Desktop app)
- `gdrive_token.json` - Your personal access token (DO NOT COMMIT)
- Both are already in `.gitignore`

## Mind Monitor App

Mind Monitor is an iOS/Android app that records Muse headband data:
- Available on App Store and Google Play
- Can sync to Google Drive automatically
- Records raw EEG, FFT bands, accelerometer, gyroscope, PPG
- Export format: CSV files

This importer makes those files compatible with your Muse analysis pipeline.
