"""
Show comprehensive statistics from Muse + Garmin synced session
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

def show_statistics(csv_file):
    """Display comprehensive statistics from synced data."""
    
    # Load synced data
    df = pd.read_csv(csv_file)
    
    print('='*70)
    print('MUSE + GARMIN SESSION STATISTICS')
    print('='*70)
    
    # Session info
    print(f'\n📊 SESSION OVERVIEW')
    print(f'  Duration: {df["elapsed_time"].max():.1f} seconds ({df["elapsed_time"].max()/60:.1f} minutes)')
    print(f'  Total Samples: {len(df):,}')
    print(f'  Sampling Rate: {len(df)/df["elapsed_time"].max():.1f} Hz')
    
    # EEG Channel Statistics
    print(f'\n🧠 EEG BRAIN WAVE STATISTICS (µV)')
    print(f'  {"Channel":<12} {"Mean":>8} {"Std":>8} {"Min":>8} {"Max":>8} {"Range":>8}')
    print(f'  {"="*60}')
    for ch in ['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']:
        mean = df[ch].mean()
        std = df[ch].std()
        min_val = df[ch].min()
        max_val = df[ch].max()
        range_val = max_val - min_val
        print(f'  {ch.upper():<12} {mean:>8.2f} {std:>8.2f} {min_val:>8.2f} {max_val:>8.2f} {range_val:>8.2f}')
    
    # Calculate signal quality (lower std = better)
    avg_std = df[['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']].std().mean()
    quality = 'Excellent' if avg_std < 50 else 'Good' if avg_std < 100 else 'Fair' if avg_std < 150 else 'Poor'
    print(f'\n  Signal Quality: {quality} (avg std: {avg_std:.1f} µV)')
    
    # Garmin Heart Rate
    if 'heart_rate_bpm' in df.columns:
        hr_valid = df['heart_rate_bpm'].notna()
        if hr_valid.sum() > 0:
            print(f'\n❤️  GARMIN HEART RATE')
            print(f'  Valid Samples: {hr_valid.sum()}')
            print(f'  Average: {df.loc[hr_valid, "heart_rate_bpm"].mean():.1f} bpm')
            print(f'  Min: {df.loc[hr_valid, "heart_rate_bpm"].min():.0f} bpm')
            print(f'  Max: {df.loc[hr_valid, "heart_rate_bpm"].max():.0f} bpm')
            print(f'  Range: {df.loc[hr_valid, "heart_rate_bpm"].max() - df.loc[hr_valid, "heart_rate_bpm"].min():.0f} bpm')
            
            if hr_valid.sum() > 1:
                trend = "Increasing" if df.loc[hr_valid, "heart_rate_bpm"].iloc[-1] > df.loc[hr_valid, "heart_rate_bpm"].iloc[0] else "Decreasing"
                print(f'  Trend: {trend}')
    
    # Garmin Stress
    if 'stress_level' in df.columns:
        stress_valid = df['stress_level'].notna()
        if stress_valid.sum() > 0:
            print(f'\n😰 GARMIN STRESS LEVEL')
            print(f'  Valid Samples: {stress_valid.sum()}')
            print(f'  Average: {df.loc[stress_valid, "stress_level"].mean():.1f}')
            print(f'  Min: {df.loc[stress_valid, "stress_level"].min():.0f}')
            print(f'  Max: {df.loc[stress_valid, "stress_level"].max():.0f}')
            
            # Stress interpretation
            avg_stress = df.loc[stress_valid, "stress_level"].mean()
            if avg_stress < 25:
                interpretation = "Very Relaxed"
            elif avg_stress < 50:
                interpretation = "Relaxed"
            elif avg_stress < 75:
                interpretation = "Moderate Stress"
            else:
                interpretation = "High Stress"
            print(f'  Interpretation: {interpretation}')
    
    # Motion Analysis
    print(f'\n🏃 HEAD MOTION STATISTICS')
    gyro_magnitude = np.sqrt(df['gyro_x']**2 + df['gyro_y']**2 + df['gyro_z']**2)
    acc_magnitude = np.sqrt(df['acc_x']**2 + df['acc_y']**2 + df['acc_z']**2)
    
    print(f'  Gyroscope (°/s):')
    print(f'    Mean Movement: {gyro_magnitude.mean():.2f}')
    print(f'    Max Movement: {gyro_magnitude.max():.2f}')
    still_pct = (gyro_magnitude < 10).sum()/len(gyro_magnitude)*100
    print(f'    Still (<10°/s): {still_pct:.1f}%')
    
    print(f'  Accelerometer (g):')
    print(f'    Mean: {acc_magnitude.mean():.3f}')
    stillness_score = max(0, 100 - (gyro_magnitude.mean()/10 * 100))
    print(f'    Stillness Score: {stillness_score:.1f}%')
    
    # PPG Analysis
    ppg_valid = df['ppg_avg'].notna()
    if ppg_valid.sum() > 0:
        print(f'\n💓 PPG (PHOTOPLETHYSMOGRAPHY)')
        print(f'  Mean: {df.loc[ppg_valid, "ppg_avg"].mean():.2f}')
        print(f'  Std: {df.loc[ppg_valid, "ppg_avg"].std():.2f}')
        print(f'  Range: {df.loc[ppg_valid, "ppg_avg"].max() - df.loc[ppg_valid, "ppg_avg"].min():.2f}')
    
    # Correlation Analysis (if both HR and EEG available)
    if 'heart_rate_bpm' in df.columns and hr_valid.sum() > 2:
        print(f'\n🔗 EEG-HEART RATE CORRELATIONS')
        for ch in ['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']:
            # Get samples where HR is available
            valid_indices = hr_valid
            if valid_indices.sum() > 2:
                corr = df.loc[valid_indices, [ch, 'heart_rate_bpm']].corr().iloc[0, 1]
                print(f'  {ch.upper()} ↔ HR: {corr:+.3f}', end='')
                if abs(corr) > 0.7:
                    print(' (Strong)')
                elif abs(corr) > 0.4:
                    print(' (Moderate)')
                else:
                    print(' (Weak)')
    
    print('\n' + '='*70)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python show_session_stats.py <synced_csv_file>")
        print("\nExample:")
        print("  python show_session_stats.py recordings/2025-12-18/muse_mindmonitor_*_garmin_sync.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    if not Path(csv_file).exists():
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)
    
    show_statistics(csv_file)
