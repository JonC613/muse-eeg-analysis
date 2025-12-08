"""
Check available Fitbit heart rate data
"""
from fitbit_interface import FitbitInterface, FitbitAuth
import json
from datetime import datetime, timedelta

# Load credentials
with open('fitbit_credentials.json', 'r') as f:
    creds = json.load(f)

auth = FitbitAuth(creds['client_id'], creds['client_secret'])
fitbit = FitbitInterface(auth)

print("="*60)
print("CHECKING FITBIT HEART RATE DATA")
print("="*60)

# Check last 7 days
dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

print(f"\nChecking last 7 days...\n")

found_data = []

for date in dates:
    print(f"{date}:", end=" ")
    hr_data = fitbit.get_heart_rate_intraday(date, detail_level='1min')
    
    if hr_data is not None and not hr_data.empty:
        print(f"✓ {len(hr_data)} samples (HR: {hr_data['heart_rate'].min():.0f}-{hr_data['heart_rate'].max():.0f} bpm)")
        found_data.append((date, hr_data))
        
        # Show time range
        start_time = datetime.fromtimestamp(hr_data['timestamp_unix'].min())
        end_time = datetime.fromtimestamp(hr_data['timestamp_unix'].max())
        print(f"           Time: {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}")
    else:
        print("✗ No data")

if found_data:
    print(f"\n{'='*60}")
    print(f"SUMMARY: Found heart rate data for {len(found_data)} day(s)")
    print(f"{'='*60}")
    
    # Ask if user wants to export
    print("\nMost recent data with heart rate:")
    recent_date, recent_hr = found_data[0]
    print(f"  Date: {recent_date}")
    print(f"  Samples: {len(recent_hr)}")
    print(f"  Average HR: {recent_hr['heart_rate'].mean():.1f} bpm")
    
    # Save the most recent day's data
    output_file = f"recordings/{recent_date}/fitbit_heartrate_{recent_date}.csv"
    import os
    os.makedirs(f"recordings/{recent_date}", exist_ok=True)
    recent_hr.to_csv(output_file, index=False)
    print(f"\n✓ Saved to: {output_file}")
else:
    print("\n" + "="*60)
    print("No heart rate data found in the last 7 days")
    print("="*60)
    print("\nMake sure:")
    print("  • Fitbit device is synced with Fitbit app")
    print("  • All-Day Heart Rate tracking is enabled")
    print("  • You're wearing the device regularly")
