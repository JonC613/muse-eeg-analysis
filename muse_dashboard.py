"""
Real-time Muse S EEG Dashboard
Visualizes brain activity, heart rate, and motion data in real-time using Plotly Dash
"""

import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from collections import deque
import numpy as np
from muse_interface import MuseInterface
import threading
import time


class MuseDashboard:
    """Real-time dashboard for Muse S data visualization."""
    
    def __init__(self, buffer_size=500):
        """
        Initialize the dashboard.
        
        Args:
            buffer_size: Number of data points to keep in rolling buffer
        """
        self.buffer_size = buffer_size
        self.muse = MuseInterface()
        
        # Data buffers for EEG (4 channels)
        self.eeg_time = deque(maxlen=buffer_size)
        self.eeg_tp9 = deque(maxlen=buffer_size)
        self.eeg_af7 = deque(maxlen=buffer_size)
        self.eeg_af8 = deque(maxlen=buffer_size)
        self.eeg_tp10 = deque(maxlen=buffer_size)
        
        # Data buffers for frequency bands
        self.band_names = ['Delta (0.5-4Hz)', 'Theta (4-8Hz)', 'Alpha (8-13Hz)', 
                          'Beta (13-30Hz)', 'Gamma (30-50Hz)']
        self.band_powers = {band: deque(maxlen=50) for band in self.band_names}
        
        # Data buffers for motion
        self.gyro_time = deque(maxlen=buffer_size)
        self.gyro_x = deque(maxlen=buffer_size)
        self.gyro_y = deque(maxlen=buffer_size)
        self.gyro_z = deque(maxlen=buffer_size)
        
        self.acc_time = deque(maxlen=buffer_size)
        self.acc_x = deque(maxlen=buffer_size)
        self.acc_y = deque(maxlen=buffer_size)
        self.acc_z = deque(maxlen=buffer_size)
        
        # PPG (heart rate) buffer
        self.ppg_time = deque(maxlen=buffer_size)
        self.ppg_values = deque(maxlen=buffer_size)
        
        # Sampling info
        self.start_time = None
        self.start_time_unix = None  # Unix epoch timestamp for sync
        self.is_running = False
        self.data_thread = None
        
        # Create Dash app
        self.app = dash.Dash(__name__)
        self.setup_layout()
        self.setup_callbacks()
    
    def calculate_band_powers(self, eeg_data, fs=256):
        """
        Calculate power in different frequency bands.
        
        Args:
            eeg_data: Array of EEG samples
            fs: Sampling frequency (Hz)
            
        Returns:
            Dictionary of band powers
        """
        if len(eeg_data) < 128:  # Need enough data
            return {band: 0 for band in self.band_names}
        
        # Compute FFT
        fft_vals = np.fft.rfft(eeg_data)
        fft_freq = np.fft.rfftfreq(len(eeg_data), 1.0/fs)
        fft_power = np.abs(fft_vals) ** 2
        
        # Define frequency bands
        bands = {
            'Delta (0.5-4Hz)': (0.5, 4),
            'Theta (4-8Hz)': (4, 8),
            'Alpha (8-13Hz)': (8, 13),
            'Beta (13-30Hz)': (13, 30),
            'Gamma (30-50Hz)': (30, 50)
        }
        
        band_powers = {}
        for band_name, (low, high) in bands.items():
            idx = np.where((fft_freq >= low) & (fft_freq <= high))
            band_powers[band_name] = np.mean(fft_power[idx]) if len(idx[0]) > 0 else 0
        
        return band_powers
    
    def collect_data(self):
        """Background thread to collect data from Muse."""
        self.start_time = time.time()
        self.start_time_unix = self.start_time  # Store Unix epoch for sync
        sample_count = 0
        
        while self.is_running:
            current_time = time.time() - self.start_time
            
            # Read EEG
            eeg_data = self.muse.read_eeg_sample()
            if eeg_data and eeg_data['channels']:
                self.eeg_time.append(current_time)
                self.eeg_tp9.append(eeg_data['tp9'] or 0)
                self.eeg_af7.append(eeg_data['af7'] or 0)
                self.eeg_af8.append(eeg_data['af8'] or 0)
                self.eeg_tp10.append(eeg_data['tp10'] or 0)
                
                sample_count += 1
                if sample_count % 100 == 0:
                    print(f"Collected {sample_count} EEG samples, buffer size: {len(self.eeg_time)}")
                
                # Calculate frequency bands (use AF7 channel)
                if len(self.eeg_af7) >= 128:
                    bands = self.calculate_band_powers(list(self.eeg_af7))
                    for band_name, power in bands.items():
                        self.band_powers[band_name].append(power)
            
            # Read PPG
            ppg_data = self.muse.read_ppg_sample()
            if ppg_data and ppg_data['values']:
                self.ppg_time.append(current_time)
                self.ppg_values.append(np.mean(ppg_data['values']))
            
            # Read Gyroscope
            gyro_data = self.muse.read_gyro_sample()
            if gyro_data and gyro_data['x'] is not None:
                self.gyro_time.append(current_time)
                self.gyro_x.append(gyro_data['x'])
                self.gyro_y.append(gyro_data['y'])
                self.gyro_z.append(gyro_data['z'])
            
            # Read Accelerometer
            acc_data = self.muse.read_acc_sample()
            if acc_data and acc_data['x'] is not None:
                self.acc_time.append(current_time)
                self.acc_x.append(acc_data['x'])
                self.acc_y.append(acc_data['y'])
                self.acc_z.append(acc_data['z'])
            
            time.sleep(0.01)  # 100Hz polling
    
    def setup_layout(self):
        """Setup the Dash app layout."""
        self.app.layout = html.Div([
            html.H1("Muse S Real-Time Dashboard", 
                   style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': 30}),
            
            html.Div([
                html.H3("Connection Status", style={'color': '#34495e'}),
                html.Div(id='connection-status', style={'fontSize': 18, 'marginBottom': 20})
            ], style={'textAlign': 'center', 'marginBottom': 30}),
            
            # EEG Waveforms
            html.Div([
                html.H2("EEG Brain Waves", style={'color': '#2980b9'}),
                dcc.Graph(id='eeg-graph', config={'displayModeBar': False})
            ], style={'marginBottom': 30}),
            
            # Frequency Bands
            html.Div([
                html.H2("Frequency Band Power", style={'color': '#8e44ad'}),
                dcc.Graph(id='bands-graph', config={'displayModeBar': False})
            ], style={'marginBottom': 30}),
            
            # Motion and PPG in row
            html.Div([
                html.Div([
                    html.H2("Head Motion (Gyroscope)", style={'color': '#27ae60'}),
                    dcc.Graph(id='gyro-graph', config={'displayModeBar': False})
                ], style={'width': '48%', 'display': 'inline-block'}),
                
                html.Div([
                    html.H2("Heart Rate (PPG)", style={'color': '#e74c3c'}),
                    dcc.Graph(id='ppg-graph', config={'displayModeBar': False})
                ], style={'width': '48%', 'display': 'inline-block', 'float': 'right'})
            ], style={'marginBottom': 30}),
            
            # Accelerometer
            html.Div([
                html.H2("Head Movement (Accelerometer)", style={'color': '#f39c12'}),
                dcc.Graph(id='acc-graph', config={'displayModeBar': False})
            ], style={'marginBottom': 30}),
            
            # Update interval
            dcc.Interval(
                id='interval-component',
                interval=100,  # Update every 100ms
                n_intervals=0
            )
        ], style={'padding': '20px', 'fontFamily': 'Arial, sans-serif', 'backgroundColor': '#ecf0f1'})
    
    def setup_callbacks(self):
        """Setup Dash callbacks for real-time updates."""
        
        @self.app.callback(
            Output('connection-status', 'children'),
            Input('interval-component', 'n_intervals')
        )
        def update_status(n):
            if self.is_running:
                return html.Span("✓ Connected and Streaming", 
                               style={'color': '#27ae60', 'fontWeight': 'bold'})
            else:
                return html.Span("✗ Not Connected", 
                               style={'color': '#e74c3c', 'fontWeight': 'bold'})
        
        @self.app.callback(
            Output('eeg-graph', 'figure'),
            Input('interval-component', 'n_intervals')
        )
        def update_eeg(n):
            if n % 10 == 0:  # Log every 10 updates
                print(f"Update {n}: EEG buffer has {len(self.eeg_time)} samples")
            
            fig = go.Figure()
            
            if not self.eeg_time:
                fig.update_layout(
                    xaxis_title="Time (seconds)",
                    yaxis_title="Amplitude (µV)",
                    height=400,
                    margin=dict(l=50, r=50, t=30, b=50),
                    plot_bgcolor='white',
                    annotations=[dict(
                        text="Waiting for EEG data...",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=20, color="gray")
                    )]
                )
                return fig
            
            # Add each EEG channel
            channels = [
                ('TP9 (Left Ear)', self.eeg_tp9, '#3498db'),
                ('AF7 (Left Forehead)', self.eeg_af7, '#9b59b6'),
                ('AF8 (Right Forehead)', self.eeg_af8, '#e67e22'),
                ('TP10 (Right Ear)', self.eeg_tp10, '#1abc9c')
            ]
            
            for name, data, color in channels:
                fig.add_trace(go.Scatter(
                    x=list(self.eeg_time),
                    y=list(data),
                    name=name,
                    mode='lines',
                    line=dict(color=color, width=1.5)
                ))
            
            fig.update_layout(
                xaxis_title="Time (seconds)",
                yaxis_title="Amplitude (µV)",
                hovermode='x unified',
                height=400,
                margin=dict(l=50, r=50, t=30, b=50),
                plot_bgcolor='white',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            
            return fig
        
        @self.app.callback(
            Output('bands-graph', 'figure'),
            Input('interval-component', 'n_intervals')
        )
        def update_bands(n):
            current_powers = []
            has_data = False
            for band in self.band_names:
                if self.band_powers[band]:
                    current_powers.append(self.band_powers[band][-1])
                    has_data = True
                else:
                    current_powers.append(0.1)
            
            fig = go.Figure(data=[
                go.Bar(
                    x=self.band_names,
                    y=current_powers,
                    marker_color=['#3498db', '#9b59b6', '#2ecc71', '#e67e22', '#e74c3c']
                )
            ])
            
            fig.update_layout(
                yaxis_title="Power (µV²)",
                height=350,
                margin=dict(l=50, r=50, t=30, b=100),
                plot_bgcolor='white'
            )
            
            if not has_data:
                fig.add_annotation(
                    text="Calculating frequency bands...",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="gray")
                )
            
            return fig
        
        @self.app.callback(
            Output('gyro-graph', 'figure'),
            Input('interval-component', 'n_intervals')
        )
        def update_gyro(n):
            fig = go.Figure()
            
            if not self.gyro_time:
                fig.update_layout(
                    xaxis_title="Time (seconds)",
                    yaxis_title="Angular Velocity (°/s)",
                    height=300,
                    margin=dict(l=50, r=50, t=30, b=50),
                    plot_bgcolor='white',
                    annotations=[dict(
                        text="Waiting for gyroscope data...",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=16, color="gray")
                    )]
                )
                return fig
            
            axes = [
                ('X-axis', self.gyro_x, '#e74c3c'),
                ('Y-axis', self.gyro_y, '#2ecc71'),
                ('Z-axis', self.gyro_z, '#3498db')
            ]
            
            for name, data, color in axes:
                fig.add_trace(go.Scatter(
                    x=list(self.gyro_time),
                    y=list(data),
                    name=name,
                    mode='lines',
                    line=dict(color=color, width=2)
                ))
            
            fig.update_layout(
                xaxis_title="Time (seconds)",
                yaxis_title="Angular Velocity (°/s)",
                hovermode='x unified',
                height=300,
                margin=dict(l=50, r=50, t=30, b=50),
                plot_bgcolor='white'
            )
            
            return fig
        
        @self.app.callback(
            Output('ppg-graph', 'figure'),
            Input('interval-component', 'n_intervals')
        )
        def update_ppg(n):
            fig = go.Figure()
            
            if not self.ppg_time:
                fig.update_layout(
                    xaxis_title="Time (seconds)",
                    yaxis_title="PPG Signal",
                    height=300,
                    margin=dict(l=50, r=50, t=30, b=50),
                    plot_bgcolor='white',
                    annotations=[dict(
                        text="Waiting for PPG data...",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=16, color="gray")
                    )]
                )
                return fig
            
            fig.add_trace(go.Scatter(
                x=list(self.ppg_time),
                y=list(self.ppg_values),
                mode='lines',
                line=dict(color='#e74c3c', width=2),
                fill='tozeroy',
                fillcolor='rgba(231, 76, 60, 0.1)'
            ))
            
            fig.update_layout(
                xaxis_title="Time (seconds)",
                yaxis_title="PPG Signal",
                hovermode='x unified',
                height=300,
                margin=dict(l=50, r=50, t=30, b=50),
                plot_bgcolor='white',
                showlegend=False
            )
            
            return fig
        
        @self.app.callback(
            Output('acc-graph', 'figure'),
            Input('interval-component', 'n_intervals')
        )
        def update_acc(n):
            fig = go.Figure()
            
            if not self.acc_time:
                fig.update_layout(
                    xaxis_title="Time (seconds)",
                    yaxis_title="Acceleration (g)",
                    height=300,
                    margin=dict(l=50, r=50, t=30, b=50),
                    plot_bgcolor='white',
                    annotations=[dict(
                        text="Waiting for accelerometer data...",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False,
                        font=dict(size=16, color="gray")
                    )]
                )
                return fig
            
            axes = [
                ('X-axis', self.acc_x, '#e67e22'),
                ('Y-axis', self.acc_y, '#9b59b6'),
                ('Z-axis', self.acc_z, '#1abc9c')
            ]
            
            for name, data, color in axes:
                fig.add_trace(go.Scatter(
                    x=list(self.acc_time),
                    y=list(data),
                    name=name,
                    mode='lines',
                    line=dict(color=color, width=2)
                ))
            
            fig.update_layout(
                xaxis_title="Time (seconds)",
                yaxis_title="Acceleration (g)",
                hovermode='x unified',
                height=300,
                margin=dict(l=50, r=50, t=30, b=50),
                plot_bgcolor='white'
            )
            
            return fig
    
    def start(self, debug=False, port=8050):
        """
        Connect to Muse and start the dashboard.
        
        Args:
            debug: Run in debug mode
            port: Port number for web server
        """
        print("=" * 60)
        print("Muse S Real-Time Dashboard")
        print("=" * 60)
        
        # Connect to Muse
        print("\nConnecting to Muse S...")
        if not self.muse.connect(timeout=10):
            print("\nFailed to connect to Muse. Exiting...")
            return
        
        # Start data collection thread
        print("\nStarting data collection...")
        self.is_running = True
        self.data_thread = threading.Thread(target=self.collect_data, daemon=True)
        self.data_thread.start()
        
        # Start web server
        print(f"\n✓ Dashboard starting...")
        print(f"✓ Open your browser to: http://localhost:{port}")
        print("\nPress Ctrl+C to stop\n")
        
        try:
            self.app.run(debug=debug, port=port, host='0.0.0.0')
        except KeyboardInterrupt:
            print("\n\nStopping dashboard...")
            self.is_running = False
            if self.data_thread:
                self.data_thread.join(timeout=2)
            print("Dashboard stopped.")


def main():
    """Main function to run the dashboard."""
    dashboard = MuseDashboard(buffer_size=500)
    dashboard.start(debug=False, port=8050)


if __name__ == "__main__":
    main()
