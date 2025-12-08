"""
Convert Muse PPG data to heart rate in beats per minute (BPM)
"""

import numpy as np
import pandas as pd
from scipy import signal
from pathlib import Path


def ppg_to_bpm(ppg_data, sampling_rate=256):
    """
    Convert PPG signal to heart rate in beats per minute.
    
    Args:
        ppg_data: Array of PPG values
        sampling_rate: Sampling rate in Hz (default: 256 for Muse)
        
    Returns:
        Array of heart rate values in BPM
    """
    # Remove NaN values
    ppg_clean = ppg_data[~np.isnan(ppg_data)]
    
    if len(ppg_clean) < sampling_rate:
        return None
    
    # Bandpass filter to isolate heart rate frequencies (0.5-4 Hz = 30-240 BPM)
    nyquist = sampling_rate / 2
    low = 0.5 / nyquist
    high = 4.0 / nyquist
    
    b, a = signal.butter(3, [low, high], btype='band')
    ppg_filtered = signal.filtfilt(b, a, ppg_clean)
    
    # Find peaks in the filtered signal
    # Minimum distance between peaks = 0.25 seconds (240 BPM max)
    min_distance = int(0.25 * sampling_rate)
    peaks, _ = signal.find_peaks(ppg_filtered, distance=min_distance)
    
    # Calculate instantaneous heart rate
    if len(peaks) < 2:
        return None
    
    # Time between peaks (in seconds)
    peak_intervals = np.diff(peaks) / sampling_rate
    
    # Convert to BPM
    instantaneous_bpm = 60.0 / peak_intervals
    
    # Create time-aligned BPM array
    bpm_array = np.full(len(ppg_data), np.nan)
    
    # Interpolate BPM values across the signal
    peak_times = peaks[:-1]  # Use all peaks except the last
    for i, (peak_idx, bpm_val) in enumerate(zip(peak_times, instantaneous_bpm)):
        # Fill from this peak to next peak
        if i < len(peak_times) - 1:
            next_peak = peak_times[i + 1]
            bpm_array[peak_idx:next_peak] = bpm_val
        else:
            # Last segment
            bpm_array[peak_idx:] = bpm_val
    
    return bpm_array


def add_bpm_to_csv(csv_path, output_path=None):
    """
    Add heart rate (BPM) column to Muse CSV file.
    
    Args:
        csv_path: Path to Muse CSV file
        output_path: Optional output path (default: overwrites original)
    """
    print(f"\nProcessing: {Path(csv_path).name}")
    
    # Load data
    df = pd.read_csv(csv_path)
    
    if 'ppg_avg' not in df.columns:
        print("✗ No PPG data found in file")
        return None
    
    print(f"✓ Loaded {len(df)} samples")
    
    # Convert PPG to BPM
    print("Converting PPG to heart rate (BPM)...")
    bpm_data = ppg_to_bpm(df['ppg_avg'].values)
    
    if bpm_data is None:
        print("✗ Could not calculate heart rate")
        return None
    
    # Add BPM column
    df['heart_rate_bpm'] = bpm_data
    
    # Calculate statistics
    valid_bpm = df['heart_rate_bpm'].dropna()
    if len(valid_bpm) > 0:
        print(f"\n{'='*60}")
        print("HEART RATE STATISTICS")
        print(f"{'='*60}")
        print(f"Mean HR:    {valid_bpm.mean():.1f} BPM")
        print(f"Min HR:     {valid_bpm.min():.1f} BPM")
        print(f"Max HR:     {valid_bpm.max():.1f} BPM")
        print(f"Std Dev:    {valid_bpm.std():.1f} BPM")
        print(f"Samples:    {len(valid_bpm)} / {len(df)}")
        print(f"{'='*60}")
    
    # Save
    if output_path is None:
        output_path = csv_path
    
    df.to_csv(output_path, index=False)
    print(f"\n✓ Saved with heart_rate_bpm column to: {output_path}")
    
    return df


def process_all_sessions(recordings_dir="recordings"):
    """Process all Muse sessions and add BPM data."""
    recordings_path = Path(recordings_dir)
    
    print("="*60)
    print("CONVERTING MUSE PPG TO HEART RATE (BPM)")
    print("="*60)
    
    # Find all CSV files
    csv_files = list(recordings_path.glob("**/*.csv"))
    muse_files = [f for f in csv_files if 'muse_session' in f.name and 'fitbit' not in f.name]
    
    print(f"\nFound {len(muse_files)} Muse session file(s)")
    
    for csv_file in muse_files:
        add_bpm_to_csv(csv_file)
    
    print("\n✓ All sessions processed!")


def main():
    """Main function."""
    import sys
    
    if len(sys.argv) > 1:
        # Process specific file
        csv_path = sys.argv[1]
        add_bpm_to_csv(csv_path)
    else:
        # Process all files
        process_all_sessions()


if __name__ == "__main__":
    main()
