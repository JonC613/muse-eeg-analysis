#!/usr/bin/env python3
"""
Check Garmin data coverage for both Mind Monitor sessions
"""
from garmin_interface import GarminInterface
from datetime import datetime
import pandas as pd

print("=" * 60)
print("GARMIN DATA COVERAGE REPORT")
print("=" * 60)

# Initialize Garmin
garmin = GarminInterface()

# Get heart rate data
print("\nFetching Garmin heart rate data...")
hr_df = garmin.get_heart_rate_intraday('2025-12-18')
print(f"✓ Retrieved {len(hr_df)} heart rate samples")

if len(hr_df) > 0:
    print(f"\nGarmin HR Coverage:")
    print(f"  First sample: {hr_df['datetime'].iloc[0]}")
    print(f"  Last sample:  {hr_df['datetime'].iloc[-1]}")
else:
    print("❌ No heart rate data available")

# Session 1 info
print("\n" + "=" * 60)
print("SESSION 1: T+15 minutes (22:04:33 - 22:10:50)")
print("=" * 60)
session1_start = datetime.fromisoformat("2025-12-18 22:04:33")
session1_end = datetime.fromisoformat("2025-12-18 22:10:50")

if len(hr_df) > 0:
    session1_hr = hr_df[
        (pd.to_datetime(hr_df['datetime']) >= session1_start) &
        (pd.to_datetime(hr_df['datetime']) <= session1_end)
    ]
    print(f"Heart Rate samples in range: {len(session1_hr)}")
    if len(session1_hr) > 0:
        print(f"  Avg HR: {session1_hr['heart_rate_bpm'].mean():.1f} bpm")
        print(f"  Min/Max: {session1_hr['heart_rate_bpm'].min()}/{session1_hr['heart_rate_bpm'].max()} bpm")
        print("  ✅ DATA AVAILABLE FOR SYNC")
    else:
        print("  ❌ NO DATA IN THIS TIME RANGE")

# Session 2 info
print("\n" + "=" * 60)
print("SESSION 2: T+50 minutes (22:55:30 - 23:02:56)")
print("=" * 60)
session2_start = datetime.fromisoformat("2025-12-18 22:55:30")
session2_end = datetime.fromisoformat("2025-12-18 23:02:56")

if len(hr_df) > 0:
    session2_hr = hr_df[
        (pd.to_datetime(hr_df['datetime']) >= session2_start) &
        (pd.to_datetime(hr_df['datetime']) <= session2_end)
    ]
    print(f"Heart Rate samples in range: {len(session2_hr)}")
    if len(session2_hr) > 0:
        print(f"  Avg HR: {session2_hr['heart_rate_bpm'].mean():.1f} bpm")
        print(f"  Min/Max: {session2_hr['heart_rate_bpm'].min()}/{session2_hr['heart_rate_bpm'].max()} bpm")
        print("  ✅ DATA AVAILABLE FOR SYNC")
    else:
        print("  ❌ NO DATA IN THIS TIME RANGE")
        # Find closest samples
        before = hr_df[pd.to_datetime(hr_df['datetime']) < session2_start]
        after = hr_df[pd.to_datetime(hr_df['datetime']) > session2_end]
        if len(before) > 0:
            print(f"\n  Last HR before session: {before['datetime'].iloc[-1]}")
        if len(after) > 0:
            print(f"  First HR after session: {after['datetime'].iloc[0]}")

print("\n" + "=" * 60)
print("CONCLUSION")
print("=" * 60)
print("Session 1: Can sync with Garmin data")
print("Session 2: Check if data available in time range above")
