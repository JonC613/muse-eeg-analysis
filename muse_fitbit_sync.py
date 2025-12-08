"""
Sync Fitbit and Muse Data
Match Fitbit heart rate and activity data with Muse EEG recordings using timestamps
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from fitbit_interface import FitbitInterface, FitbitAuth


class MuseFitbitSync:
    """Synchronize Muse and Fitbit data based on timestamps."""
    
    def __init__(self):
        """Initialize the sync tool."""
        # Load Fitbit credentials
        self.fitbit = self._init_fitbit()
    
    def _init_fitbit(self):
        """Initialize Fitbit interface."""
        cred_file = Path('fitbit_credentials.json')
        
        if not cred_file.exists():
            print("Fitbit not set up. Run: python fitbit_interface.py")
            return None
        
        with open(cred_file, 'r') as f:
            creds = json.load(f)
        
        auth = FitbitAuth(creds['client_id'], creds['client_secret'])
        return FitbitInterface(auth)
    
    def sync_with_muse_session(self, muse_csv_path, output_path=None):
        """
        Sync Fitbit data with a Muse recording session.
        
        Args:
            muse_csv_path: Path to Muse CSV file
            output_path: Optional path to save synced data (default: same folder as Muse file)
            
        Returns:
            DataFrame with combined Muse and Fitbit data
        """
        if not self.fitbit:
            print("Fitbit not initialized")
            return None
        
        print("\n" + "="*60)
        print("MUSE + FITBIT DATA SYNC")
        print("="*60)
        
        # Load Muse data
        muse_csv = Path(muse_csv_path)
        print(f"\nLoading Muse data: {muse_csv.name}")
        muse_df = pd.read_csv(muse_csv)
        
        # Check for metadata file
        metadata_file = muse_csv.with_suffix('.metadata.json')
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                start_time_unix = metadata['start_time_unix']
                print(f"✓ Session started: {metadata['start_time_iso']}")
        else:
            # Try to get from first timestamp
            if 'timestamp_unix' in muse_df.columns:
                start_time_unix = muse_df['timestamp_unix'].iloc[0]
            else:
                print("✗ Cannot determine session start time")
                return None
        
        # Calculate session time range
        start_dt = datetime.fromtimestamp(start_time_unix)
        if 'elapsed_time' in muse_df.columns:
            duration = muse_df['elapsed_time'].max()
        elif 'timestamp' in muse_df.columns:
            duration = muse_df['timestamp'].max()
        else:
            duration = len(muse_df) / 256  # Assume 256 Hz sampling
        
        end_dt = start_dt + timedelta(seconds=duration)
        
        print(f"✓ Duration: {duration:.1f} seconds")
        print(f"✓ Time range: {start_dt.strftime('%H:%M:%S')} to {end_dt.strftime('%H:%M:%S')}")
        
        # Get Fitbit heart rate data for the session date
        session_date = start_dt.strftime("%Y-%m-%d")
        print(f"\nFetching Fitbit heart rate data for {session_date}...")
        
        fitbit_hr = self.fitbit.get_heart_rate_intraday(session_date, detail_level='1min')
        
        if fitbit_hr is None or fitbit_hr.empty:
            print("✗ No Fitbit heart rate data found for this date")
            return None
        
        print(f"✓ Loaded {len(fitbit_hr)} heart rate samples")
        
        # Filter Fitbit data to session time range
        fitbit_hr_filtered = fitbit_hr[
            (fitbit_hr['timestamp_unix'] >= start_time_unix) &
            (fitbit_hr['timestamp_unix'] <= start_time_unix + duration)
        ].copy()
        
        if fitbit_hr_filtered.empty:
            print("✗ No Fitbit data overlaps with Muse session time")
            print(f"   Muse session: {start_dt.strftime('%H:%M:%S')} - {end_dt.strftime('%H:%M:%S')}")
            print(f"   Fitbit data range: {datetime.fromtimestamp(fitbit_hr['timestamp_unix'].min()).strftime('%H:%M:%S')} - {datetime.fromtimestamp(fitbit_hr['timestamp_unix'].max()).strftime('%H:%M:%S')}")
            return None
        
        print(f"✓ Found {len(fitbit_hr_filtered)} Fitbit samples during Muse session")
        
        # Merge Muse and Fitbit data
        print("\nMerging data...")
        
        # Use timestamp_unix for merging
        if 'timestamp_unix' in muse_df.columns:
            merged_df = pd.merge_asof(
                muse_df.sort_values('timestamp_unix'),
                fitbit_hr_filtered[['timestamp_unix', 'heart_rate']].sort_values('timestamp_unix'),
                on='timestamp_unix',
                direction='nearest',
                tolerance=30.0  # Match within 30 seconds
            )
        else:
            print("✗ Muse data doesn't have timestamp_unix column")
            return None
        
        print(f"✓ Merged {len(merged_df)} samples")
        print(f"✓ Heart rate data matched for {merged_df['heart_rate'].notna().sum()} samples")
        
        # Save merged data
        if output_path is None:
            output_path = muse_csv.parent / f"{muse_csv.stem}_with_fitbit.csv"
        else:
            output_path = Path(output_path)
        
        merged_df.to_csv(output_path, index=False)
        print(f"\n✓ Saved merged data to: {output_path}")
        
        # Create summary
        self._create_summary(merged_df, muse_csv.parent / f"{muse_csv.stem}_fitbit_summary.txt")
        
        # Visualize
        self._visualize_sync(merged_df, muse_csv.parent / f"{muse_csv.stem}_fitbit_sync.png")
        
        return merged_df
    
    def _create_summary(self, df, output_path):
        """Create a text summary of the synced data."""
        summary = []
        summary.append("="*60)
        summary.append("MUSE + FITBIT SYNC SUMMARY")
        summary.append("="*60)
        summary.append("")
        
        # Basic stats
        summary.append(f"Total samples: {len(df)}")
        summary.append(f"Samples with heart rate: {df['heart_rate'].notna().sum()}")
        summary.append("")
        
        # Heart rate stats
        if df['heart_rate'].notna().any():
            summary.append("Heart Rate Statistics:")
            summary.append(f"  Mean: {df['heart_rate'].mean():.1f} bpm")
            summary.append(f"  Min: {df['heart_rate'].min():.0f} bpm")
            summary.append(f"  Max: {df['heart_rate'].max():.0f} bpm")
            summary.append(f"  Std Dev: {df['heart_rate'].std():.1f} bpm")
            summary.append("")
        
        # EEG channels average
        eeg_channels = ['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']
        if all(ch in df.columns for ch in eeg_channels):
            summary.append("EEG Statistics:")
            for ch in eeg_channels:
                summary.append(f"  {ch}: mean={df[ch].mean():.2f}, std={df[ch].std():.2f}")
            summary.append("")
        
        # Motion stats
        if 'gyro_x' in df.columns:
            import numpy as np
            movement = np.sqrt(df['gyro_x']**2 + df['gyro_y']**2 + df['gyro_z']**2)
            summary.append("Movement Statistics:")
            summary.append(f"  Mean movement: {movement.mean():.2f}°/s")
            summary.append(f"  Still time: {(movement < 10).sum() / len(movement) * 100:.1f}%")
            summary.append("")
        
        summary_text = "\n".join(summary)
        
        with open(output_path, 'w') as f:
            f.write(summary_text)
        
        print(f"✓ Saved summary to: {output_path}")
        print("\n" + summary_text)
    
    def _visualize_sync(self, df, output_path):
        """Create visualization of synced Muse and Fitbit data."""
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        fig.suptitle('Muse EEG + Fitbit Heart Rate Sync', fontsize=16, fontweight='bold')
        
        # Determine time column
        if 'elapsed_time' in df.columns:
            time_col = 'elapsed_time'
            time_label = 'Elapsed Time (seconds)'
        elif 'timestamp' in df.columns:
            time_col = 'timestamp'
            time_label = 'Time (seconds)'
        else:
            time_col = None
        
        if time_col:
            # Plot 1: EEG channels
            ax1 = axes[0]
            eeg_channels = ['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']
            for ch in eeg_channels:
                if ch in df.columns:
                    ax1.plot(df[time_col], df[ch], label=ch, alpha=0.7, linewidth=0.5)
            ax1.set_ylabel('EEG (μV)')
            ax1.set_title('EEG Channels')
            ax1.legend(loc='upper right')
            ax1.grid(True, alpha=0.3)
            
            # Plot 2: Heart Rate
            ax2 = axes[1]
            if 'heart_rate' in df.columns:
                ax2.plot(df[time_col], df['heart_rate'], 'r-', linewidth=2, label='Heart Rate')
                ax2.scatter(df[time_col][df['heart_rate'].notna()], 
                           df['heart_rate'][df['heart_rate'].notna()], 
                           c='red', s=20, alpha=0.6, label='Fitbit Samples')
            ax2.set_ylabel('Heart Rate (bpm)')
            ax2.set_title('Fitbit Heart Rate')
            ax2.legend(loc='upper right')
            ax2.grid(True, alpha=0.3)
            
            # Plot 3: Movement
            ax3 = axes[2]
            if all(col in df.columns for col in ['gyro_x', 'gyro_y', 'gyro_z']):
                import numpy as np
                movement = np.sqrt(df['gyro_x']**2 + df['gyro_y']**2 + df['gyro_z']**2)
                ax3.plot(df[time_col], movement, 'g-', linewidth=1, label='Movement')
            ax3.set_ylabel('Movement (°/s)')
            ax3.set_xlabel(time_label)
            ax3.set_title('Head Movement')
            ax3.legend(loc='upper right')
            ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"✓ Saved visualization to: {output_path}")
        plt.close()


def main():
    """Main function."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python muse_fitbit_sync.py <muse_csv_file>")
        print("\nExample:")
        print("  python muse_fitbit_sync.py recordings/2025-12-07/muse_session_90_20251207_200456.csv")
        return
    
    muse_csv = sys.argv[1]
    
    sync = MuseFitbitSync()
    merged_df = sync.sync_with_muse_session(muse_csv)
    
    if merged_df is not None:
        print("\n✓ Sync complete!")
        print(f"  Total samples: {len(merged_df)}")
        print(f"  With heart rate: {merged_df['heart_rate'].notna().sum()}")


if __name__ == "__main__":
    main()
