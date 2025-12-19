#!/usr/bin/env python3
"""
Compare cannabis study Session 1 (T+15) vs Session 2 (T+50) to track progression
"""
import pandas as pd
import numpy as np
from scipy import signal

def calculate_band_powers(data, fs=256):
    """Calculate EEG band powers using Welch method"""
    bands = {
        'Delta': (0.5, 4),
        'Theta': (4, 8),
        'Alpha': (8, 13),
        'Beta': (13, 30),
        'Gamma': (30, 50)
    }
    
    # Calculate PSD
    freqs, psd = signal.welch(data, fs, nperseg=512)
    
    # Calculate band powers
    band_powers = {}
    for band_name, (low, high) in bands.items():
        idx = np.logical_and(freqs >= low, freqs <= high)
        power = np.trapz(psd[idx], freqs[idx])
        band_powers[band_name] = power
    
    return band_powers

def analyze_session(filepath):
    """Analyze a single session and return metrics"""
    df = pd.read_csv(filepath)
    
    # Drop NaN values from EEG data
    df = df.dropna(subset=['eeg_af7', 'eeg_af8'])
    
    # Get time info
    duration = df['elapsed_time'].max() - df['elapsed_time'].min()
    
    # Calculate band powers for frontal channels (AF7, AF8)
    af7_powers = calculate_band_powers(df['eeg_af7'].values)
    af8_powers = calculate_band_powers(df['eeg_af8'].values)
    
    # Calculate ratios
    alpha_beta_af7 = af7_powers['Alpha'] / af7_powers['Beta']
    alpha_beta_af8 = af8_powers['Alpha'] / af8_powers['Beta']
    theta_beta_af7 = af7_powers['Theta'] / af7_powers['Beta']
    theta_beta_af8 = af8_powers['Theta'] / af8_powers['Beta']
    
    # Average across frontal channels
    alpha_beta = (alpha_beta_af7 + alpha_beta_af8) / 2
    theta_beta = (theta_beta_af7 + theta_beta_af8) / 2
    
    # Calculate percentages
    total_power_af7 = sum(af7_powers.values())
    total_power_af8 = sum(af8_powers.values())
    
    alpha_pct = ((af7_powers['Alpha'] + af8_powers['Alpha']) / 
                 (total_power_af7 + total_power_af8) * 100)
    theta_pct = ((af7_powers['Theta'] + af8_powers['Theta']) / 
                 (total_power_af7 + total_power_af8) * 100)
    beta_pct = ((af7_powers['Beta'] + af8_powers['Beta']) / 
                (total_power_af7 + total_power_af8) * 100)
    
    # Get physiological data (check for different column names)
    if 'garmin_heart_rate' in df.columns:
        hr_mean = df['garmin_heart_rate'].mean()
        hr_std = df['garmin_heart_rate'].std()
    elif 'heart_rate_bpm' in df.columns:
        hr_mean = df['heart_rate_bpm'].mean()
        hr_std = df['heart_rate_bpm'].std()
    else:
        hr_mean = None
        hr_std = None
    
    if 'garmin_stress' in df.columns:
        stress_mean = df['garmin_stress'].mean()
    elif 'stress' in df.columns:
        stress_mean = df['stress'].mean()
    else:
        stress_mean = None
    
    return {
        'duration': duration,
        'alpha_beta': alpha_beta,
        'theta_beta': theta_beta,
        'alpha_pct': alpha_pct,
        'theta_pct': theta_pct,
        'beta_pct': beta_pct,
        'hr_mean': hr_mean,
        'hr_std': hr_std,
        'stress_mean': stress_mean,
        'af7_powers': af7_powers,
        'af8_powers': af8_powers
    }

# Analyze both sessions
print("=" * 70)
print("CANNABIS STUDY: T+15 vs T+50 MINUTE COMPARISON")
print("=" * 70)

session1_path = "recordings/2025-12-18/muse_mindmonitor_20251218_221255_garmin_sync.csv"
session2_path = "recordings/2025-12-18/muse_mindmonitor_20251218_230708_garmin_sync.csv"

print("\n🔬 ANALYZING SESSION 1 (T+15 minutes)...")
s1 = analyze_session(session1_path)

print("🔬 ANALYZING SESSION 2 (T+50 minutes)...")
s2 = analyze_session(session2_path)

print("\n" + "=" * 70)
print("📊 EEG FREQUENCY BAND COMPARISON")
print("=" * 70)

print("\nAlpha/Beta Ratio (Higher = More Relaxation/Creativity):")
print(f"  T+15: {s1['alpha_beta']:.3f}")
print(f"  T+50: {s2['alpha_beta']:.3f}")
print(f"  Change: {(s2['alpha_beta'] - s1['alpha_beta']):.3f} ({((s2['alpha_beta']/s1['alpha_beta']-1)*100):+.1f}%)")

