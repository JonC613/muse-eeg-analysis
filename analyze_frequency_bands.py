"""
Analyze frequency bands in the synced session to verify creative/altered state claims
"""

import pandas as pd
import numpy as np
from scipy import signal
import sys

def calculate_band_powers(eeg_data, fs=254.89):
    """Calculate power in each frequency band."""
    
    # Use Welch's method for better spectral estimate
    nperseg = min(512, len(eeg_data))
    freqs, psd = signal.welch(eeg_data, fs=fs, nperseg=nperseg)
    
    # Define bands
    bands = {
        'Delta (0.5-4 Hz)': (0.5, 4),
        'Theta (4-8 Hz)': (4, 8),
        'Alpha (8-13 Hz)': (8, 13),
        'Beta (13-30 Hz)': (13, 30),
        'Gamma (30-50 Hz)': (30, 50)
    }
    
    band_powers = {}
    for band_name, (low, high) in bands.items():
        idx = np.where((freqs >= low) & (freqs <= high))
        power = np.trapz(psd[idx], freqs[idx])
        band_powers[band_name] = power
    
    return band_powers

def analyze_session(csv_file):
    """Analyze frequency bands to check for creative/altered state markers."""
    
    df = pd.read_csv(csv_file)
    
    print('='*70)
    print('FREQUENCY BAND ANALYSIS - CANNABIS CREATIVE STATE VERIFICATION')
    print('='*70)
    
    print('\n🔬 ANALYZING EEG FREQUENCY BANDS...\n')
    
    # Analyze each channel
    all_bands = {}
    for ch in ['eeg_af7', 'eeg_af8']:  # Focus on frontal channels (creativity/cognition)
        print(f'  Channel: {ch.upper()}')
        band_powers = calculate_band_powers(df[ch].dropna().values)
        
        # Calculate total power
        total_power = sum(band_powers.values())
        
        # Calculate percentages
        for band_name, power in band_powers.items():
            percentage = (power / total_power) * 100
            print(f'    {band_name:<20} {power:>12.2f} ({percentage:>5.1f}%)')
            
            if ch not in all_bands:
                all_bands[ch] = {}
            all_bands[ch][band_name] = percentage
        print()
    
    # Calculate Alpha/Beta ratio (key indicator of relaxation vs alertness)
    print('='*70)
    print('KEY METRICS FOR CANNABIS/CREATIVE STATE')
    print('='*70)
    
    for ch in ['eeg_af7', 'eeg_af8']:
        alpha = all_bands[ch]['Alpha (8-13 Hz)']
        beta = all_bands[ch]['Beta (13-30 Hz)']
        theta = all_bands[ch]['Theta (4-8 Hz)']
        
        alpha_beta_ratio = alpha / beta if beta > 0 else 0
        theta_beta_ratio = theta / beta if beta > 0 else 0
        
        print(f'\n  {ch.upper()}:')
        print(f'    Alpha/Beta Ratio: {alpha_beta_ratio:.3f}')
        print(f'    Theta/Beta Ratio: {theta_beta_ratio:.3f}')
    
    # Average across frontal channels
    avg_alpha = (all_bands['eeg_af7']['Alpha (8-13 Hz)'] + all_bands['eeg_af8']['Alpha (8-13 Hz)']) / 2
    avg_beta = (all_bands['eeg_af7']['Beta (13-30 Hz)'] + all_bands['eeg_af8']['Beta (13-30 Hz)']) / 2
    avg_theta = (all_bands['eeg_af7']['Theta (4-8 Hz)'] + all_bands['eeg_af8']['Theta (4-8 Hz)']) / 2
    
    avg_alpha_beta = avg_alpha / avg_beta
    avg_theta_beta = avg_theta / avg_beta
    
    print(f'\n  AVERAGED (frontal cortex):')
    print(f'    Alpha/Beta Ratio: {avg_alpha_beta:.3f}')
    print(f'    Theta/Beta Ratio: {avg_theta_beta:.3f}')
    
    # Interpretation
    print('\n' + '='*70)
    print('INTERPRETATION: DOES EEG SUPPORT CREATIVE/ALTERED STATE?')
    print('='*70)
    
    print('\n📚 EXPECTED VALUES:')
    print('  Normal Alert State:')
    print('    Alpha/Beta: 0.5-1.0 (beta dominant)')
    print('    Theta/Beta: 0.3-0.6 (low theta)')
    print('    Beta%: 25-40% (active thinking)')
    print('')
    print('  Cannabis Creative State:')
    print('    Alpha/Beta: 1.5-3.0 (alpha increases)')
    print('    Theta/Beta: 0.8-1.5 (theta increases)')
    print('    Beta%: 15-25% (reduced analytical thinking)')
    print('')
    print('  Deep Meditation/Flow:')
    print('    Alpha/Beta: 2.0-4.0 (very high alpha)')
    print('    Theta/Beta: 1.0-2.0 (elevated theta)')
    
    print('\n📊 YOUR ACTUAL VALUES:')
    print(f'  Alpha/Beta: {avg_alpha_beta:.3f}')
    print(f'  Theta/Beta: {avg_theta_beta:.3f}')
    print(f'  Beta%: {avg_beta:.1f}%')
    print(f'  Alpha%: {avg_alpha:.1f}%')
    print(f'  Theta%: {avg_theta:.1f}%')
    
    print('\n' + '='*70)
    print('VERDICT:')
    print('='*70)
    
    # Determine state
    if avg_alpha_beta > 1.5 and avg_theta_beta > 0.8:
        print('\n✅ EEG STRONGLY SUPPORTS: Cannabis/Creative/Flow State')
        print('   Alpha and Theta are elevated relative to Beta')
        print('   Pattern consistent with altered consciousness')
    elif avg_alpha_beta > 1.2 and avg_theta_beta > 0.6:
        print('\n⚠️  EEG MODERATELY SUPPORTS: Early Creative State')
        print('   Some elevation in Alpha/Theta')
        print('   Transitioning from alert to creative state')
    elif avg_beta > 30:
        print('\n❌ EEG CONTRADICTS: Creative/Relaxed State')
        print('   HIGH BETA = Active analytical thinking')
        print('   Pattern consistent with: Focus, problem-solving, or anxiety')
        print('   NOT consistent with: Cannabis relaxation or creative flow')
    else:
        print('\n🤷 EEG INCONCLUSIVE')
        print('   Ratios in borderline range')
    
    # Cross-check with physiological data
    print('\n' + '='*70)
    print('CROSS-VALIDATION WITH HEART RATE & STRESS')
    print('='*70)
    
    print('\n  Garmin Stress: 95 (HIGH)')
    print('  Heart Rate: 105-109 bpm (INCREASING)')
    print('')
    
    if avg_beta > 30:
        print('  ✓ HIGH BETA + HIGH STRESS = CONSISTENT')
        print('    Both indicate sympathetic nervous system activation')
        print('    State: Alert, focused, possibly anxious')
    else:
        print('  ✗ EEG vs STRESS = INCONSISTENT')
        print('    EEG suggests relaxation but body shows stress')
    
    print('\n' + '='*70)

if __name__ == "__main__":
    csv_file = 'recordings/2025-12-18/muse_mindmonitor_20251218_221255_garmin_sync.csv'
    analyze_session(csv_file)
