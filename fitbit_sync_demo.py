"""
Demo: How to sync Muse and Fitbit data
This shows what the sync will look like when you have matching data
"""

from muse_fitbit_sync import MuseFitbitSync
from fitbit_interface import FitbitInterface, FitbitAuth
import json
from pathlib import Path

print("="*60)
print("MUSE + FITBIT SYNC GUIDE")
print("="*60)

print("\n1. AUTOMATIC SYNC (Recommended)")
print("-" * 60)
print("When you have a Muse recording and want to match it with Fitbit:")
print("")
print("  python muse_fitbit_sync.py <path_to_muse_csv>")
print("")
print("Example:")
print("  python muse_fitbit_sync.py recordings/2025-12-07/muse_session_meditation_20251207_200000.csv")
print("")
print("This will:")
print("  ✓ Load your Muse session")
print("  ✓ Fetch Fitbit heart rate data for the same time period")
print("  ✓ Merge the data based on timestamps")
print("  ✓ Create visualization showing EEG + heart rate")
print("  ✓ Save combined CSV file")

print("\n2. MANUAL SYNC (For custom analysis)")
print("-" * 60)
print("In Python:")
print("""
from muse_fitbit_sync import MuseFitbitSync

sync = MuseFitbitSync()
merged_data = sync.sync_with_muse_session(
    'recordings/2025-12-07/muse_session_90_20251207_200415.csv'
)

# Now you have combined data with both EEG and heart rate
print(merged_data.columns)
# Output: timestamp_unix, timestamp_iso, elapsed_time, eeg_tp9, eeg_af7, 
#         eeg_af8, eeg_tp10, ppg_avg, gyro_x, gyro_y, gyro_z, 
#         acc_x, acc_y, acc_z, heart_rate

# Analyze correlations
import pandas as pd
correlation = merged_data[['eeg_af7', 'heart_rate']].corr()
print(correlation)
""")

print("\n3. GET FITBIT DATA FOR SPECIFIC DATE")
print("-" * 60)
print("To check what Fitbit data is available:")
print("""
from fitbit_interface import FitbitInterface, FitbitAuth
import json

# Load credentials
with open('fitbit_credentials.json', 'r') as f:
    creds = json.load(f)

auth = FitbitAuth(creds['client_id'], creds['client_secret'])
fitbit = FitbitInterface(auth)

# Get heart rate for specific date
hr_data = fitbit.get_heart_rate_intraday('2025-12-07')
if hr_data is not None:
    print(f"Found {len(hr_data)} heart rate samples")
    print(hr_data.head())

# Get sleep data
sleep = fitbit.get_sleep_data('2025-12-07')
if sleep:
    for session in sleep:
        print(f"Sleep: {session['start_time']} to {session['end_time']}")

# Export sleep stages to CSV
fitbit.export_sleep_to_csv('2025-12-07')
""")

print("\n4. WHAT GETS CREATED")
print("-" * 60)
print("When sync is successful, you get:")
print("  • muse_session_XXX_with_fitbit.csv - Combined data")
print("  • muse_session_XXX_fitbit_summary.txt - Statistics")
print("  • muse_session_XXX_fitbit_sync.png - Visualization")
print("")
print("The visualization shows:")
print("  - Top panel: EEG brainwaves")
print("  - Middle panel: Fitbit heart rate overlaid")
print("  - Bottom panel: Head movement")

print("\n5. WHY NO DATA TODAY?")
print("-" * 60)
print("Fitbit collects heart rate data when:")
print("  ✓ You're wearing the device")
print("  ✓ Heart rate tracking is enabled")
print("  ✓ You're active or have 'All-Day Sync' enabled")
print("")
print("The Muse session at 20:04 today might not have matching")
print("Fitbit data if:")
print("  • Fitbit wasn't being worn")
print("  • Device hasn't synced yet")
print("  • Heart rate tracking was paused")
print("")
print("Try syncing with:")
print("  • A session from yesterday (when you have confirmed Fitbit data)")
print("  • A future session after wearing Fitbit during recording")

print("\n6. BEST PRACTICES")
print("-" * 60)
print("For optimal sync:")
print("  1. Wear your Fitbit during Muse recording sessions")
print("  2. Enable 'All-Day Heart Rate' in Fitbit app")
print("  3. Sync Fitbit device before running sync")
print("  4. Record sessions when you know you have Fitbit data")

print("\n" + "="*60)
print("✓ Fitbit is connected and ready!")
print("  Just need matching data timeframes")
print("="*60)
