"""
CPAP + Muse EEG Sleep Correlation Tool

Correlates CPAP respiratory data with Muse EEG sleep stages to provide
comprehensive sleep analysis showing how breathing events relate to brain activity.
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
from pathlib import Path


class SleepCorrelator:
    """Correlates CPAP and Muse EEG data for comprehensive sleep analysis"""
    
    def __init__(self, muse_csv_path, cpap_json_path):
        """
        Initialize correlator with Muse CSV and CPAP JSON report
        
        Args:
            muse_csv_path: Path to Muse EEG recording CSV
            cpap_json_path: Path to CPAP analysis JSON report
        """
        self.muse_csv_path = muse_csv_path
        self.cpap_json_path = cpap_json_path
        
        # Load data
        print(f"Loading Muse EEG data from: {muse_csv_path}")
        self.muse_data = pd.read_csv(muse_csv_path)
        
        print(f"Loading CPAP data from: {cpap_json_path}")
        with open(cpap_json_path, 'r') as f:
            self.cpap_data = json.load(f)
        
        # Parse timestamps
        self._parse_timestamps()
        
        # Results storage
        self.correlation_results = {}
        
    def _parse_timestamps(self):
        """Parse and align timestamps from both sources"""
        # Muse timestamp (assuming elapsed_time or timestamp column)
        if 'timestamp' in self.muse_data.columns:
            self.muse_data['datetime'] = pd.to_datetime(self.muse_data['timestamp'])
            self.muse_start = self.muse_data['datetime'].iloc[0]
        elif 'elapsed_time' in self.muse_data.columns:
            # Use first timestamp as reference
            # Try to get recording start time from filename or use current date
            base_time = self._extract_datetime_from_filename(self.muse_csv_path)
            self.muse_data['datetime'] = base_time + pd.to_timedelta(self.muse_data['elapsed_time'], unit='s')
            self.muse_start = self.muse_data['datetime'].iloc[0]
        else:
            raise ValueError("Muse CSV must have 'timestamp' or 'elapsed_time' column")
        
        # CPAP timestamp
        cpap_time_str = self.cpap_data['session']['recording_start']
        self.cpap_start = pd.to_datetime(cpap_time_str)
        
        print(f"\nTimestamp alignment:")
        print(f"  Muse start:  {self.muse_start}")
        print(f"  CPAP start:  {self.cpap_start}")
        print(f"  Offset:      {abs((self.muse_start - self.cpap_start).total_seconds())} seconds")
        
    def _extract_datetime_from_filename(self, filepath):
        """Extract datetime from Muse filename pattern"""
        filename = Path(filepath).stem
        try:
            # Look for pattern like muse_session_YYYYMMDD_HHMMSS
            if '_' in filename:
                parts = filename.split('_')
                for i, part in enumerate(parts):
                    if len(part) == 8 and part.isdigit():  # YYYYMMDD
                        if i + 1 < len(parts) and len(parts[i+1]) == 6 and parts[i+1].isdigit():  # HHMMSS
                            date_str = part
                            time_str = parts[i+1]
                            return pd.to_datetime(f"{date_str}_{time_str}", format='%Y%m%d_%H%M%S')
        except:
            pass
        
        # Default to file modification time
        mod_time = os.path.getmtime(filepath)
        return pd.to_datetime(mod_time, unit='s')
    
    def calculate_sleep_stages(self, window_seconds=30):
        """
        Calculate sleep stages from Muse EEG data
        
        Args:
            window_seconds: Window size for sleep stage classification (default 30s)
        """
        print(f"\nCalculating sleep stages (window: {window_seconds}s)...")
        
        # Calculate band powers if not already present
        if 'Delta' not in self.muse_data.columns:
            print("  Computing frequency band powers...")
            self._calculate_band_powers()
        
        # Window the data
        sample_rate = 256  # Muse S sample rate
        window_samples = window_seconds * sample_rate
        
        stages = []
        stage_times = []
        
        for start_idx in range(0, len(self.muse_data), window_samples):
            end_idx = min(start_idx + window_samples, len(self.muse_data))
            window = self.muse_data.iloc[start_idx:end_idx]
            
            if len(window) < window_samples // 2:  # Skip incomplete windows
                continue
            
            # Average band powers in window
            delta = window['Delta'].mean() if 'Delta' in window.columns else 0
            theta = window['Theta'].mean() if 'Theta' in window.columns else 0
            alpha = window['Alpha'].mean() if 'Alpha' in window.columns else 0
            beta = window['Beta'].mean() if 'Beta' in window.columns else 0
            
            # Simple sleep stage classification
            stage = self._classify_sleep_stage(delta, theta, alpha, beta)
            stages.append(stage)
            stage_times.append(window['datetime'].iloc[0])
        
        self.sleep_stages = pd.DataFrame({
            'datetime': stage_times,
            'stage': stages
        })
        
        print(f"  ✓ Classified {len(stages)} sleep stage windows")
        self._print_sleep_stage_summary()
        
    def _calculate_band_powers(self):
        """Calculate EEG frequency band powers"""
        from scipy import signal
        
        # Use average of all EEG channels
        eeg_channels = ['TP9', 'AF7', 'AF8', 'TP10']
        available_channels = [ch for ch in eeg_channels if ch in self.muse_data.columns]
        
        if not available_channels:
            print("  Warning: No EEG channels found, using mock data")
            return
        
        eeg_avg = self.muse_data[available_channels].mean(axis=1)
        
        # Calculate band powers using windowed FFT
        window_size = 256  # 1 second windows
        bands = {
            'Delta': (0.5, 4),
            'Theta': (4, 8),
            'Alpha': (8, 13),
            'Beta': (13, 30)
        }
        
        for band_name, (low, high) in bands.items():
            powers = []
            for i in range(0, len(eeg_avg), window_size):
                window = eeg_avg.iloc[i:i+window_size]
                if len(window) < window_size // 2:
                    powers.append(np.nan)
                    continue
                
                # FFT
                freqs, psd = signal.welch(window, fs=256, nperseg=min(len(window), 256))
                
                # Integrate power in band
                band_mask = (freqs >= low) & (freqs <= high)
                band_power = np.trapz(psd[band_mask], freqs[band_mask])
                powers.append(band_power)
            
            # Expand to match original data length
            expanded_powers = np.repeat(powers, window_size)[:len(eeg_avg)]
            self.muse_data[band_name] = expanded_powers
    
    def _classify_sleep_stage(self, delta, theta, alpha, beta):
        """
        Classify sleep stage based on band powers
        
        Returns: 'Wake', 'REM', 'Light', 'Deep'
        """
        total = delta + theta + alpha + beta
        if total == 0:
            return 'Unknown'
        
        # Normalize
        delta_pct = delta / total
        theta_pct = theta / total
        alpha_pct = alpha / total
        beta_pct = beta / total
        
        # Simple classification rules
        if beta_pct > 0.3 or alpha_pct > 0.4:
            return 'Wake'
        elif delta_pct > 0.5:
            return 'Deep'
        elif theta_pct > 0.3 and delta_pct > 0.2:
            return 'REM'
        else:
            return 'Light'
    
    def _print_sleep_stage_summary(self):
        """Print summary of sleep stages"""
        stage_counts = self.sleep_stages['stage'].value_counts()
        total_time = len(self.sleep_stages) * 30 / 60  # Convert 30s windows to minutes
        
        print(f"\n  Sleep Stage Distribution:")
        for stage in ['Wake', 'Light', 'Deep', 'REM', 'Unknown']:
            if stage in stage_counts:
                count = stage_counts[stage]
                minutes = count * 30 / 60
                pct = (count / len(self.sleep_stages)) * 100
                print(f"    {stage:8s}: {minutes:5.1f} min ({pct:5.1f}%)")
    
    def correlate_events(self):
        """Correlate CPAP events with sleep stages"""
        print("\nCorrelating CPAP events with sleep stages...")
        
        # Extract CPAP events
        cpap_events = self.cpap_data.get('events', {})
        ahi = self.cpap_data.get('ahi', {}).get('ahi', 0)
        
        print(f"  CPAP AHI: {ahi} events/hour")
        print(f"  Total events: {self.cpap_data.get('ahi', {}).get('total_events', 0)}")
        
        # If no events, correlation is simple
        if ahi == 0:
            print("  ✓ No respiratory events to correlate")
            self.correlation_results = {
                'events_by_stage': {'Wake': 0, 'Light': 0, 'Deep': 0, 'REM': 0},
                'ahi': ahi,
                'total_events': 0,
                'sleep_quality_score': self._calculate_sleep_quality()
            }
            return
        
        # TODO: If CPAP has event timestamps, correlate with sleep stages
        # For now, store basic results
        self.correlation_results = {
            'ahi': ahi,
            'total_events': self.cpap_data.get('ahi', {}).get('total_events', 0),
            'sleep_quality_score': self._calculate_sleep_quality()
        }
    
    def _calculate_sleep_quality(self):
        """
        Calculate overall sleep quality score (0-100)
        Based on: deep sleep %, AHI, sleep efficiency
        """
        if not hasattr(self, 'sleep_stages'):
            return None
        
        stage_counts = self.sleep_stages['stage'].value_counts()
        total = len(self.sleep_stages)
        
        # Deep sleep percentage (target: 20-25%)
        deep_pct = (stage_counts.get('Deep', 0) / total) * 100 if total > 0 else 0
        deep_score = min(100, (deep_pct / 20) * 100)  # 20% = perfect
        
        # REM percentage (target: 20-25%)
        rem_pct = (stage_counts.get('REM', 0) / total) * 100 if total > 0 else 0
        rem_score = min(100, (rem_pct / 20) * 100)
        
        # Sleep efficiency (time asleep vs total time)
        wake_pct = (stage_counts.get('Wake', 0) / total) * 100 if total > 0 else 0
        efficiency_score = max(0, 100 - wake_pct)
        
        # AHI impact (lower is better)
        ahi = self.cpap_data.get('ahi', {}).get('ahi', 0)
        if ahi < 5:
            ahi_score = 100
        elif ahi < 15:
            ahi_score = 75
        elif ahi < 30:
            ahi_score = 50
        else:
            ahi_score = 25
        
        # Weighted average
        quality_score = (deep_score * 0.3 + rem_score * 0.3 + efficiency_score * 0.2 + ahi_score * 0.2)
        
        return round(quality_score, 1)
    
    def generate_correlation_report(self):
        """Generate comprehensive correlation report"""
        print("\n" + "="*70)
        print("SLEEP CORRELATION REPORT: CPAP + Muse EEG")
        print("="*70)
        
        # Session info
        print(f"\nSESSION INFORMATION:")
        print(f"  Muse Recording: {self.muse_start}")
        print(f"  CPAP Recording: {self.cpap_start}")
        print(f"  Duration: {self.cpap_data['session']['duration_hours']:.1f} hours")
        
        # Sleep architecture
        if hasattr(self, 'sleep_stages'):
            print(f"\nSLEEP ARCHITECTURE (Muse EEG):")
            stage_counts = self.sleep_stages['stage'].value_counts()
            total = len(self.sleep_stages)
            for stage in ['Wake', 'Light', 'Deep', 'REM']:
                if stage in stage_counts:
                    count = stage_counts[stage]
                    minutes = count * 30 / 60
                    pct = (count / total) * 100
                    print(f"  {stage:8s}: {minutes:5.1f} min ({pct:5.1f}%)")
        
        # Respiratory analysis
        print(f"\nRESPIRATORY ANALYSIS (CPAP):")
        ahi_data = self.cpap_data.get('ahi', {})
        print(f"  AHI: {ahi_data.get('ahi', 0):.1f} events/hour ({ahi_data.get('severity', 'Unknown')})")
        print(f"  Total Events: {ahi_data.get('total_events', 0)}")
        
        # Pressure info
        pressure = self.cpap_data.get('pressure', {})
        if pressure:
            print(f"\nPRESSURE SETTINGS:")
            print(f"  Mean: {pressure.get('mean', 0):.1f} cmH2O")
            print(f"  Range: {pressure.get('min', 0):.1f} - {pressure.get('max', 0):.1f} cmH2O")
        
        # Overall quality
        quality = self.correlation_results.get('sleep_quality_score')
        if quality is not None:
            print(f"\nOVERALL SLEEP QUALITY: {quality}/100")
            if quality >= 80:
                rating = "Excellent"
            elif quality >= 65:
                rating = "Good"
            elif quality >= 50:
                rating = "Fair"
            else:
                rating = "Poor"
            print(f"  Rating: {rating}")
        
        print("\n" + "="*70)
        
        return self.correlation_results
    
    def plot_correlation(self, output_path=None):
        """
        Create visualization showing CPAP and EEG data correlation
        
        Args:
            output_path: Path to save plot (optional)
        """
        print("\nGenerating correlation plot...")
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
        
        # Plot 1: Sleep stages hypnogram
        if hasattr(self, 'sleep_stages'):
            ax1 = axes[0]
            
            # Convert stages to numeric for plotting
            stage_map = {'Wake': 3, 'REM': 2, 'Light': 1, 'Deep': 0, 'Unknown': -1}
            numeric_stages = [stage_map[s] for s in self.sleep_stages['stage']]
            times = [(t - self.sleep_stages['datetime'].iloc[0]).total_seconds() / 3600 
                     for t in self.sleep_stages['datetime']]
            
            ax1.step(times, numeric_stages, where='post', color='navy', linewidth=2)
            ax1.set_ylabel('Sleep Stage', fontsize=11, fontweight='bold')
            ax1.set_yticks([0, 1, 2, 3])
            ax1.set_yticklabels(['Deep', 'Light', 'REM', 'Wake'])
            ax1.grid(True, alpha=0.3)
            ax1.set_title('Muse EEG Sleep Stages + CPAP Respiratory Data', fontsize=13, fontweight='bold')
        
        # Plot 2: CPAP Pressure (if available from CSV export)
        ax2 = axes[1]
        cpap_csv_path = self.cpap_json_path.replace('.cpap_report.json', '.csv')
        if os.path.exists(cpap_csv_path):
            cpap_df = pd.read_csv(cpap_csv_path)
            if 'Press.40ms' in cpap_df.columns and 'time' in cpap_df.columns:
                ax2.plot(cpap_df['time'] / 3600, cpap_df['Press.40ms'], 
                        color='darkgreen', linewidth=0.5, alpha=0.7)
                ax2.set_ylabel('CPAP Pressure\n(cmH2O)', fontsize=11, fontweight='bold')
                ax2.grid(True, alpha=0.3)
        else:
            ax2.text(0.5, 0.5, 'CPAP pressure data not available', 
                    ha='center', va='center', transform=ax2.transAxes)
            ax2.set_ylabel('CPAP Pressure\n(cmH2O)', fontsize=11, fontweight='bold')
        
        # Plot 3: Respiratory flow
        ax3 = axes[2]
        if os.path.exists(cpap_csv_path):
            cpap_df = pd.read_csv(cpap_csv_path)
            if 'Flow.40ms' in cpap_df.columns and 'time' in cpap_df.columns:
                ax3.plot(cpap_df['time'] / 3600, cpap_df['Flow.40ms'], 
                        color='darkred', linewidth=0.5, alpha=0.7)
                ax3.set_ylabel('Airflow\n(L/s)', fontsize=11, fontweight='bold')
                ax3.set_xlabel('Time (hours)', fontsize=11, fontweight='bold')
                ax3.grid(True, alpha=0.3)
        else:
            ax3.text(0.5, 0.5, 'Airflow data not available', 
                    ha='center', va='center', transform=ax3.transAxes)
            ax3.set_ylabel('Airflow\n(L/s)', fontsize=11, fontweight='bold')
            ax3.set_xlabel('Time (hours)', fontsize=11, fontweight='bold')
        
        plt.tight_layout()
        
        if output_path is None:
            # Generate output path based on input files
            base_path = Path(self.muse_csv_path).parent
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = base_path / f"sleep_correlation_{timestamp}.png"
        
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"  ✓ Correlation plot saved to: {output_path}")
        
        return output_path
    
    def export_correlation_report(self, output_path=None):
        """Export correlation results to JSON"""
        if output_path is None:
            base_path = Path(self.muse_csv_path).parent
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = base_path / f"sleep_correlation_{timestamp}.json"
        
        report = {
            'muse_file': str(self.muse_csv_path),
            'cpap_file': str(self.cpap_json_path),
            'timestamp': datetime.now().isoformat(),
            'session': {
                'muse_start': self.muse_start.isoformat(),
                'cpap_start': self.cpap_start.isoformat(),
                'duration_hours': self.cpap_data['session']['duration_hours']
            },
            'correlation_results': self.correlation_results
        }
        
        if hasattr(self, 'sleep_stages'):
            stage_counts = self.sleep_stages['stage'].value_counts().to_dict()
            total = len(self.sleep_stages)
            report['sleep_architecture'] = {
                stage: {
                    'count': int(count),
                    'minutes': round(count * 30 / 60, 1),
                    'percentage': round((count / total) * 100, 1)
                }
                for stage, count in stage_counts.items()
            }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"  ✓ Correlation report saved to: {output_path}")
        return output_path


def main():
    import sys
    
    if len(sys.argv) < 3:
        print("CPAP + Muse EEG Sleep Correlation Tool")
        print("\nUsage:")
        print("  python muse_cpap_correlator.py <muse_csv> <cpap_json>")
        print("\nExample:")
        print("  python muse_cpap_correlator.py recordings/muse_session.csv D:/DATALOG/20251208_013717_BRP.cpap_report.json")
        sys.exit(1)
    
    muse_csv = sys.argv[1]
    cpap_json = sys.argv[2]
    
    # Validate files exist
    if not os.path.exists(muse_csv):
        print(f"Error: Muse CSV not found: {muse_csv}")
        sys.exit(1)
    
    if not os.path.exists(cpap_json):
        print(f"Error: CPAP JSON report not found: {cpap_json}")
        sys.exit(1)
    
    try:
        # Create correlator
        correlator = SleepCorrelator(muse_csv, cpap_json)
        
        # Calculate sleep stages from Muse data
        correlator.calculate_sleep_stages(window_seconds=30)
        
        # Correlate with CPAP events
        correlator.correlate_events()
        
        # Generate report
        correlator.generate_correlation_report()
        
        # Create visualization
        correlator.plot_correlation()
        
        # Export results
        correlator.export_correlation_report()
        
        print("\n✓ Correlation analysis complete!")
        
    except Exception as e:
        print(f"\n✗ Error during correlation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
