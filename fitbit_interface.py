"""
Fitbit Data Interface
Fetch sleep, heart rate, and activity data from Fitbit API for synchronization with Muse data
"""

import requests
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse


class FitbitAuth:
    """Handle Fitbit OAuth 2.0 authentication."""
    
    def __init__(self, client_id, client_secret, redirect_uri="http://localhost:8080/callback"):
        """
        Initialize Fitbit authentication.
        
        Args:
            client_id: Your Fitbit app client ID
            client_secret: Your Fitbit app client secret
            redirect_uri: OAuth redirect URI (must match app settings)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.refresh_token = None
        self.token_file = Path("fitbit_tokens.json")
        
        # Load saved tokens if available
        self._load_tokens()
    
    def _load_tokens(self):
        """Load saved access tokens from file."""
        if self.token_file.exists():
            try:
                with open(self.token_file, 'r') as f:
                    tokens = json.load(f)
                    self.access_token = tokens.get('access_token')
                    self.refresh_token = tokens.get('refresh_token')
                    print("✓ Loaded saved Fitbit tokens")
            except Exception as e:
                print(f"Could not load tokens: {e}")
    
    def _save_tokens(self):
        """Save access tokens to file."""
        tokens = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'updated_at': datetime.now().isoformat()
        }
        with open(self.token_file, 'w') as f:
            json.dump(tokens, f, indent=2)
        print("✓ Saved Fitbit tokens")
    
    def authenticate(self):
        """
        Perform OAuth authentication flow.
        Opens browser for user to authorize app.
        """
        # Authorization URL
        auth_url = (
            f"https://www.fitbit.com/oauth2/authorize?"
            f"response_type=code&client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            f"scope=activity%20heartrate%20sleep%20profile"
        )
        
        print("\n" + "="*60)
        print("FITBIT AUTHENTICATION")
        print("="*60)
        print("\n1. Opening browser for Fitbit authorization...")
        print("2. Log in and authorize the app")
        print("3. You'll be redirected to localhost (this is normal)")
        print("\nWaiting for authorization...")
        
        # Start local server to catch callback
        auth_code = self._get_auth_code(auth_url)
        
        if auth_code:
            # Exchange authorization code for tokens
            self._exchange_code_for_tokens(auth_code)
            return True
        
        return False
    
    def _get_auth_code(self, auth_url):
        """Start local server and get authorization code."""
        auth_code = [None]  # Use list to store code in nested function
        
        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                # Parse the authorization code from URL
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                
                if 'code' in params:
                    auth_code[0] = params['code'][0]
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"<html><body><h1>Authorization successful!</h1><p>You can close this window.</p></body></html>")
                else:
                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"<html><body><h1>Authorization failed!</h1></body></html>")
            
            def log_message(self, format, *args):
                pass  # Suppress server logs
        
        # Open browser
        webbrowser.open(auth_url)
        
        # Start server
        server = HTTPServer(('localhost', 8080), CallbackHandler)
        server.timeout = 120  # 2 minute timeout
        server.handle_request()
        
        return auth_code[0]
    
    def _exchange_code_for_tokens(self, auth_code):
        """Exchange authorization code for access and refresh tokens."""
        token_url = "https://api.fitbit.com/oauth2/token"
        
        data = {
            'client_id': self.client_id,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'code': auth_code
        }
        
        # Use Basic Auth with client_id:client_secret
        import base64
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.post(token_url, data=data, headers=headers)
        
        if response.status_code == 200:
            tokens = response.json()
            self.access_token = tokens['access_token']
            self.refresh_token = tokens['refresh_token']
            self._save_tokens()
            print("\n✓ Successfully authenticated with Fitbit!")
        else:
            print(f"\n✗ Authentication failed: {response.text}")
    
    def refresh_access_token(self):
        """Refresh the access token using refresh token."""
        if not self.refresh_token:
            print("No refresh token available. Please authenticate first.")
            return False
        
        token_url = "https://api.fitbit.com/oauth2/token"
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token
        }
        
        import base64
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.post(token_url, data=data, headers=headers)
        
        if response.status_code == 200:
            tokens = response.json()
            self.access_token = tokens['access_token']
            self.refresh_token = tokens['refresh_token']
            self._save_tokens()
            print("✓ Refreshed Fitbit access token")
            return True
        else:
            print(f"✗ Token refresh failed: {response.text}")
            return False


class FitbitInterface:
    """Interface to fetch Fitbit data."""
    
    def __init__(self, auth):
        """
        Initialize Fitbit interface.
        
        Args:
            auth: FitbitAuth instance with valid tokens
        """
        self.auth = auth
        self.base_url = "https://api.fitbit.com/1/user/-"
    
    def _make_request(self, endpoint):
        """Make authenticated API request."""
        if not self.auth.access_token:
            print("Not authenticated. Please authenticate first.")
            return None
        
        headers = {
            'Authorization': f'Bearer {self.auth.access_token}'
        }
        
        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 401:
            # Token expired, try to refresh
            print("Token expired, refreshing...")
            if self.auth.refresh_access_token():
                # Retry request with new token
                headers['Authorization'] = f'Bearer {self.auth.access_token}'
                response = requests.get(url, headers=headers)
            else:
                return None
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API request failed: {response.status_code} - {response.text}")
            return None
    
    def get_sleep_data(self, date=None):
        """
        Get sleep data for a specific date.
        
        Args:
            date: Date string in YYYY-MM-DD format (default: today)
            
        Returns:
            Dictionary with sleep data including timestamps
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        endpoint = f"/sleep/date/{date}.json"
        data = self._make_request(endpoint)
        
        if data and 'sleep' in data:
            sleep_sessions = []
            for sleep in data['sleep']:
                session = {
                    'date': sleep['dateOfSleep'],
                    'start_time': sleep['startTime'],
                    'end_time': sleep['endTime'],
                    'duration_ms': sleep['duration'],
                    'efficiency': sleep.get('efficiency'),
                    'minutes_asleep': sleep.get('minutesAsleep'),
                    'minutes_awake': sleep.get('minutesAwake'),
                    'time_in_bed': sleep.get('timeInBed'),
                    'main_sleep': sleep.get('isMainSleep', False)
                }
                
                # Parse timestamps to Unix epoch
                start_dt = datetime.fromisoformat(sleep['startTime'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(sleep['endTime'].replace('Z', '+00:00'))
                session['start_time_unix'] = start_dt.timestamp()
                session['end_time_unix'] = end_dt.timestamp()
                
                # Sleep stages if available
                if 'levels' in sleep:
                    session['stages'] = sleep['levels']
                
                sleep_sessions.append(session)
            
            return sleep_sessions
        
        return None
    
    def get_heart_rate_intraday(self, date=None, detail_level='1min'):
        """
        Get intraday heart rate data.
        
        Args:
            date: Date string in YYYY-MM-DD format (default: today)
            detail_level: '1min' or '1sec'
            
        Returns:
            DataFrame with timestamp and heart rate
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        endpoint = f"/activities/heart/date/{date}/1d/{detail_level}.json"
        data = self._make_request(endpoint)
        
        if data and 'activities-heart-intraday' in data:
            hr_data = data['activities-heart-intraday']['dataset']
            
            # Convert to DataFrame with Unix timestamps
            df_data = []
            base_date = datetime.strptime(date, "%Y-%m-%d")
            
            for entry in hr_data:
                time_str = entry['time']
                hr_time = datetime.strptime(f"{date} {time_str}", "%Y-%m-%d %H:%M:%S")
                
                df_data.append({
                    'timestamp_unix': hr_time.timestamp(),
                    'timestamp_iso': hr_time.isoformat(),
                    'heart_rate': entry['value']
                })
            
            return pd.DataFrame(df_data)
        
        return None
    
    def get_activity_data(self, date=None):
        """
        Get activity data for a specific date.
        
        Args:
            date: Date string in YYYY-MM-DD format (default: today)
            
        Returns:
            Dictionary with activity metrics
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        endpoint = f"/activities/date/{date}.json"
        data = self._make_request(endpoint)
        
        if data and 'summary' in data:
            return {
                'date': date,
                'steps': data['summary'].get('steps'),
                'calories': data['summary'].get('caloriesOut'),
                'distance': data['summary'].get('distances', [{}])[0].get('distance'),
                'active_minutes': data['summary'].get('fairlyActiveMinutes', 0) + 
                                 data['summary'].get('veryActiveMinutes', 0),
                'sedentary_minutes': data['summary'].get('sedentaryMinutes'),
                'resting_heart_rate': data['summary'].get('restingHeartRate')
            }
        
        return None
    
    def export_sleep_to_csv(self, date, output_dir="recordings"):
        """
        Export Fitbit sleep data to CSV for sync with Muse data.
        
        Args:
            date: Date string in YYYY-MM-DD format
            output_dir: Directory to save the file
        """
        sleep_data = self.get_sleep_data(date)
        
        if not sleep_data:
            print(f"No sleep data found for {date}")
            return None
        
        # Create date folder
        output_path = Path(output_dir) / date
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save main sleep session
        for session in sleep_data:
            if session.get('main_sleep', False):
                filename = output_path / f"fitbit_sleep_{date}.json"
                with open(filename, 'w') as f:
                    json.dump(session, f, indent=2)
                
                print(f"✓ Saved Fitbit sleep data to: {filename}")
                
                # Also create a simplified CSV for easy sync
                if 'stages' in session:
                    stages_data = []
                    for stage in session['stages']['data']:
                        stages_data.append({
                            'timestamp_unix': datetime.fromisoformat(stage['dateTime'].replace('Z', '+00:00')).timestamp(),
                            'stage': stage['level'],
                            'duration_seconds': stage['seconds']
                        })
                    
                    df = pd.DataFrame(stages_data)
                    csv_filename = output_path / f"fitbit_sleep_stages_{date}.csv"
                    df.to_csv(csv_filename, index=False)
                    print(f"✓ Saved sleep stages CSV to: {csv_filename}")
                    return csv_filename
        
        return None


def setup_fitbit():
    """Interactive setup for Fitbit integration."""
    print("\n" + "="*60)
    print("FITBIT INTEGRATION SETUP")
    print("="*60)
    print("\nTo use Fitbit integration, you need to:")
    print("1. Create a Fitbit app at https://dev.fitbit.com/apps/new")
    print("   - Application Type: Personal")
    print("   - OAuth 2.0 Application Type: Personal")
    print("   - Redirect URL: http://localhost:8080/callback")
    print("\n2. Get your Client ID and Client Secret from the app")
    print("\n3. Enter them below:")
    
    client_id = input("\nFitbit Client ID: ").strip()
    client_secret = input("Fitbit Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("\n✗ Client ID and Secret are required")
        return None
    
    # Save credentials
    credentials = {
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    with open('fitbit_credentials.json', 'w') as f:
        json.dump(credentials, f, indent=2)
    
    print("\n✓ Credentials saved to fitbit_credentials.json")
    
    # Authenticate
    auth = FitbitAuth(client_id, client_secret)
    if auth.authenticate():
        return FitbitInterface(auth)
    
    return None


def main():
    """Main function for testing."""
    import sys
    
    # Check if credentials exist
    cred_file = Path('fitbit_credentials.json')
    
    if not cred_file.exists():
        fitbit = setup_fitbit()
    else:
        with open(cred_file, 'r') as f:
            creds = json.load(f)
        
        auth = FitbitAuth(creds['client_id'], creds['client_secret'])
        
        if not auth.access_token:
            print("No valid token found. Authenticating...")
            auth.authenticate()
        
        fitbit = FitbitInterface(auth)
    
    if fitbit:
        # Example: Get today's sleep data
        print("\nFetching today's sleep data...")
        sleep = fitbit.get_sleep_data()
        if sleep:
            print(f"\nFound {len(sleep)} sleep session(s):")
            for s in sleep:
                print(f"  - {s['start_time']} to {s['end_time']}")
                print(f"    Duration: {s['minutes_asleep']} min asleep")
                print(f"    Efficiency: {s['efficiency']}%")
        
        # Export to CSV
        date = datetime.now().strftime("%Y-%m-%d")
        fitbit.export_sleep_to_csv(date)


if __name__ == "__main__":
    main()
