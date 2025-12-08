"""
Muse S Data Recorder and Analyzer
Records EEG sessions to CSV files and provides analysis tools
"""

import numpy as np
import pandas as pd
from muse_interface import MuseInterface
import time
from datetime import datetime
import matplotlib.pyplot as plt
from pathlib import Path
import winsound  # For audio notifications on Windows


class MuseRecorder:
    """Record Muse S data to CSV files."""
    
    def __init__(self, output_dir="recordings"):
        """Initialize the recorder."""
        self.muse = MuseInterface()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.is_recording = False
        self.data = {
            'timestamp_unix': [],      # Unix epoch timestamp (seconds since 1970-01-01)
            'timestamp_iso': [],       # ISO 8601 format for human readability
            'elapsed_time': [],        # Seconds since recording started
            'eeg_tp9': [],
            'eeg_af7': [],
            'eeg_af8': [],
            'eeg_tp10': [],
            'ppg_avg': [],
            'gyro_x': [],
            'gyro_y': [],
            'gyro_z': [],
            'acc_x': [],
            'acc_y': [],
            'acc_z': []
        }
    
    def record_session(self, duration=60, session_name=None):
        """
        Record a Muse session to CSV.
        
        Args:
            duration: Recording duration in seconds
            session_name: Optional name for the session (default: timestamp)
        """
        print("=" * 60)
        print("Muse S Data Recorder")
        print("=" * 60)
        
        # Connect to Muse
        print("\nConnecting to Muse S...")
        if not self.muse.connect(timeout=10):
            print("\nFailed to connect to Muse. Exiting...")
            return None
        
        # Create date-based folder structure
        current_date = datetime.now()
        date_folder = self.output_dir / current_date.strftime("%Y-%m-%d")
        date_folder.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp_str = current_date.strftime("%Y%m%d_%H%M%S")
        if session_name is None:
            # If no session name, use just the timestamp
            filename = date_folder / f"muse_session_{timestamp_str}.csv"
        else:
            # If session name provided, append timestamp to it
            filename = date_folder / f"muse_session_{session_name}_{timestamp_str}.csv"
        
        print(f"\n✓ Recording for {duration} seconds...")
        print(f"✓ Saving to: {filename}")
        print("\nRecording started...")
        
        self.is_recording = True
        start_time = time.time()
        sample_count = 0
        
        try:
            while time.time() - start_time < duration:
                current_time_unix = time.time()
                elapsed_time = current_time_unix - start_time
                
                # Read all sensors
                eeg = self.muse.read_eeg_sample()
                ppg = self.muse.read_ppg_sample()
                gyro = self.muse.read_gyro_sample()
                acc = self.muse.read_acc_sample()
                
                # Store timestamps in multiple formats for cross-platform sync
                self.data['timestamp_unix'].append(current_time_unix)
                self.data['timestamp_iso'].append(datetime.fromtimestamp(current_time_unix).isoformat())
                self.data['elapsed_time'].append(elapsed_time)
                
                if eeg and eeg['channels']:
                    self.data['eeg_tp9'].append(eeg['tp9'] or 0)
                    self.data['eeg_af7'].append(eeg['af7'] or 0)
                    self.data['eeg_af8'].append(eeg['af8'] or 0)
                    self.data['eeg_tp10'].append(eeg['tp10'] or 0)
                else:
                    self.data['eeg_tp9'].append(np.nan)
                    self.data['eeg_af7'].append(np.nan)
                    self.data['eeg_af8'].append(np.nan)
                    self.data['eeg_tp10'].append(np.nan)
                
                if ppg and ppg['values']:
                    self.data['ppg_avg'].append(np.mean(ppg['values']))
                else:
                    self.data['ppg_avg'].append(np.nan)
                
                if gyro and gyro['x'] is not None:
                    self.data['gyro_x'].append(gyro['x'])
                    self.data['gyro_y'].append(gyro['y'])
                    self.data['gyro_z'].append(gyro['z'])
                else:
                    self.data['gyro_x'].append(np.nan)
                    self.data['gyro_y'].append(np.nan)
                    self.data['gyro_z'].append(np.nan)
                
                if acc and acc['x'] is not None:
                    self.data['acc_x'].append(acc['x'])
                    self.data['acc_y'].append(acc['y'])
                    self.data['acc_z'].append(acc['z'])
                else:
                    self.data['acc_x'].append(np.nan)
                    self.data['acc_y'].append(np.nan)
                    self.data['acc_z'].append(np.nan)
                
                sample_count += 1
                
                # Progress update
                if sample_count % 100 == 0:
                    elapsed = time.time() - start_time
                    remaining = duration - elapsed
                    print(f"  {elapsed:.1f}s / {duration}s | Samples: {sample_count} | Remaining: {remaining:.1f}s")
                
                time.sleep(0.01)  # 100Hz sampling
        
        except KeyboardInterrupt:
            print("\n\nRecording stopped by user")
        
        finally:
            self.is_recording = False
            # Play completion sound
            self._play_completion_sound()
        
        # Save to CSV
        print(f"\n✓ Recording complete! Collected {sample_count} samples")
        print(f"✓ Saving data...")
        
        df = pd.DataFrame(self.data)
        
        # Add metadata as comments in a separate file for easy sync
        metadata_file = filename.with_suffix('.metadata.json')
        import json
        metadata = {
            'session_name': session_name,
            'start_time_unix': start_time,
            'start_time_iso': datetime.fromtimestamp(start_time).isoformat(),
            'duration_seconds': duration,
            'sample_count': sample_count,
            'device': 'Muse S',
            'sampling_rate_hz': sample_count / duration if duration > 0 else 0,
            'data_columns': list(self.data.keys())
        }
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        df.to_csv(filename, index=False)
        
        print(f"✓ Saved to: {filename}")
        print(f"✓ Metadata: {metadata_file}")
        print(f"✓ File size: {filename.stat().st_size / 1024:.1f} KB")
        print(f"✓ Session started: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')}")
        
        return filename
    
    def _play_completion_sound(self):
        """Play an audio notification when recording is complete."""
        try:
            # Play a pleasant completion sound (3 ascending beeps)
            frequencies = [800, 1000, 1200]  # Hz
            duration = 200  # milliseconds
            
            for freq in frequencies:
                winsound.Beep(freq, duration)
                time.sleep(0.05)  # Small pause between beeps
            
            print("🔔 Recording complete!")
        except Exception as e:
            # If sound fails, just continue (e.g., on systems without speaker)
            pass