print("\nTheta/Beta Ratio (Higher = More Creative/Flow State):")
print(f"  T+15: {s1['theta_beta']:.3f}")
print(f"  T+50: {s2['theta_beta']:.3f}")
print(f"  Change: {(s2['theta_beta'] - s1['theta_beta']):.3f} ({((s2['theta_beta']/s1['theta_beta']-1)*100):+.1f}%)")

print("\nAlpha Power % (Relaxed Awareness):")
print(f"  T+15: {s1['alpha_pct']:.1f}%")
print(f"  T+50: {s2['alpha_pct']:.1f}%")
print(f"  Change: {(s2['alpha_pct'] - s1['alpha_pct']):+.1f}%")

print("\nTheta Power % (Meditation/Creativity):")
print(f"  T+15: {s1['theta_pct']:.1f}%")
print(f"  T+50: {s2['theta_pct']:.1f}%")
print(f"  Change: {(s2['theta_pct'] - s1['theta_pct']):+.1f}%")

print("\nBeta Power % (Analytical Thinking):")
print(f"  T+15: {s1['beta_pct']:.1f}%")
print(f"  T+50: {s2['beta_pct']:.1f}%")
print(f"  Change: {(s2['beta_pct'] - s1['beta_pct']):+.1f}%")

print("\n" + "=" * 70)
print("❤️  PHYSIOLOGICAL COMPARISON")
print("=" * 70)

if s1['hr_mean'] and s2['hr_mean']:
    print(f"\nHeart Rate (Average):")
    print(f"  T+15: {s1['hr_mean']:.1f} bpm")
    print(f"  T+50: {s2['hr_mean']:.1f} bpm")
    print(f"  Change: {(s2['hr_mean'] - s1['hr_mean']):+.1f} bpm ({((s2['hr_mean']/s1['hr_mean']-1)*100):+.1f}%)")
    
    print(f"\nHeart Rate Variability (Std Dev):")
    print(f"  T+15: {s1['hr_std']:.1f} bpm")
    print(f"  T+50: {s2['hr_std']:.1f} bpm")
    print(f"  Change: {(s2['hr_std'] - s1['hr_std']):+.1f} bpm")

if s1['stress_mean']:
    print(f"\nGarmin Stress Level:")
    print(f"  T+15: {s1['stress_mean']:.0f}")
    print(f"  T+50: N/A (no measurements)")

print("\n" + "=" * 70)
print("🎯 INTERPRETATION")
print("=" * 70)

# Calculate overall trends
alpha_beta_trend = "INCREASED ✅" if s2['alpha_beta'] > s1['alpha_beta'] else "DECREASED ❌"
theta_beta_trend = "INCREASED ✅" if s2['theta_beta'] > s1['theta_beta'] else "DECREASED ❌"
hr_trend = "DECREASED ✅" if (s2['hr_mean'] and s1['hr_mean'] and s2['hr_mean'] < s1['hr_mean']) else "INCREASED ❌" if (s2['hr_mean'] and s1['hr_mean']) else "N/A"

print(f"\nAlpha/Beta Ratio: {alpha_beta_trend}")
print(f"Theta/Beta Ratio: {theta_beta_trend}")
if s1['hr_mean'] and s2['hr_mean']:
    print(f"Heart Rate: {hr_trend}")

print("\n🧪 Cannabis Effect Timeline:")
if s2['alpha_beta'] > s1['alpha_beta'] and s2['theta_beta'] > s1['theta_beta']:
    print("  ✅ EEG shows progressive relaxation/creative state from T+15 to T+50")
    print("  ✅ Consistent with cannabis onset progressing to peak effects")
elif s2['alpha_beta'] < s1['alpha_beta']:
    print("  ⚠️  Alpha/Beta DECREASED over time (unexpected)")
    print("  ⚠️  May indicate tolerance, measurement variability, or other factors")
else:
    print("  🤷 Mixed signals - some markers increased, others decreased")

if s1['hr_mean'] and s2['hr_mean']:
    if s2['hr_mean'] < s1['hr_mean']:
        print(f"  ✅ Heart rate decreased by {abs(s2['hr_mean'] - s1['hr_mean']):.1f} bpm (relaxation)")
    else:
        print(f"  ⚠️  Heart rate still elevated at T+50 (physiological arousal)")

print("\n📋 RECOMMENDATION:")
print("  • Need baseline (T+0) for within-subject comparison")
print("  • Need T+30 and T+90 timepoints to map full onset curve")
print("  • Current 2-point comparison shows trend but limited context")
print("=" * 70)
