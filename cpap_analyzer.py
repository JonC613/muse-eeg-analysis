"""
CPAP EDF Data Analyzer
Analyzes CPAP machine EDF (European Data Format) files
Extracts sleep events, pressure data, and respiratory metrics
"""

import pyedflib
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json


class CPAPAnalyzer:
    """Analyze CPAP machine EDF files."""
    
    def __init__(self, edf_file):
        """
        Initialize CPAP analyzer.
        
        Args:
            edf_file: Path to CPAP EDF file
        """
        self.edf_file = Path(edf_file)
        self.edf = None
        self.signals = {}
        self.header = {}
        
        print(f"Loading CPAP data from: {self.edf_file}")
        self._load_edf()
    
    def _load_edf(self):
        """Load EDF file and extract metadata."""
        try:
            # Try to open with check_file_size=False for discontinuous files
            self.edf = pyedflib.EdfReader(str(self.edf_file), check_file_size=False)
            
            # Extract header information
            self.header = {
                'patient': self.edf.getPatientName(),
                'recording_date': self.edf.getStartdatetime(),
                'duration_seconds': self.edf.getFileDuration(),
                'num_signals': self.edf.signals_in_file,
                'signal_labels': self.edf.getSignalLabels()
            }
            
            print(f"✓ Loaded EDF file")
            print(f"  Patient: {self.header['patient']}")
            print(f"  Recording: {self.header['recording_date']}")
            print(f"  Duration: {self.header['duration_seconds'] / 3600:.1f} hours")
            print(f"  Signals: {self.header['num_signals']}")
            print(f"\nAvailable channels:")
            for i, label in enumerate(self.header['signal_labels']):
                print(f"  {i}: {label}")
            
        except Exception as e:
            print(f"✗ Error loading EDF file: {e}")
            raise
    
    def extract_signals(self):
        """Extract all signals from EDF file."""
        print(f"\nExtracting signals...")
        
        signal_labels = self.edf.getSignalLabels()
        for i in range(self.edf.signals_in_file):
            label = signal_labels[i]
            signal = self.edf.readSignal(i)
            sample_rate = self.edf.getSampleFrequency(i)
            
            self.signals[label] = {
                'data': signal,
                'sample_rate': sample_rate,
                'unit': self.edf.getPhysicalDimension(i),
                'samples': len(signal)
            }
            
            print(f"  ✓ {label}: {len(signal)} samples @ {sample_rate} Hz ({self.signals[label]['unit']})")
        
        return self.signals
    
    def analyze_apnea_events(self):
        """Analyze apnea/hypopnea events from CPAP data."""
        print(f"\nAnalyzing respiratory events...")
        
        # Common CPAP event channels
        event_channels = [
            'Apnea', 'Hypopnea', 'RERA', 'Flow Limitation',
            'Central Apnea', 'Obstructive Apnea', 'Mixed Apnea',
            'Respiratory Event'
        ]
        
        events = {}
        
        for channel in event_channels:
            # Try to find matching channel (case-insensitive)
            for label in self.signals.keys():
                if channel.lower() in label.lower():
                    data = self.signals[label]['data']
                    
                    # Count events (non-zero values)
                    event_mask = data > 0
                    event_count = np.sum(event_mask)
                    
                    # Calculate event duration
                    sample_rate = self.signals[label]['sample_rate']
                    event_indices = np.where(event_mask)[0]
                    
                    if len(event_indices) > 0:
                        # Group consecutive events
                        event_groups = np.split(event_indices, np.where(np.diff(event_indices) > 1)[0] + 1)
                        
                        total_duration = sum(len(group) / sample_rate for group in event_groups)
                        avg_duration = total_duration / len(event_groups) if event_groups else 0
                        
                        events[label] = {
                            'count': len(event_groups),
                            'total_duration_seconds': total_duration,
                            'average_duration_seconds': avg_duration
                        }
        
        return events
    
    def calculate_ahi(self, events):
        """Calculate AHI (Apnea-Hypopnea Index)."""
        duration_hours = self.header['duration_seconds'] / 3600
        
        # Sum apnea and hypopnea events
        total_events = 0
        for label, data in events.items():
            if any(keyword in label.lower() for keyword in ['apnea', 'hypopnea']):
                total_events += data['count']
        
        ahi = total_events / duration_hours if duration_hours > 0 else 0
        
        return {
            'ahi': ahi,
            'total_events': total_events,
            'duration_hours': duration_hours,
            'severity': self._ahi_severity(ahi)
        }
    
    def _ahi_severity(self, ahi):
        """Determine AHI severity classification."""
        if ahi < 5:
            return 'Normal'
        elif ahi < 15:
            return 'Mild'
        elif ahi < 30:
            return 'Moderate'
        else:
            return 'Severe'
    
    def analyze_pressure(self):
        """Analyze CPAP pressure data."""
        print(f"\nAnalyzing pressure data...")
        
        pressure_channels = ['Pressure', 'CPAP Pressure', 'Mask Pressure', 'IPAP', 'EPAP']
        
        pressure_stats = {}
        
        for channel in pressure_channels:
            for label in self.signals.keys():
                if channel.lower() in label.lower():
                    data = self.signals[label]['data']
                    
                    pressure_stats[label] = {
                        'mean': float(np.mean(data)),
                        'median': float(np.median(data)),
                        'min': float(np.min(data)),
                        'max': float(np.max(data)),
                        'p95': float(np.percentile(data, 95)),
                        'std': float(np.std(data)),
                        'unit': self.signals[label]['unit']
                    }
        
        return pressure_stats
    
    def analyze_leaks(self):
        """Analyze mask leak data."""
        print(f"\nAnalyzing leak data...")
        
        leak_channels = ['Leak', 'Mask Leak', 'Total Leak']
        
        leak_stats = {}
        
        for channel in leak_channels:
            for label in self.signals.keys():
                if channel.lower() in label.lower():
                    data = self.signals[label]['data']
                    
                    # Leaks are typically considered high if > 24 L/min
                    high_leak_threshold = 24
                    high_leak_percentage = (np.sum(data > high_leak_threshold) / len(data)) * 100
                    
                    leak_stats[label] = {
                        'mean': float(np.mean(data)),
                        'median': float(np.median(data)),
                        'p95': float(np.percentile(data, 95)),
                        'max': float(np.max(data)),
                        'high_leak_percentage': float(high_leak_percentage),
                        'unit': self.signals[label]['unit']
                    }
        
        return leak_stats
    
    def generate_report(self):
        """Generate comprehensive CPAP analysis report."""
        print("\n" + "="*70)
        print("CPAP DATA ANALYSIS REPORT")
        print("="*70)
        
        # Extract all data
        self.extract_signals()
        
        # Analyze events
        events = self.analyze_apnea_events()
        ahi_data = self.calculate_ahi(events)
        pressure_stats = self.analyze_pressure()
        leak_stats = self.analyze_leaks()
        
        # Print report
        print(f"\nSESSION INFORMATION:")
        print(f"  Date: {self.header['recording_date']}")
        print(f"  Duration: {self.header['duration_seconds'] / 3600:.1f} hours")
        
        print(f"\nAHI (APNEA-HYPOPNEA INDEX):")
        print(f"  AHI: {ahi_data['ahi']:.1f} events/hour")
        print(f"  Severity: {ahi_data['severity']}")
        print(f"  Total events: {ahi_data['total_events']}")
        
        if events:
            print(f"\nRESPIRATORY EVENTS:")
            for label, data in events.items():
                print(f"  {label}:")
                print(f"    Count: {data['count']}")
                print(f"    Avg duration: {data['average_duration_seconds']:.1f} seconds")
        
        if pressure_stats:
            print(f"\nPRESSURE STATISTICS:")
            for label, stats in pressure_stats.items():
                print(f"  {label}:")
                print(f"    Mean: {stats['mean']:.1f} {stats['unit']}")
                print(f"    Range: {stats['min']:.1f} - {stats['max']:.1f} {stats['unit']}")
                print(f"    95th percentile: {stats['p95']:.1f} {stats['unit']}")
        
        if leak_stats:
            print(f"\nLEAK STATISTICS:")
            for label, stats in leak_stats.items():
                print(f"  {label}:")
                print(f"    Median: {stats['median']:.1f} {stats['unit']}")
                print(f"    95th percentile: {stats['p95']:.1f} {stats['unit']}")
                print(f"    High leak time: {stats['high_leak_percentage']:.1f}%")
        
        print("\n" + "="*70)
        
        # Save report
        report = {
            'session_info': self.header,
            'ahi': ahi_data,
            'events': events,
            'pressure': pressure_stats,
            'leaks': leak_stats
        }
        
        return report
    
    def plot_cpap_data(self, save_path=None):
        """Create visualization of CPAP data."""
        if not self.signals:
            self.extract_signals()
        
        # Create figure
        fig = plt.figure(figsize=(16, 10))
        fig.suptitle(f'CPAP Analysis: {self.edf_file.name}', fontsize=16, fontweight='bold')
        
        plot_count = 0
        
        # Plot pressure
        pressure_signals = [label for label in self.signals.keys() if 'pressure' in label.lower()]
        if pressure_signals:
            plot_count += 1
            ax = plt.subplot(4, 1, plot_count)
            for label in pressure_signals[:2]:  # Max 2 pressure channels
                signal = self.signals[label]
                time = np.arange(len(signal['data'])) / signal['sample_rate'] / 3600  # hours
                ax.plot(time, signal['data'], label=label, linewidth=0.5)
            ax.set_ylabel(f"Pressure ({self.signals[pressure_signals[0]]['unit']})")
            ax.set_xlabel('Time (hours)')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # Plot flow
        flow_signals = [label for label in self.signals.keys() if 'flow' in label.lower()]
        if flow_signals:
            plot_count += 1
            ax = plt.subplot(4, 1, plot_count)
            signal = self.signals[flow_signals[0]]
            time = np.arange(len(signal['data'])) / signal['sample_rate'] / 3600
            ax.plot(time, signal['data'], linewidth=0.5, color='green')
            ax.set_ylabel(f"{flow_signals[0]} ({signal['unit']})")
            ax.set_xlabel('Time (hours)')
            ax.grid(True, alpha=0.3)
        
        # Plot leaks
        leak_signals = [label for label in self.signals.keys() if 'leak' in label.lower()]
        if leak_signals:
            plot_count += 1
            ax = plt.subplot(4, 1, plot_count)
            signal = self.signals[leak_signals[0]]
            time = np.arange(len(signal['data'])) / signal['sample_rate'] / 3600
            ax.plot(time, signal['data'], linewidth=0.5, color='red')
            ax.axhline(y=24, color='orange', linestyle='--', label='High leak threshold')
            ax.set_ylabel(f"{leak_signals[0]} ({signal['unit']})")
            ax.set_xlabel('Time (hours)')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        # Plot events
        event_signals = [label for label in self.signals.keys() if any(kw in label.lower() for kw in ['apnea', 'hypopnea', 'event'])]
        if event_signals:
            plot_count += 1
            ax = plt.subplot(4, 1, plot_count)
            for label in event_signals[:3]:  # Max 3 event types
                signal = self.signals[label]
                time = np.arange(len(signal['data'])) / signal['sample_rate'] / 3600
                ax.plot(time, signal['data'], label=label, linewidth=1, alpha=0.7)
            ax.set_ylabel('Events')
            ax.set_xlabel('Time (hours)')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = self.edf_file.with_suffix('.cpap_analysis.png')
        
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\n✓ Plot saved to: {save_path}")
        
        return save_path
    
    def export_to_csv(self, output_path=None):
        """Export CPAP data to CSV format."""
        if not self.signals:
            self.extract_signals()
        
        # Find the signal with the most samples (typically the main flow/pressure signal)
        max_samples = max(sig['samples'] for sig in self.signals.values())
        
        # Create DataFrame
        df_dict = {}
        
        for label, signal in self.signals.items():
            data = signal['data']
            sample_rate = signal['sample_rate']
            
            # Resample to match longest signal if necessary
            if len(data) < max_samples:
                # Simple upsampling by repetition
                indices = np.linspace(0, len(data) - 1, max_samples).astype(int)
                data = data[indices]
            
            df_dict[label] = data
        
        # Add time column
        df_dict['time_seconds'] = np.arange(max_samples) / self.signals[list(self.signals.keys())[0]]['sample_rate']
        
        df = pd.DataFrame(df_dict)
        
        if output_path is None:
            output_path = self.edf_file.with_suffix('.csv')
        
        df.to_csv(output_path, index=False)
        print(f"\n✓ CSV exported to: {output_path}")
        
        return output_path
    
    def close(self):
        """Close EDF file."""
        if self.edf:
            self.edf.close()


def main():
    """Main function."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python cpap_analyzer.py <edf_file>")
        print("\nExample:")
        print("  python cpap_analyzer.py recordings/cpap_20231206.edf")
        return
    
    edf_file = sys.argv[1]
    
    try:
        analyzer = CPAPAnalyzer(edf_file)
        
        # Generate report
        report = analyzer.generate_report()
        
        # Save report
        report_path = Path(edf_file).with_suffix('.cpap_report.json')
        with open(report_path, 'w') as f:
            # Convert datetime objects to strings for JSON
            report_copy = report.copy()
            if 'session_info' in report_copy and 'recording_date' in report_copy['session_info']:
                report_copy['session_info']['recording_date'] = str(report_copy['session_info']['recording_date'])
            json.dump(report_copy, f, indent=2)
        print(f"\n✓ Report saved to: {report_path}")
        
        # Create visualization
        analyzer.plot_cpap_data()
        
        # Export to CSV
        analyzer.export_to_csv()
        
        # Close
        analyzer.close()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