class MuseAnalyzer:
    """Analyze recorded Muse S data."""
    
    def __init__(self, csv_file):
        """Load data from CSV file."""
        self.csv_file = Path(csv_file)
        print(f"Loading data from: {self.csv_file}")
        self.df = pd.read_csv(csv_file)
        print(f"✓ Loaded {len(self.df)} samples")
        print(f"✓ Duration: {self.df['timestamp'].max():.1f} seconds")
    
    def calculate_band_powers(self, channel='eeg_af7', fs=256):
        """Calculate frequency band powers over time."""
        eeg_data = self.df[channel].dropna().values
        
        if len(eeg_data) < 256:
            print("Not enough data for frequency analysis")
            return None
        
        # Window size for FFT
        window_size = 256
        hop_size = 128
        
        bands = {
            'Delta (0.5-4Hz)': (0.5, 4),
            'Theta (4-8Hz)': (4, 8),
            'Alpha (8-13Hz)': (8, 13),
            'Beta (13-30Hz)': (13, 30),
            'Gamma (30-50Hz)': (30, 50)
        }
        
        band_powers = {band: [] for band in bands.keys()}
        times = []
        
        for i in range(0, len(eeg_data) - window_size, hop_size):
            segment = eeg_data[i:i+window_size]
            
            # Compute FFT
            fft_vals = np.fft.rfft(segment)
            fft_freq = np.fft.rfftfreq(window_size, 1.0/fs)
            fft_power = np.abs(fft_vals) ** 2
            
            # Calculate power in each band
            for band_name, (low, high) in bands.items():
                idx = np.where((fft_freq >= low) & (fft_freq <= high))
                power = np.mean(fft_power[idx]) if len(idx[0]) > 0 else 0
                band_powers[band_name].append(power)
            
            # Time point (middle of window)
            time_idx = i + window_size // 2
            if time_idx < len(self.df):
                times.append(self.df.iloc[time_idx]['timestamp'])
        
        return pd.DataFrame({
            'timestamp': times,
            **band_powers
        })
    
    def plot_summary(self, save_path=None):
        """Create a summary visualization of the session."""
        fig = plt.figure(figsize=(14, 10))
        fig.suptitle(f'Muse Session Analysis: {self.csv_file.name}', 
                    fontsize=14, fontweight='bold')
        
        # 1. EEG Waveforms
        ax1 = plt.subplot(3, 2, 1)
        ax1.set_title('EEG Waveforms (First 10 seconds)', fontweight='bold')
        mask = self.df['timestamp'] <= 10
        ax1.plot(self.df[mask]['timestamp'], self.df[mask]['eeg_tp9'], 
                label='TP9', alpha=0.7, linewidth=0.5)
        ax1.plot(self.df[mask]['timestamp'], self.df[mask]['eeg_af7'], 
                label='AF7', alpha=0.7, linewidth=0.5)
        ax1.plot(self.df[mask]['timestamp'], self.df[mask]['eeg_af8'], 
                label='AF8', alpha=0.7, linewidth=0.5)
        ax1.plot(self.df[mask]['timestamp'], self.df[mask]['eeg_tp10'], 
                label='TP10', alpha=0.7, linewidth=0.5)
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Amplitude (µV)')
        ax1.legend(loc='upper right', fontsize=8)
        ax1.grid(True, alpha=0.3)
        
        # 2. Frequency Bands Over Time
        ax2 = plt.subplot(3, 2, 2)
        ax2.set_title('Frequency Bands Over Time', fontweight='bold')
        band_df = self.calculate_band_powers()
        if band_df is not None:
            for band in ['Delta (0.5-4Hz)', 'Theta (4-8Hz)', 'Alpha (8-13Hz)', 
                        'Beta (13-30Hz)', 'Gamma (30-50Hz)']:
                ax2.plot(band_df['timestamp'], band_df[band], label=band, linewidth=2)
            ax2.set_xlabel('Time (s)')
            ax2.set_ylabel('Power (µV²)')
            ax2.legend(loc='upper right', fontsize=8)
            ax2.grid(True, alpha=0.3)
        
        # 3. Average Band Power
        ax3 = plt.subplot(3, 2, 3)
        ax3.set_title('Average Frequency Band Power', fontweight='bold')
        if band_df is not None:
            band_means = [band_df[band].mean() for band in 
                         ['Delta (0.5-4Hz)', 'Theta (4-8Hz)', 'Alpha (8-13Hz)', 
                          'Beta (13-30Hz)', 'Gamma (30-50Hz)']]
            colors = ['#3498db', '#9b59b6', '#2ecc71', '#e67e22', '#e74c3c']
            ax3.bar(['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma'], 
                   band_means, color=colors)
            ax3.set_ylabel('Mean Power (µV²)')
            ax3.grid(True, alpha=0.3, axis='y')
        
        # 4. Head Motion (Gyroscope)
        ax4 = plt.subplot(3, 2, 4)
        ax4.set_title('Head Motion (Gyroscope)', fontweight='bold')
        ax4.plot(self.df['timestamp'], self.df['gyro_x'], label='X', alpha=0.7)
        ax4.plot(self.df['timestamp'], self.df['gyro_y'], label='Y', alpha=0.7)
        ax4.plot(self.df['timestamp'], self.df['gyro_z'], label='Z', alpha=0.7)
        ax4.set_xlabel('Time (s)')
        ax4.set_ylabel('Angular Velocity (°/s)')
        ax4.legend(loc='upper right', fontsize=8)
        ax4.grid(True, alpha=0.3)
        
        # 5. EEG Statistics
        ax5 = plt.subplot(3, 2, 5)
        ax5.set_title('EEG Channel Statistics', fontweight='bold')
        channels = ['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']
        means = [self.df[ch].mean() for ch in channels]
        stds = [self.df[ch].std() for ch in channels]
        x = np.arange(len(channels))
        ax5.bar(x, means, yerr=stds, capsize=5, alpha=0.7)
        ax5.set_xticks(x)
        ax5.set_xticklabels(['TP9', 'AF7', 'AF8', 'TP10'])
        ax5.set_ylabel('Amplitude (µV)')
        ax5.grid(True, alpha=0.3, axis='y')
        
        # 6. Session Info
        ax6 = plt.subplot(3, 2, 6)
        ax6.axis('off')
        stats_text = f"""
        Session Statistics:
        
        Duration: {self.df['timestamp'].max():.1f} seconds
        Samples: {len(self.df)}
        Sampling Rate: {len(self.df) / self.df['timestamp'].max():.1f} Hz
        
        EEG Channels:
          TP9  - Mean: {self.df['eeg_tp9'].mean():.1f} µV
          AF7  - Mean: {self.df['eeg_af7'].mean():.1f} µV
          AF8  - Mean: {self.df['eeg_af8'].mean():.1f} µV
          TP10 - Mean: {self.df['eeg_tp10'].mean():.1f} µV
        
        Motion Range:
          Gyro: ±{max(abs(self.df['gyro_x'].min()), abs(self.df['gyro_x'].max())):.1f} °/s
        """
        ax6.text(0.1, 0.5, stats_text, fontsize=10, verticalalignment='center',
                fontfamily='monospace')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✓ Saved analysis plot to: {save_path}")
        
        plt.show()
    
    def get_statistics(self):
        """Get summary statistics of the session."""
        stats = {
            'duration_seconds': self.df['timestamp'].max(),
            'total_samples': len(self.df),
            'sampling_rate': len(self.df) / self.df['timestamp'].max(),
            'eeg_channels': {
                'tp9': {
                    'mean': self.df['eeg_tp9'].mean(),
                    'std': self.df['eeg_tp9'].std(),
                    'min': self.df['eeg_tp9'].min(),
                    'max': self.df['eeg_tp9'].max()
                },
                'af7': {
                    'mean': self.df['eeg_af7'].mean(),
                    'std': self.df['eeg_af7'].std(),
                    'min': self.df['eeg_af7'].min(),
                    'max': self.df['eeg_af7'].max()
                },
                'af8': {
                    'mean': self.df['eeg_af8'].mean(),
                    'std': self.df['eeg_af8'].std(),
                    'min': self.df['eeg_af8'].min(),
                    'max': self.df['eeg_af8'].max()
                },
                'tp10': {
                    'mean': self.df['eeg_tp10'].mean(),
                    'std': self.df['eeg_tp10'].std(),
                    'min': self.df['eeg_tp10'].min(),
                    'max': self.df['eeg_tp10'].max()
                }
            }
        }
        return stats


