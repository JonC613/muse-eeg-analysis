"""
Garmin Connect Data Interface
Fetch sleep, heart rate, and activity data from Garmin Connect for synchronization with Muse data
"""

import json
import time
from datetime import datetime, timedelta, date
from pathlib import Path
import pandas as pd
from garminconnect import Garmin, GarminConnectAuthenticationError, GarminConnectConnectionError


class GarminInterface:
    """Interface to fetch Garmin Connect data."""
    
    def __init__(self, email=None, password=None):
        """
        Initialize Garmin Connect interface.
        
        Args:
            email: Garmin Connect email (optional if credentials file exists)
            password: Garmin Connect password (optional if credentials file exists)
        """
        self.email = email
        self.password = password
        self.client = None
        self.token_file = Path("garmin_tokens.json")
        self.creds_file = Path("garmin_credentials.json")
        
        # Load credentials if not provided
        if not self.email or not self.password:
            self._load_credentials()
        
        # Try to authenticate
        self._authenticate()
    
    def _load_credentials(self):
        """Load saved credentials from file."""
        if self.creds_file.exists():
            try:
                with open(self.creds_file, 'r') as f:
                    creds = json.load(f)
                    self.email = creds.get('email')
                    self.password = creds.get('password')
                    print("✓ Loaded saved Garmin credentials")
            except Exception as e:
                print(f"Could not load credentials: {e}")
        else:
            print("No credentials file found. Please provide email and password.")
    
    def _save_credentials(self):
        """Save credentials to file."""
        creds = {
            'email': self.email,
            'password': self.password
        }
        with open(self.creds_file, 'w') as f:
            json.dump(creds, f, indent=2)
        print("✓ Saved Garmin credentials")
    
    def _authenticate(self):
        """Authenticate with Garmin Connect."""
        if not self.email or not self.password:
            print("❌ Email and password required for Garmin Connect")
            return False
        
        try:
            print("Authenticating with Garmin Connect...")
            self.client = Garmin(self.email, self.password)
            self.client.login()
            
            # Save session tokens
            self._save_tokens()
            
            # Save credentials if authentication successful
            if not self.creds_file.exists():
                self._save_credentials()
            
            print("✓ Successfully authenticated with Garmin Connect!")
            return True
            
        except GarminConnectAuthenticationError as e:
            print(f"❌ Authentication failed: {e}")
            print("Please check your email and password.")
            return False
        except Exception as e:
            print(f"❌ Error during authentication: {e}")
            return False
    
    def _save_tokens(self):
        """Save session tokens for reuse."""
        if self.client:
            try:
                tokens = {
                    'authenticated': True,
                    'updated_at': datetime.now().isoformat()
                }
                with open(self.token_file, 'w') as f:
                    json.dump(tokens, f, indent=2)
            except Exception as e:
                # Session data not available in this version
                pass
    
    def get_heart_rate_intraday(self, target_date, detail_level='second'):
        """
        Get intraday heart rate data for a specific date.
        
        Args:
            target_date: Date string in format 'YYYY-MM-DD' or datetime object
            detail_level: 'second', 'minute', or 'hour' (Garmin provides per-second data)
            
        Returns:
            DataFrame with heart rate data
        """
        if not self.client:
            print("Not authenticated")
            return None
        
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()
        
        try:
            print(f"Fetching heart rate data for {target_date}...")
            
            # Get heart rate data
            hr_data = self.client.get_heart_rates(target_date.isoformat())
            
            if not hr_data or 'heartRateValues' not in hr_data:
                print("No heart rate data available")
                return None
            
            # Parse heart rate values
            hr_values = hr_data['heartRateValues']
            
            records = []
            for entry in hr_values:
                if not entry or len(entry) < 2:
                    continue
                    
                timestamp_ms = entry[0]  # Unix timestamp in milliseconds
                hr_value = entry[1]      # Heart rate in bpm
                
                if hr_value and hr_value > 0:  # Skip null values
                    try:
                        dt = datetime.fromtimestamp(timestamp_ms / 1000)
                        records.append({
                            'datetime': dt,
                            'time': dt.strftime('%H:%M:%S'),
                            'heart_rate_bpm': int(hr_value)
                        })
                    except (ValueError, TypeError):
                        continue
            
            if not records:
                print("No valid heart rate data found")
                return None
            
            df = pd.DataFrame(records)
            
            # Resample if needed
            if detail_level == 'minute':
                df.set_index('datetime', inplace=True)
                df = df[['heart_rate_bpm']].resample('1min').mean().reset_index()
                df['time'] = df['datetime'].dt.strftime('%H:%M:%S')
                df['heart_rate_bpm'] = df['heart_rate_bpm'].round().astype('Int64')
            elif detail_level == 'hour':
                df.set_index('datetime', inplace=True)
                df = df[['heart_rate_bpm']].resample('1H').mean().reset_index()
                df['time'] = df['datetime'].dt.strftime('%H:%M:%S')
                df['heart_rate_bpm'] = df['heart_rate_bpm'].round().astype('Int64')
            
            print(f"✓ Retrieved {len(df)} heart rate samples")
            return df
            
        except Exception as e:
            print(f"Error fetching heart rate data: {e}")
            return None
    
    def get_sleep_data(self, target_date):
        """
        Get sleep data for a specific date.
        
        Args:
            target_date: Date string in format 'YYYY-MM-DD' or datetime object
            
        Returns:
            Dictionary with sleep data
        """
        if not self.client:
            print("Not authenticated")
            return None
        
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()
        
        try:
            print(f"Fetching sleep data for {target_date}...")
            
            sleep_data = self.client.get_sleep_data(target_date.isoformat())
            
            if not sleep_data:
                print("No sleep data available")
                return None
            
            # Extract key metrics
            summary = {
                'date': target_date.isoformat(),
                'sleep_start': sleep_data.get('sleepStartTimestampLocal'),
                'sleep_end': sleep_data.get('sleepEndTimestampLocal'),
                'total_sleep_seconds': sleep_data.get('sleepTimeSeconds', 0),
                'deep_sleep_seconds': sleep_data.get('deepSleepSeconds', 0),
                'light_sleep_seconds': sleep_data.get('lightSleepSeconds', 0),
                'rem_sleep_seconds': sleep_data.get('remSleepSeconds', 0),
                'awake_seconds': sleep_data.get('awakeSleepSeconds', 0),
                'sleep_score': sleep_data.get('overallSleepScore'),
                'avg_respiration': sleep_data.get('averageRespirationValue'),
                'avg_spo2': sleep_data.get('averageSpO2Value')
            }
            
            print(f"✓ Retrieved sleep data: {summary['total_sleep_seconds']/3600:.1f} hours")
            return summary
            
        except Exception as e:
            print(f"Error fetching sleep data: {e}")
            return None
    
    def get_activities_on_date(self, target_date):
        """
        Get activities for a specific date.
        
        Args:
            target_date: Date string in format 'YYYY-MM-DD' or datetime object
            
        Returns:
            List of activities
        """
        if not self.client:
            print("Not authenticated")
            return None
        
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()
        
        try:
            print(f"Fetching activities for {target_date}...")
            
            activities = self.client.get_activities_by_date(
                target_date.isoformat(),
                target_date.isoformat()
            )
            
            if not activities:
                print("No activities found")
                return []
            
            activity_list = []
            for activity in activities:
                activity_list.append({
                    'activity_id': activity.get('activityId'),
                    'activity_name': activity.get('activityName'),
                    'start_time': activity.get('startTimeLocal'),
                    'duration_seconds': activity.get('duration'),
                    'distance_meters': activity.get('distance'),
                    'avg_heart_rate': activity.get('averageHR'),
                    'max_heart_rate': activity.get('maxHR'),
                    'calories': activity.get('calories')
                })
            
            print(f"✓ Found {len(activity_list)} activities")
            return activity_list
            
        except Exception as e:
            print(f"Error fetching activities: {e}")
            return []
    
    def get_stress_data(self, target_date):
        """
        Get stress data for a specific date.
        
        Args:
            target_date: Date string in format 'YYYY-MM-DD' or datetime object
            
        Returns:
            DataFrame with stress levels throughout the day
        """
        if not self.client:
            print("Not authenticated")
            return None
        
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()
        
        try:
            print(f"Fetching stress data for {target_date}...")
            
            stress_data = self.client.get_stress_data(target_date.isoformat())
            
            if not stress_data or 'stressValuesArray' not in stress_data:
                print("No stress data available")
                return None
            
            records = []
            for entry in stress_data['stressValuesArray']:
                if entry[1] is not None and entry[1] >= 0:  # Skip invalid values
                    timestamp_ms = entry[0]
                    stress_level = entry[1]
                    dt = datetime.fromtimestamp(timestamp_ms / 1000)
                    
                    records.append({
                        'datetime': dt,
                        'time': dt.strftime('%H:%M:%S'),
                        'stress_level': stress_level
                    })
            
            if not records:
                print("No valid stress data found")
                return None
            
            df = pd.DataFrame(records)
            print(f"✓ Retrieved {len(df)} stress measurements")
            return df
            
        except Exception as e:
            print(f"Error fetching stress data: {e}")
            return None


