"""
Manual Mind Monitor File Importer
Processes Mind Monitor CSV files from recordings/manual/ folder
Converts to Muse format and organizes by date
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import pandas as pd
import json


class ManualMindMonitorImporter:
    """Import Mind Monitor files from local recordings/manual/ folder."""
    
    def __init__(self, manual_folder='recordings/manual'):
        """
        Initialize manual importer.
        
        Args:
            manual_folder: Folder to watch for Mind Monitor files
        """
        self.manual_folder = Path(manual_folder)
        self.manual_folder.mkdir(parents=True, exist_ok=True)
        
    def convert_mind_monitor_to_muse(self, csv_path, target_date=None):
        """
        Convert Mind Monitor CSV format to Muse recorder format.
        
        Args:
            csv_path: Path to Mind Monitor CSV file
            target_date: Optional date for organization (YYYY-MM-DD)
                        If None, extracts from file or uses current date
            
        Returns:
            Path to converted file
        """
        print(f"\nConverting: {Path(csv_path).name}")
        
        try:
            # Read Mind Monitor CSV
            df = pd.read_csv(csv_path)
            
            print(f"✓ Loaded {len(df)} samples")
            
            # Create Muse format DataFrame
            muse_df = pd.DataFrame()
            
            # Determine timestamp column
            time_col = None
            for col in ['TimeStamp', 'timestamp', 'Timestamp', 'time', 'Time']:
                if col in df.columns:
                    time_col = col
                    break
            
            # Parse timestamps and determine date
            if time_col:
                try:
                    timestamps = pd.to_datetime(df[time_col])
                    start_time = timestamps.iloc[0]
                    
                    # Extract date from timestamp if not provided
                    if target_date is None:
                        target_date = start_time.strftime("%Y-%m-%d")
                    
                    # Calculate elapsed time
                    muse_df['elapsed_time'] = (timestamps - start_time).dt.total_seconds()
                    muse_df['timestamp_unix'] = timestamps.astype(int) / 10**9
                    muse_df['timestamp_iso'] = timestamps.astype(str)
                    
                except Exception as e:
                    print(f"  Warning: Could not parse timestamps: {e}")
                    # Assume already in seconds
                    muse_df['elapsed_time'] = df[time_col]
                    start_time = datetime.now()
                    muse_df['timestamp_unix'] = start_time.timestamp() + df[time_col]
                    muse_df['timestamp_iso'] = pd.to_datetime(muse_df['timestamp_unix'], unit='s').astype(str)
                    
                    if target_date is None:
                        target_date = start_time.strftime("%Y-%m-%d")
            else:
                # No timestamp column - generate from sample count
                print("  No timestamp column found, generating from sample count...")
                muse_df['elapsed_time'] = pd.Series(range(len(df))) / 256.0
                start_time = datetime.now()
                muse_df['timestamp_unix'] = start_time.timestamp() + muse_df['elapsed_time']
                muse_df['timestamp_iso'] = pd.to_datetime(muse_df['timestamp_unix'], unit='s').astype(str)
                
                if target_date is None:
                    target_date = start_time.strftime("%Y-%m-%d")
            
            # Map EEG channels
            eeg_mapping = {
                'TP9': 'eeg_tp9',
                'AF7': 'eeg_af7',
                'AF8': 'eeg_af8',
                'TP10': 'eeg_tp10',
                'RAW_TP9': 'eeg_tp9',
                'RAW_AF7': 'eeg_af7',
                'RAW_AF8': 'eeg_af8',
                'RAW_TP10': 'eeg_tp10',
                'Left_Ear': 'eeg_tp9',
                'Left_Forehead': 'eeg_af7',
                'Right_Forehead': 'eeg_af8',
                'Right_Ear': 'eeg_tp10'
            }
            
            for mind_col, muse_col in eeg_mapping.items():
                if mind_col in df.columns:
                    muse_df[muse_col] = df[mind_col]
                    print(f"  Mapped {mind_col} → {muse_col}")
            
            # Ensure all EEG channels exist
            for col in ['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']:
                if col not in muse_df.columns:
                    muse_df[col] = 0.0
            
            # Map PPG if available
            ppg_cols = [col for col in df.columns if 'ppg' in col.lower() or 'pulse' in col.lower()]
            if ppg_cols:
                muse_df['ppg_avg'] = df[ppg_cols[0]]
                print(f"  Mapped {ppg_cols[0]} → ppg_avg")
            else:
                muse_df['ppg_avg'] = 0
            
            # Map gyroscope
            gyro_mapping = {
                'Gyro_X': 'gyro_x', 'gyro_x': 'gyro_x', 'GyroX': 'gyro_x',
                'Gyro_Y': 'gyro_y', 'gyro_y': 'gyro_y', 'GyroY': 'gyro_y',
                'Gyro_Z': 'gyro_z', 'gyro_z': 'gyro_z', 'GyroZ': 'gyro_z'
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
                'Acc_X': 'acc_x', 'acc_x': 'acc_x', 'AccX': 'acc_x',
                'Acc_Y': 'acc_y', 'acc_y': 'acc_y', 'AccY': 'acc_y',
                'Acc_Z': 'acc_z', 'acc_z': 'acc_z', 'AccZ': 'acc_z'
            }
            
            for mind_col, muse_col in acc_mapping.items():
                if mind_col in df.columns:
                    muse_df[muse_col] = df[mind_col]
            
            # Fill missing acc with zeros
            for col in ['acc_x', 'acc_y', 'acc_z']:
                if col not in muse_df.columns:
                    muse_df[col] = 0.0
            
            # Create output path in date folder
            date_folder = Path("recordings") / target_date
            date_folder.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = Path(csv_path).stem
            output_path = date_folder / f"muse_mindmonitor_{original_name}_{timestamp_str}.csv"
            
            # Save converted file
            muse_df.to_csv(output_path, index=False)
            print(f"✓ Converted to Muse format: {output_path}")
            
            # Check data quality
            total_samples = len(muse_df)
            valid_eeg_samples = muse_df['eeg_af7'].notna().sum()
            data_quality = (valid_eeg_samples / total_samples) * 100
            
            print(f"  Data quality: {valid_eeg_samples}/{total_samples} samples ({data_quality:.1f}% valid EEG)")
            
            if data_quality < 50:
                print(f"  ⚠ WARNING: Low data quality ({data_quality:.1f}% valid)")
                print(f"     Mind Monitor may have been in marker/timestamp mode")
                print(f"     This file may not work well for detailed analysis")
            
            # Create metadata
            metadata = {
                'source': 'Mind Monitor (Manual Import)',
                'original_file': str(csv_path),
                'original_filename': Path(csv_path).name,
                'import_date': datetime.now().isoformat(),
                'session_date': target_date,
                'start_time_unix': float(muse_df['timestamp_unix'].iloc[0]),
                'start_time_iso': muse_df['timestamp_iso'].iloc[0],
                'duration_seconds': float(muse_df['elapsed_time'].max()),
                'sample_count': len(muse_df),
                'device': 'Muse (Mind Monitor)',
                'sampling_rate_hz': len(muse_df) / muse_df['elapsed_time'].max() if muse_df['elapsed_time'].max() > 0 else 256,
                'columns_found': list(df.columns),
                'has_ppg': bool(ppg_cols),
                'data_quality': {
                    'total_samples': int(total_samples),
                    'valid_eeg_samples': int(valid_eeg_samples),
                    'percentage_valid': float(data_quality),
                    'warning': 'Low data quality' if data_quality < 50 else 'Good'
                }
            }
            
            metadata_file = Path(output_path).with_suffix('.metadata.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✓ Created metadata: {metadata_file}")
            
            return output_path
        
        except Exception as e:
            print(f"✗ Error converting file: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def process_manual_files(self, move_originals=True):
        """
        Process all Mind Monitor files in recordings/manual/ folder.
        
        Args:
            move_originals: If True, move original files to archive after conversion
            
        Returns:
            List of converted file paths
        """
        print("="*70)
        print("MANUAL MIND MONITOR FILE IMPORTER")
        print("="*70)
        
        # Find all CSV files in manual folder
        csv_files = list(self.manual_folder.glob('*.csv'))
        
        if not csv_files:
            print(f"\n✗ No CSV files found in {self.manual_folder}")
            print("\nPlace Mind Monitor CSV files in this folder:")
            print(f"  {self.manual_folder.absolute()}")
            return []
        
        print(f"\nFound {len(csv_files)} file(s) to process:")
        for i, file in enumerate(csv_files, 1):
            size_mb = file.stat().st_size / 1024 / 1024
            modified = datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            print(f"  {i}. {file.name:<50} {size_mb:>6.2f} MB  {modified}")
        
        converted_files = []
        
        # Process each file
        for csv_file in csv_files:
            print(f"\n{'='*70}")
            
            # Convert file
            converted = self.convert_mind_monitor_to_muse(csv_file)
            
            if converted:
                converted_files.append(converted)
                
                # Move or archive original
                if move_originals:
                    archive_folder = self.manual_folder / 'processed'
                    archive_folder.mkdir(exist_ok=True)
                    
                    archive_path = archive_folder / csv_file.name
                    shutil.move(str(csv_file), str(archive_path))
                    print(f"✓ Moved original to: {archive_path}")
        
        print(f"\n{'='*70}")
        print(f"IMPORT COMPLETE: {len(converted_files)}/{len(csv_files)} files converted")
        print("="*70)
        
        if converted_files:
            print("\nConverted files:")
            for file in converted_files:
                print(f"  ✓ {file}")
        
        return converted_files
    
    def list_manual_files(self):
        """List files waiting in manual folder."""
        csv_files = list(self.manual_folder.glob('*.csv'))
        
        if not csv_files:
            print(f"No files in {self.manual_folder}")
            return []
        
        print(f"\nFiles in {self.manual_folder}:")
        print("-" * 70)
        for i, file in enumerate(csv_files, 1):
            size_mb = file.stat().st_size / 1024 / 1024
            modified = datetime.fromtimestamp(file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            print(f"{i}. {file.name:<50} {size_mb:>6.2f} MB  {modified}")
        
        return csv_files


def main():
    """Main function."""
    importer = ManualMindMonitorImporter()
    
    # Check if there are files to process
    files = importer.list_manual_files()
    
    if files:
        print("\n" + "="*70)
        print("Process these files? (y/n/list): ", end="")
        choice = input().strip().lower()
        
        if choice == 'y' or choice == 'yes':
            importer.process_manual_files(move_originals=True)
        elif choice == 'list':
            # Show first few lines of each file to help identify
            for file in files[:3]:  # Limit to first 3 files
                print(f"\n--- {file.name} (first 5 rows) ---")
                try:
                    df = pd.read_csv(file, nrows=5)
                    print(df.to_string())
                except:
                    print("Could not read file")
        else:
            print("Cancelled")
    else:
        print(f"\nTo use this tool:")
        print(f"1. Copy Mind Monitor CSV files to: {importer.manual_folder.absolute()}")
        print(f"2. Run: python import_mindmonitor_manual.py")
        print(f"3. Files will be converted and organized by date")
        print(f"4. Originals moved to: {importer.manual_folder.absolute()}/processed/")


if __name__ == "__main__":
    main()
