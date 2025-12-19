"""
Sync Garmin Connect and Muse Data
Match Garmin heart rate and activity data with Muse EEG recordings using timestamps
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from garmin_interface import GarminInterface


class MuseGarminSync:
    """Synchronize Muse and Garmin Connect data based on timestamps."""
    
    def __init__(self):
        """Initialize the sync tool."""
        self.garmin = GarminInterface()
    
    def sync_with_muse_session(self, muse_csv_path, output_path=None):
        """
        Sync Garmin data with a Muse recording session.
        
        Args:
            muse_csv_path: Path to Muse CSV file
            output_path: Optional path to save synced data (default: same folder as Muse file)
            
        Returns:
            DataFrame with combined Muse and Garmin data
        """
        if not self.garmin.client:
            print("Garmin not authenticated")
            return None
        
        print("\n" + "="*60)
        print("MUSE + GARMIN CONNECT DATA SYNC")
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
                # Use ISO timestamp if available for better timezone handling
                if 'start_time_iso' in metadata:
                    start_dt = datetime.fromisoformat(metadata['start_time_iso'].replace(' ', 'T'))
                    print(f"✓ Session started: {metadata['start_time_iso']}")
                else:
                    start_time_unix = metadata['start_time_unix']
                    start_dt = datetime.fromtimestamp(start_time_unix)
                    print(f"✓ Session started: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            # Try to get from first timestamp
            if 'timestamp_iso' in muse_df.columns:
                start_dt = pd.to_datetime(muse_df['timestamp_iso'].iloc[0])
            elif 'timestamp_unix' in muse_df.columns:
                start_time_unix = muse_df['timestamp_unix'].iloc[0]
                start_dt = datetime.fromtimestamp(start_time_unix)
            else:
                print("✗ Cannot determine session start time")
                return None
        if 'elapsed_time' in muse_df.columns:
            duration = muse_df['elapsed_time'].max()
        elif 'timestamp' in muse_df.columns:
            duration = muse_df['timestamp'].max()
        else:
            duration = len(muse_df) / 256  # Assume 256 Hz sampling
        
        end_dt = start_dt + timedelta(seconds=duration)
        
        print(f"✓ Duration: {duration:.1f} seconds")
        print(f"✓ Time range: {start_dt.strftime('%H:%M:%S')} to {end_dt.strftime('%H:%M:%S')}")
        
        # Get Garmin heart rate data for the session date
        session_date = start_dt.strftime("%Y-%m-%d")
        print(f"\nFetching Garmin heart rate data for {session_date}...")
        
        garmin_hr = self.garmin.get_heart_rate_intraday(session_date, detail_level='second')
        
        if garmin_hr is None or garmin_hr.empty:
            print("✗ No Garmin heart rate data found for this date")
            return None
        
        print(f"✓ Loaded {len(garmin_hr)} heart rate samples")
        
        # Filter Garmin data to session time range
        garmin_hr['datetime'] = pd.to_datetime(garmin_hr['datetime'])
        
        # Debug: Show time range comparison
        print(f"\nDebug - Garmin data range:")
        print(f"  First: {garmin_hr['datetime'].min()}")
        print(f"  Last: {garmin_hr['datetime'].max()}")
        print(f"Debug - Session range:")
        print(f"  Start: {start_dt}")
        print(f"  End: {end_dt}")
        
        garmin_session = garmin_hr[
            (garmin_hr['datetime'] >= start_dt) & 
            (garmin_hr['datetime'] <= end_dt)
        ].copy()
        
        if garmin_session.empty:
            print("✗ No Garmin data overlaps with Muse session time")
            print(f"Debug - Check comparison: {garmin_hr['datetime'].dtype} vs {type(start_dt)}")
            return None
        
        print(f"✓ {len(garmin_session)} heart rate samples during session")
        
        # Get stress data
        print(f"\nFetching Garmin stress data for {session_date}...")
        garmin_stress = self.garmin.get_stress_data(session_date)
        
        garmin_stress_session = None
        if garmin_stress is not None and not garmin_stress.empty:
            garmin_stress['datetime'] = pd.to_datetime(garmin_stress['datetime'])
            garmin_stress_session = garmin_stress[
                (garmin_stress['datetime'] >= start_dt) & 
                (garmin_stress['datetime'] <= end_dt)
            ].copy()
            print(f"✓ {len(garmin_stress_session)} stress measurements during session")
        
        # Prepare Muse data with proper timestamps
        if 'timestamp_unix' in muse_df.columns:
            muse_df['datetime'] = pd.to_datetime(muse_df['timestamp_unix'], unit='s')
        elif 'timestamp_iso' in muse_df.columns:
            muse_df['datetime'] = pd.to_datetime(muse_df['timestamp_iso'])
        else:
            # Create timestamps from elapsed time
            muse_df['datetime'] = start_dt + pd.to_timedelta(muse_df['elapsed_time'], unit='s')
        
        # Merge heart rate data using nearest timestamp
        muse_df = muse_df.sort_values('datetime')
        garmin_session = garmin_session.sort_values('datetime')
        
        merged_df = pd.merge_asof(
            muse_df,
            garmin_session[['datetime', 'heart_rate_bpm']],
            on='datetime',
            direction='nearest',
            tolerance=pd.Timedelta('30s')
        )
        
        # Merge stress data if available
        if garmin_stress_session is not None and not garmin_stress_session.empty:
            garmin_stress_session = garmin_stress_session.sort_values('datetime')
            merged_df = pd.merge_asof(
                merged_df,
                garmin_stress_session[['datetime', 'stress_level']],
                on='datetime',
                direction='nearest',
                tolerance=pd.Timedelta('5min')
            )
        
        # Save combined data
        if output_path is None:
            output_path = muse_csv.with_name(f"{muse_csv.stem}_garmin_sync.csv")
        
        merged_df.to_csv(output_path, index=False)
        print(f"\n✓ Saved combined data to: {output_path}")
        
        # Generate summary
        self._create_summary(merged_df, output_path)
        
        # Create visualization
        self._visualize_sync(merged_df, output_path)
        
        return merged_df
    
    def _create_summary(self, df, output_path):
        """Create a text summary of the synced session."""
        summary_file = Path(str(output_path).replace('.csv', '_summary.txt'))
        
        with open(summary_file, 'w') as f:
            f.write("MUSE + GARMIN SYNC SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            
            # Session info
            start_time = df['datetime'].min()
            end_time = df['datetime'].max()
            duration = (end_time - start_time).total_seconds()
            
            f.write(f"Session Start: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Session End:   {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duration:      {duration:.0f} seconds ({duration/60:.1f} minutes)\n\n")
            
            # Garmin heart rate stats
            hr_valid = df['heart_rate_bpm'].notna().sum()
            if hr_valid > 0:
                f.write(f"GARMIN HEART RATE\n")
                f.write(f"-" * 40 + "\n")
                f.write(f"Valid Samples: {hr_valid}\n")
                f.write(f"Average HR:    {df['heart_rate_bpm'].mean():.1f} bpm\n")
                f.write(f"Min HR:        {df['heart_rate_bpm'].min():.0f} bpm\n")
                f.write(f"Max HR:        {df['heart_rate_bpm'].max():.0f} bpm\n")
                f.write(f"Std Dev:       {df['heart_rate_bpm'].std():.1f} bpm\n\n")
            
            # Garmin stress stats
            if 'stress_level' in df.columns:
                stress_valid = df['stress_level'].notna().sum()
                if stress_valid > 0:
                    f.write(f"GARMIN STRESS LEVEL\n")
                    f.write(f"-" * 40 + "\n")
                    f.write(f"Valid Samples: {stress_valid}\n")
                    f.write(f"Average:       {df['stress_level'].mean():.1f}\n")
                    f.write(f"Min:           {df['stress_level'].min():.0f}\n")
                    f.write(f"Max:           {df['stress_level'].max():.0f}\n\n")
            
            # Muse EEG stats
            eeg_channels = ['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']
            f.write(f"MUSE EEG CHANNELS\n")
            f.write(f"-" * 40 + "\n")
            for ch in eeg_channels:
                if ch in df.columns:
                    f.write(f"{ch.upper():12} - Mean: {df[ch].mean():7.2f} µV, Std: {df[ch].std():7.2f} µV\n")
        
        print(f"✓ Saved summary to: {summary_file}")
    
    def _visualize_sync(self, df, output_path):
        """Create visualization of synced data."""
        plot_file = Path(str(output_path).replace('.csv', '_sync_plot.png'))
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
        
        # Use elapsed time for x-axis
        if 'elapsed_time' in df.columns:
            time_col = 'elapsed_time'
        else:
            time_col = df.index / 256  # Approximate if no elapsed time
        
        # Plot 1: EEG channels
        ax = axes[0]
        for ch, color in zip(['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10'], 
                             ['#3498db', '#9b59b6', '#e67e22', '#1abc9c']):
            if ch in df.columns:
                ax.plot(df[time_col], df[ch], label=ch.upper(), color=color, alpha=0.7, linewidth=0.5)
        ax.set_ylabel('EEG Amplitude (µV)')
        ax.set_title('Muse EEG Brain Waves')
        ax.legend(loc='upper right', ncol=4)
        ax.grid(True, alpha=0.3)
        
        # Plot 2: Garmin heart rate
        ax = axes[1]
        if 'heart_rate_bpm' in df.columns:
            valid_hr = df[df['heart_rate_bpm'].notna()]
            ax.plot(valid_hr[time_col], valid_hr['heart_rate_bpm'], 
                   color='#e74c3c', linewidth=2, label='Heart Rate')
            ax.fill_between(valid_hr[time_col], valid_hr['heart_rate_bpm'], 
                           alpha=0.3, color='#e74c3c')
            ax.set_ylabel('Heart Rate (bpm)')
            ax.set_title('Garmin Heart Rate')
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
        
        # Plot 3: Garmin stress (if available)
        ax = axes[2]
        if 'stress_level' in df.columns:
            valid_stress = df[df['stress_level'].notna()]
            if not valid_stress.empty:
                ax.plot(valid_stress[time_col], valid_stress['stress_level'], 
                       color='#f39c12', linewidth=2, marker='o', markersize=4, label='Stress Level')
                ax.fill_between(valid_stress[time_col], valid_stress['stress_level'], 
                               alpha=0.3, color='#f39c12')
                ax.set_ylabel('Stress Level')
                ax.set_title('Garmin Stress')
                ax.legend(loc='upper right')
                ax.grid(True, alpha=0.3)
        
        axes[-1].set_xlabel('Time (seconds)')
        
        plt.tight_layout()
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Saved visualization to: {plot_file}")


def main():
    """Demo usage of Muse + Garmin sync."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python muse_garmin_sync.py <muse_csv_file>")
        print("\nExample:")
        print("  python muse_garmin_sync.py recordings/2025-12-18/muse_session_20251218_143022.csv")
        return
    
    muse_file = sys.argv[1]
    
    if not Path(muse_file).exists():
        print(f"Error: File not found: {muse_file}")
        return
    
    # Create sync object and process
    sync = MuseGarminSync()
    result = sync.sync_with_muse_session(muse_file)
    
    if result is not None:
        print("\n✓ Sync completed successfully!")


if __name__ == "__main__":
    main()