def main():
    """Demo usage of Garmin Connect interface."""
    print("=" * 60)
    print("GARMIN CONNECT DATA INTERFACE")
    print("=" * 60)
    
    # Check for credentials
    creds_file = Path('garmin_credentials.json')
    if not creds_file.exists():
        print("\nFirst time setup:")
        email = input("Enter your Garmin Connect email: ")
        password = input("Enter your Garmin Connect password: ")
        
        garmin = GarminInterface(email, password)
    else:
        garmin = GarminInterface()
    
    if not garmin.client:
        print("\n❌ Failed to authenticate with Garmin Connect")
        return
    
    # Get today's date
    today = date.today()
    
    print(f"\n{'='*60}")
    print(f"DATA FOR {today}")
    print(f"{'='*60}")
    
    # Fetch heart rate
    hr_data = garmin.get_heart_rate_intraday(today, detail_level='minute')
    if hr_data is not None:
        print(f"\nHeart Rate Stats:")
        print(f"  Samples: {len(hr_data)}")
        print(f"  Average: {hr_data['heart_rate_bpm'].mean():.1f} bpm")
        print(f"  Min: {hr_data['heart_rate_bpm'].min():.0f} bpm")
        print(f"  Max: {hr_data['heart_rate_bpm'].max():.0f} bpm")
    
    # Fetch stress data
    stress_data = garmin.get_stress_data(today)
    if stress_data is not None:
        print(f"\nStress Stats:")
        print(f"  Samples: {len(stress_data)}")
        print(f"  Average: {stress_data['stress_level'].mean():.1f}")
        print(f"  Max: {stress_data['stress_level'].max():.0f}")
    
    # Fetch sleep data
    sleep_data = garmin.get_sleep_data(today)
    if sleep_data:
        print(f"\nSleep Data:")
        print(f"  Total Sleep: {sleep_data['total_sleep_seconds']/3600:.1f} hours")
        print(f"  Deep Sleep: {sleep_data['deep_sleep_seconds']/60:.0f} minutes")
        print(f"  Light Sleep: {sleep_data['light_sleep_seconds']/60:.0f} minutes")
        print(f"  REM Sleep: {sleep_data['rem_sleep_seconds']/60:.0f} minutes")
        if sleep_data['sleep_score']:
            print(f"  Sleep Score: {sleep_data['sleep_score']}")
    
    # Fetch activities
    activities = garmin.get_activities_on_date(today)
    if activities:
        print(f"\nActivities:")
        for activity in activities:
            print(f"  • {activity['activity_name']}")
            print(f"    Duration: {activity['duration_seconds']/60:.0f} minutes")
            if activity['avg_heart_rate']:
                print(f"    Avg HR: {activity['avg_heart_rate']} bpm")


if __name__ == "__main__":
    main()
