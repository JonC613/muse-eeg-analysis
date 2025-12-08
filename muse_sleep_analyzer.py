"""
Muse S Sleep Analyzer
Analyzes sleep stages and quality from overnight EEG recordings
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json


class MuseSleepAnalyzer:
    """Analyze sleep stages from Muse S overnight recordings."""
    
    def __init__(self, csv_file):
        """Initialize with overnight recording CSV."""
        self.csv_file = Path(csv_file)
        print(f"Loading sleep data from: {self.csv_file}")
        self.df = pd.read_csv(csv_file)
        
        # Handle both old and new timestamp formats
        if 'elapsed_time' in self.df.columns:
            time_col = 'elapsed_time'
        elif 'timestamp' in self.df.columns:
            time_col = 'timestamp'
        else:
            raise ValueError("No timestamp column found (need 'elapsed_time' or 'timestamp')")
        
        self.duration_hours = self.df[time_col].max() / 3600
        print(f"✓ Loaded {len(self.df)} samples ({self.duration_hours:.1f} hours)")
        
        # Sleep stage thresholds (based on EEG research)
        self.stage_thresholds = {
            'deep_sleep': {'delta_min': 50, 'movement_max': 5},
            'light_sleep': {'delta_min': 30, 'delta_max': 50, 'movement_max': 10},
            'rem_sleep': {'theta_min': 30, 'alpha_min': 10, 'movement_max': 15},
            'awake': {'beta_min': 15, 'movement_min': 10}
        }
    
    def _calculate_band_powers_windowed(self, window_seconds=30, fs=256):
        """Calculate band powers in time windows."""
        eeg_data = self.df['eeg_af7'].dropna().values
        
        # Handle both timestamp formats
        if 'elapsed_time' in self.df.columns:
            time_col = 'elapsed_time'
        else:
            time_col = 'timestamp'
        
        window_size = int(window_seconds * (len(eeg_data) / self.df[time_col].max()))
        hop_size = window_size // 2  # 50% overlap
        
        bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'beta': (13, 30),
            'gamma': (30, 50)
        }
        
        results = []
        
        for i in range(0, len(eeg_data) - window_size, hop_size):
            segment = eeg_data[i:i+window_size]
            time_idx = int(i + window_size // 2)
            
            if time_idx >= len(self.df):
                break
            
            # Get timestamp (handle both formats)
            if 'elapsed_time' in self.df.columns:
                timestamp = self.df.iloc[time_idx]['elapsed_time']
            else:
                timestamp = self.df.iloc[time_idx]['timestamp']
            
            # FFT analysis
            fft_vals = np.fft.rfft(segment)
            fft_freq = np.fft.rfftfreq(window_size, 1.0/fs)
            fft_power = np.abs(fft_vals) ** 2
            
            # Calculate band powers
            band_powers = {}
            for band_name, (low, high) in bands.items():
                idx = np.where((fft_freq >= low) & (fft_freq <= high))
                power = np.mean(fft_power[idx]) if len(idx[0]) > 0 else 0
                band_powers[band_name] = power
            
            # Normalize to percentages
            total_power = sum(band_powers.values())
            if total_power > 0:
                band_powers = {k: (v/total_power)*100 for k, v in band_powers.items()}
            
            # Calculate movement
            movement_idx = min(time_idx, len(self.df) - 1)
            movement = np.sqrt(
                self.df.iloc[movement_idx]['gyro_x']**2 +
                self.df.iloc[movement_idx]['gyro_y']**2 +
                self.df.iloc[movement_idx]['gyro_z']**2
            )
            
            results.append({
                'timestamp': timestamp,
                **band_powers,
                'movement': movement
            })
        
        return pd.DataFrame(results)
    
    def classify_sleep_stages(self):
        """Classify sleep stages based on EEG patterns and movement."""
        print("\nAnalyzing sleep stages...")
        
        # Get windowed band powers
        windowed_df = self._calculate_band_powers_windowed(window_seconds=30)
        
        stages = []
        
        for _, row in windowed_df.iterrows():
            delta = row['delta']
            theta = row['theta']
            alpha = row['alpha']
            beta = row['beta']
            movement = row['movement']
            
            # Classify sleep stage
            if movement > 20 or beta > 25:
                stage = 'Awake'
            elif delta > 50 and movement < 5:
                stage = 'Deep Sleep'
            elif delta > 30 and theta > 20 and movement < 10:
                stage = 'Light Sleep'
            elif theta > 30 and alpha > 10 and movement < 15:
                stage = 'REM Sleep'
            else:
                stage = 'Light Sleep'  # Default
            
            stages.append(stage)
        
        windowed_df['sleep_stage'] = stages
        
        return windowed_df
    
    def calculate_sleep_metrics(self, stages_df):
        """Calculate sleep quality metrics."""
        total_time = self.duration_hours * 60  # minutes
        
        # Time in each stage (minutes)
        stage_counts = stages_df['sleep_stage'].value_counts()
        window_duration = (stages_df['timestamp'].iloc[1] - stages_df['timestamp'].iloc[0]) / 60
        
        metrics = {}
        for stage in ['Awake', 'Light Sleep', 'Deep Sleep', 'REM Sleep']:
            count = stage_counts.get(stage, 0)
            minutes = count * window_duration
            metrics[stage] = {
                'minutes': minutes,
                'percentage': (minutes / total_time) * 100
            }
        
        # Sleep efficiency
        sleep_time = sum(v['minutes'] for k, v in metrics.items() if k != 'Awake')
        metrics['sleep_efficiency'] = (sleep_time / total_time) * 100
        
        # Sleep latency (time to first sleep)
        first_sleep_idx = stages_df[stages_df['sleep_stage'] != 'Awake'].index
        if len(first_sleep_idx) > 0:
            metrics['sleep_latency_minutes'] = stages_df.iloc[first_sleep_idx[0]]['timestamp'] / 60
        else:
            metrics['sleep_latency_minutes'] = 0
        
        # Wake after sleep onset (WASO)
        if len(first_sleep_idx) > 0:
            after_sleep_onset = stages_df.iloc[first_sleep_idx[0]:]
            waso_count = len(after_sleep_onset[after_sleep_onset['sleep_stage'] == 'Awake'])
            metrics['waso_minutes'] = waso_count * window_duration
        else:
            metrics['waso_minutes'] = 0
        
        # REM latency (time to first REM)
        first_rem_idx = stages_df[stages_df['sleep_stage'] == 'REM Sleep'].index
        if len(first_rem_idx) > 0:
            metrics['rem_latency_minutes'] = stages_df.iloc[first_rem_idx[0]]['timestamp'] / 60
        else:
            metrics['rem_latency_minutes'] = 0.0  # Default to 0 instead of None
        
        # Deep sleep percentage (quality indicator)
        metrics['deep_sleep_quality'] = metrics['Deep Sleep']['percentage']
        
        return metrics
    
    def plot_sleep_analysis(self, stages_df, metrics, save_path=None):
        """Create comprehensive sleep analysis visualization."""
        fig = plt.figure(figsize=(16, 12))
        fig.suptitle(f'Sleep Analysis: {self.csv_file.name}', 
                    fontsize=16, fontweight='bold')
        
        # Color mapping
        stage_colors = {
            'Awake': '#e74c3c',
            'REM Sleep': '#9b59b6',
            'Light Sleep': '#3498db',
            'Deep Sleep': '#2c3e50'
        }
        
        # 1. Hypnogram (sleep stages over time)
        ax1 = plt.subplot(4, 2, (1, 2))
        ax1.set_title('Hypnogram (Sleep Stages Over Time)', fontweight='bold', fontsize=12)
        
        # Convert stages to numeric for plotting
        stage_mapping = {'Awake': 3, 'REM Sleep': 2, 'Light Sleep': 1, 'Deep Sleep': 0}
        stages_df['stage_numeric'] = stages_df['sleep_stage'].map(stage_mapping)
        
        # Plot as stepped area
        hours = stages_df['timestamp'] / 3600
        ax1.fill_between(hours, 0, stages_df['stage_numeric'], 
                        step='post', alpha=0.7, color='#3498db')
        
        # Color segments by stage
        for stage, color in stage_colors.items():
            mask = stages_df['sleep_stage'] == stage
            if mask.any():
                ax1.fill_between(hours, 0, stages_df['stage_numeric'],
                                where=mask, step='post', alpha=0.8, 
                                color=color, label=stage)
        
        ax1.set_yticks([0, 1, 2, 3])
        ax1.set_yticklabels(['Deep', 'Light', 'REM', 'Awake'])
        ax1.set_xlabel('Time (hours)')
        ax1.set_ylabel('Sleep Stage')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(0, self.duration_hours)
        
        # 2. Sleep stage distribution (pie chart)
        ax2 = plt.subplot(4, 2, 3)
        ax2.set_title('Sleep Stage Distribution', fontweight='bold', fontsize=12)
        
        stage_counts = stages_df['sleep_stage'].value_counts()
        colors = [stage_colors[stage] for stage in stage_counts.index]
        ax2.pie(stage_counts, labels=stage_counts.index, autopct='%1.1f%%',
               colors=colors, startangle=90)
        
        # 3. Brain wave activity over time
        ax3 = plt.subplot(4, 2, 4)
        ax3.set_title('Brain Wave Activity', fontweight='bold', fontsize=12)
        
        ax3.plot(hours, stages_df['delta'], label='Delta (Deep Sleep)', 
                linewidth=2, color='#2c3e50')
        ax3.plot(hours, stages_df['theta'], label='Theta (REM)', 
                linewidth=2, color='#9b59b6')
        ax3.plot(hours, stages_df['alpha'], label='Alpha (Relaxed)', 
                linewidth=2, color='#3498db')
        ax3.plot(hours, stages_df['beta'], label='Beta (Alert)', 
                linewidth=2, color='#e74c3c')
        
        ax3.set_xlabel('Time (hours)')
        ax3.set_ylabel('Power (%)')
        ax3.legend(fontsize=8)
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim(0, self.duration_hours)
        
        # 4. Movement tracking
        ax4 = plt.subplot(4, 2, 5)
        ax4.set_title('Movement During Sleep', fontweight='bold', fontsize=12)
        
        ax4.fill_between(hours, 0, stages_df['movement'], alpha=0.6, color='#e67e22')
        ax4.axhline(y=10, color='red', linestyle='--', alpha=0.5, label='High movement threshold')
        ax4.set_xlabel('Time (hours)')
        ax4.set_ylabel('Movement (°/s)')
        ax4.legend(fontsize=8)
        ax4.grid(True, alpha=0.3)
        ax4.set_xlim(0, self.duration_hours)
        
        # 5. Sleep cycles
        ax5 = plt.subplot(4, 2, 6)
        ax5.set_title('Sleep Cycles', fontweight='bold', fontsize=12)
        
        # Identify sleep cycles (typically ~90 minutes)
        cycle_duration = 90  # minutes
        num_cycles = int(self.duration_hours * 60 / cycle_duration)
        
        for i in range(num_cycles):
            start = i * cycle_duration / 60
            ax5.axvspan(start, start + cycle_duration/60, 
                       alpha=0.1 if i % 2 == 0 else 0.2, color='blue')
            ax5.text(start + cycle_duration/120, ax5.get_ylim()[1] * 0.9,
                    f'Cycle {i+1}', fontsize=8, ha='center')
        
        # Overlay deep sleep periods
        deep_mask = stages_df['sleep_stage'] == 'Deep Sleep'
        ax5.fill_between(hours, 0, 1, where=deep_mask, 
                        step='post', alpha=0.6, color='#2c3e50')
        
        ax5.set_xlabel('Time (hours)')
        ax5.set_ylabel('Deep Sleep')
        ax5.set_xlim(0, self.duration_hours)
        ax5.set_ylim(0, 1.1)
        ax5.grid(True, alpha=0.3)
        
        # 6. Sleep metrics summary
        ax6 = plt.subplot(4, 2, (7, 8))
        ax6.axis('off')
        ax6.set_title('Sleep Quality Metrics', fontweight='bold', fontsize=12)
        
        summary_text = f"""
        SLEEP SUMMARY
        {'='*60}
        
        Total Recording Time:        {self.duration_hours:.1f} hours ({self.duration_hours*60:.0f} minutes)
        Sleep Efficiency:            {metrics['sleep_efficiency']:.1f}%
        
        SLEEP STAGES:
          Deep Sleep:                {metrics['Deep Sleep']['minutes']:.0f} min ({metrics['Deep Sleep']['percentage']:.1f}%)
          Light Sleep:               {metrics['Light Sleep']['minutes']:.0f} min ({metrics['Light Sleep']['percentage']:.1f}%)
          REM Sleep:                 {metrics['REM Sleep']['minutes']:.0f} min ({metrics['REM Sleep']['percentage']:.1f}%)
          Awake:                     {metrics['Awake']['minutes']:.0f} min ({metrics['Awake']['percentage']:.1f}%)
        
        SLEEP QUALITY INDICATORS:
          Sleep Latency:             {metrics['sleep_latency_minutes']:.1f} minutes
          REM Latency:               {metrics['rem_latency_minutes']:.1f} minutes
          Wake After Sleep Onset:    {metrics['waso_minutes']:.1f} minutes
          Deep Sleep Quality:        {metrics['deep_sleep_quality']:.1f}% {'✓ Good' if metrics['deep_sleep_quality'] > 15 else '⚠ Low'}
        
        RECOMMENDATIONS:
        """
        
        # Add recommendations
        if metrics['sleep_efficiency'] < 85:
            summary_text += "  ⚠ Sleep efficiency below 85% - consider sleep hygiene improvements\n"
        if metrics['deep_sleep_quality'] < 15:
            summary_text += "  ⚠ Low deep sleep - avoid caffeine/alcohol before bed\n"
        if metrics['waso_minutes'] > 30:
            summary_text += "  ⚠ Frequent awakenings - check environment (noise, temperature)\n"
        if metrics['sleep_latency_minutes'] > 30:
            summary_text += "  ⚠ Long sleep onset - establish bedtime routine\n"
        if metrics['REM Sleep']['percentage'] < 20:
            summary_text += "  ⚠ Low REM sleep - ensure adequate total sleep time\n"
        
        if all([
            metrics['sleep_efficiency'] >= 85,
            metrics['deep_sleep_quality'] >= 15,
            metrics['waso_minutes'] <= 30,
            metrics['REM Sleep']['percentage'] >= 20
        ]):
            summary_text += "  ✓ Excellent sleep quality - maintain current habits!\n"
        
        ax6.text(0.05, 0.95, summary_text, fontsize=9, verticalalignment='top',
                fontfamily='monospace', transform=ax6.transAxes)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✓ Sleep analysis saved to: {save_path}")
        
        plt.show()
    
    def export_report(self, stages_df, metrics):
        """Export detailed sleep report."""
        output_file = self.csv_file.with_suffix('.sleep_report.json')
        
        report = {
            'recording': {
                'filename': self.csv_file.name,
                'duration_hours': float(self.duration_hours),
                'total_samples': len(self.df)
            },
            'metrics': {
                'sleep_efficiency': float(metrics['sleep_efficiency']),
                'sleep_latency_minutes': float(metrics['sleep_latency_minutes']),
                'rem_latency_minutes': float(metrics['rem_latency_minutes']) if metrics['rem_latency_minutes'] else None,
                'waso_minutes': float(metrics['waso_minutes']),
                'deep_sleep_quality': float(metrics['deep_sleep_quality'])
            },
            'stages': {
                stage: {
                    'minutes': float(data['minutes']),
                    'percentage': float(data['percentage'])
                }
                for stage, data in metrics.items() 
                if stage in ['Awake', 'Light Sleep', 'Deep Sleep', 'REM Sleep']
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✓ Sleep report exported to: {output_file}")
        return output_file


def main():
    """Main function."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python muse_sleep_analyzer.py <overnight_recording.csv>")
        print("\nExample:")
        print("  python muse_sleep_analyzer.py recordings\\muse_sleep_20231207_080000.csv")
        return
    
    csv_file = sys.argv[1]
    
    # Initialize analyzer
    analyzer = MuseSleepAnalyzer(csv_file)
    
    # Classify sleep stages
    stages_df = analyzer.classify_sleep_stages()
    
    # Calculate metrics
    metrics = analyzer.calculate_sleep_metrics(stages_df)
    
    # Plot analysis
    plot_path = Path(csv_file).with_suffix('.sleep_analysis.png')
    analyzer.plot_sleep_analysis(stages_df, metrics, save_path=plot_path)
    
    # Export report
    analyzer.export_report(stages_df, metrics)
    
    print("\n✓ Sleep analysis complete!")


if __name__ == "__main__":
    main()