def main():
    """Main function - record and analyze."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'analyze':
        # Analyze mode
        if len(sys.argv) < 3:
            print("Usage: python muse_recorder.py analyze <csv_file>")
            return
        
        analyzer = MuseAnalyzer(sys.argv[2])
        print("\nGenerating analysis plots...")
        plot_file = Path(sys.argv[2]).with_suffix('.png')
        analyzer.plot_summary(save_path=plot_file)
        
        print("\nSession Statistics:")
        stats = analyzer.get_statistics()
        print(f"  Duration: {stats['duration_seconds']:.1f} seconds")
        print(f"  Samples: {stats['total_samples']}")
        print(f"  Sample Rate: {stats['sampling_rate']:.1f} Hz")
        
    else:
        # Record mode
        duration = 60  # default 60 seconds
        session_name = None
        
        if len(sys.argv) > 1:
            try:
                duration = int(sys.argv[1])
            except ValueError:
                session_name = sys.argv[1]
        
        if len(sys.argv) > 2:
            session_name = sys.argv[2]
        
        recorder = MuseRecorder()
        csv_file = recorder.record_session(duration=duration, session_name=session_name)
        
        if csv_file:
            print("\n" + "=" * 60)
            print("To analyze this recording, run:")
            print(f"  python muse_recorder.py analyze {csv_file}")
            print("=" * 60)


if __name__ == "__main__":
    main()
