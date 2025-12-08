import pandas as pd

df = pd.read_csv('recordings/2025-12-07/muse_session_90.csv')
print("Muse PPG (Heart Rate) Statistics:")
print(f"  Mean PPG: {df['ppg_avg'].mean():.1f}")
print(f"  Min: {df['ppg_avg'].min():.1f}")
print(f"  Max: {df['ppg_avg'].max():.1f}")
print(f"  Samples: {df['ppg_avg'].notna().sum()}")
print("\nYour Muse headband has built-in heart rate tracking!")
