"""
Simple Real-time Muse S Visualizer using Matplotlib
Shows live EEG waveforms and frequency bands in a desktop window
"""

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.gridspec import GridSpec
import numpy as np
from collections import deque
from muse_interface import MuseInterface
import threading
import time


class MuseVisualizer:
    """Simple real-time visualizer for Muse S data."""
    
    def __init__(self, buffer_size=500):
        """Initialize the visualizer."""
        self.buffer_size = buffer_size
        self.muse = MuseInterface()
        
        # Data buffers for EEG (4 channels)
        self.eeg_time = deque(maxlen=buffer_size)
        self.eeg_tp9 = deque(maxlen=buffer_size)
        self.eeg_af7 = deque(maxlen=buffer_size)
        self.eeg_af8 = deque(maxlen=buffer_size)
        self.eeg_tp10 = deque(maxlen=buffer_size)
        
        # Frequency band powers
        self.band_names = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma']
        self.band_powers = [0, 0, 0, 0, 0]
        
        # Motion data
        self.gyro_time = deque(maxlen=buffer_size)
        self.gyro_x = deque(maxlen=buffer_size)
        self.gyro_y = deque(maxlen=buffer_size)
        self.gyro_z = deque(maxlen=buffer_size)
        
        self.start_time = None
        self.is_running = False
        self.data_thread = None
        
        # Setup matplotlib figure
        self.setup_plots()
    
    def setup_plots(self):
        """Setup the matplotlib figure and subplots."""
        plt.style.use('dark_background')
        self.fig = plt.figure(figsize=(14, 10))
        self.fig.suptitle('Muse S Real-Time EEG Visualizer', fontsize=16, fontweight='bold')
        
        # Create grid layout
        gs = GridSpec(3, 2, figure=self.fig, hspace=0.3, wspace=0.3)
        
        # EEG waveforms (top row, spanning both columns)
        self.ax_eeg = self.fig.add_subplot(gs[0, :])
        self.ax_eeg.set_title('EEG Brain Waves', fontsize=12, fontweight='bold')
        self.ax_eeg.set_xlabel('Time (seconds)')
        self.ax_eeg.set_ylabel('Amplitude (µV)')
        self.ax_eeg.grid(True, alpha=0.3)
        
        # Initialize EEG lines
        self.line_tp9, = self.ax_eeg.plot([], [], label='TP9 (Left Ear)', color='#3498db', linewidth=1)
        self.line_af7, = self.ax_eeg.plot([], [], label='AF7 (Left Forehead)', color='#9b59b6', linewidth=1)
        self.line_af8, = self.ax_eeg.plot([], [], label='AF8 (Right Forehead)', color='#e67e22', linewidth=1)
        self.line_tp10, = self.ax_eeg.plot([], [], label='TP10 (Right Ear)', color='#1abc9c', linewidth=1)
        self.ax_eeg.legend(loc='upper right', ncol=4, fontsize=8)
        
        # Frequency bands (middle left)
        self.ax_bands = self.fig.add_subplot(gs[1, 0])
        self.ax_bands.set_title('Frequency Band Power', fontsize=12, fontweight='bold')
        self.ax_bands.set_ylabel('Power (µV²)')
        colors = ['#3498db', '#9b59b6', '#2ecc71', '#e67e22', '#e74c3c']
        self.bars = self.ax_bands.bar(self.band_names, self.band_powers, color=colors)
        self.ax_bands.set_ylim(0, 100)
        
        # Gyroscope (middle right)
        self.ax_gyro = self.fig.add_subplot(gs[1, 1])
        self.ax_gyro.set_title('Head Motion (Gyroscope)', fontsize=12, fontweight='bold')
        self.ax_gyro.set_xlabel('Time (seconds)')
        self.ax_gyro.set_ylabel('Angular Velocity (°/s)')
        self.ax_gyro.grid(True, alpha=0.3)
        
        self.line_gyro_x, = self.ax_gyro.plot([], [], label='X', color='#e74c3c', linewidth=1.5)
        self.line_gyro_y, = self.ax_gyro.plot([], [], label='Y', color='#2ecc71', linewidth=1.5)
        self.line_gyro_z, = self.ax_gyro.plot([], [], label='Z', color='#3498db', linewidth=1.5)
        self.ax_gyro.legend(loc='upper right', fontsize=8)
        
        # Status text (bottom)
        self.ax_status = self.fig.add_subplot(gs[2, :])
        self.ax_status.axis('off')
        self.status_text = self.ax_status.text(0.5, 0.5, 'Initializing...', 
                                               ha='center', va='center', 
                                               fontsize=14, color='#2ecc71')
    
    def calculate_band_powers(self, eeg_data, fs=256):
        """Calculate power in different frequency bands."""
        if len(eeg_data) < 128:
            return [0.1, 0.1, 0.1, 0.1, 0.1]
        
        # Compute FFT
        fft_vals = np.fft.rfft(eeg_data)
        fft_freq = np.fft.rfftfreq(len(eeg_data), 1.0/fs)
        fft_power = np.abs(fft_vals) ** 2
        
        # Define frequency bands
        bands = [(0.5, 4), (4, 8), (8, 13), (13, 30), (30, 50)]
        
        band_powers = []
        for low, high in bands:
            idx = np.where((fft_freq >= low) & (fft_freq <= high))
            power = np.mean(fft_power[idx]) if len(idx[0]) > 0 else 0.1
            band_powers.append(power)
        
        return band_powers
    
    def collect_data(self):
        """Background thread to collect data from Muse."""
        self.start_time = time.time()
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
                
                # Calculate frequency bands every 50 samples
                if sample_count % 50 == 0 and len(self.eeg_af7) >= 128:
                    self.band_powers = self.calculate_band_powers(list(self.eeg_af7))
            
            # Read Gyroscope
            gyro_data = self.muse.read_gyro_sample()
            if gyro_data and gyro_data['x'] is not None:
                self.gyro_time.append(current_time)
                self.gyro_x.append(gyro_data['x'])
                self.gyro_y.append(gyro_data['y'])
                self.gyro_z.append(gyro_data['z'])
    
    def update_plot(self, frame):
        """Update the plots with new data."""
        # Update EEG waveforms
        if len(self.eeg_time) > 0:
            times = list(self.eeg_time)
            self.line_tp9.set_data(times, list(self.eeg_tp9))
            self.line_af7.set_data(times, list(self.eeg_af7))
            self.line_af8.set_data(times, list(self.eeg_af8))
            self.line_tp10.set_data(times, list(self.eeg_tp10))
            
            # Update x-axis limits
            if times:
                self.ax_eeg.set_xlim(max(0, times[-1] - 10), times[-1] + 0.5)
                
                # Update y-axis limits based on data
                all_data = list(self.eeg_tp9) + list(self.eeg_af7) + list(self.eeg_af8) + list(self.eeg_tp10)
                if all_data:
                    data_min, data_max = min(all_data), max(all_data)
                    margin = (data_max - data_min) * 0.1
                    self.ax_eeg.set_ylim(data_min - margin, data_max + margin)
        
        # Update frequency bands
        for bar, height in zip(self.bars, self.band_powers):
            bar.set_height(height)
        
        # Update y-axis limit for bands
        max_power = max(self.band_powers) if self.band_powers else 100
        self.ax_bands.set_ylim(0, max_power * 1.2)
        
        # Update gyroscope
        if len(self.gyro_time) > 0:
            gyro_times = list(self.gyro_time)
            self.line_gyro_x.set_data(gyro_times, list(self.gyro_x))
            self.line_gyro_y.set_data(gyro_times, list(self.gyro_y))
            self.line_gyro_z.set_data(gyro_times, list(self.gyro_z))
            
            if gyro_times:
                self.ax_gyro.set_xlim(max(0, gyro_times[-1] - 10), gyro_times[-1] + 0.5)
                
                all_gyro = list(self.gyro_x) + list(self.gyro_y) + list(self.gyro_z)
                if all_gyro:
                    gyro_min, gyro_max = min(all_gyro), max(all_gyro)
                    margin = (gyro_max - gyro_min) * 0.1
                    self.ax_gyro.set_ylim(gyro_min - margin, gyro_max + margin)
        
        # Update status
        if len(self.eeg_time) > 0:
            self.status_text.set_text(f'✓ Streaming | Samples: {len(self.eeg_time)} | '
                                     f'Time: {self.eeg_time[-1]:.1f}s')
            self.status_text.set_color('#2ecc71')
        else:
            self.status_text.set_text('⚠ Waiting for data...')
            self.status_text.set_color('#e67e22')
        
        return (self.line_tp9, self.line_af7, self.line_af8, self.line_tp10,
                *self.bars, self.line_gyro_x, self.line_gyro_y, self.line_gyro_z,
                self.status_text)
    
    def start(self):
        """Connect to Muse and start visualization."""
        print("=" * 60)
        print("Muse S Simple Visualizer")
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
        
        print("\n✓ Visualization starting...")
        print("✓ Close the window to stop\n")
        
        # Start animation
        ani = animation.FuncAnimation(
            self.fig, 
            self.update_plot, 
            interval=50,  # Update every 50ms (20 FPS)
            blit=True,
            cache_frame_data=False
        )
        
        try:
            plt.show()
        except KeyboardInterrupt:
            print("\n\nStopping...")
        finally:
            self.is_running = False
            if self.data_thread:
                self.data_thread.join(timeout=2)
            print("Visualization stopped.")


def main():
    """Main function to run the visualizer."""
    visualizer = MuseVisualizer(buffer_size=500)
    visualizer.start()


if __name__ == "__main__":
    main()
