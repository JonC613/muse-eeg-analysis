"""
Muse S Headband Interface
A simple Python application to connect to and read data from Muse S headband.
"""

from pylsl import StreamInlet, resolve_byprop
import time
import numpy as np


class MuseInterface:
    """Interface for connecting to and reading data from Muse S headband."""
    
    def __init__(self):
        self.eeg_inlet = None
        self.ppg_inlet = None
        self.gyro_inlet = None
        self.acc_inlet = None
        
    def connect(self, timeout=10):
        """
        Connect to Muse S headband streams.
        
        Args:
            timeout: Time in seconds to wait for streams
            
        Returns:
            bool: True if at least one stream connected successfully
        """
        print("Searching for Muse streams...")
        
        try:
            # Look for EEG stream
            print("Looking for EEG stream...")
            eeg_streams = resolve_byprop('type', 'EEG', timeout=timeout)
            if eeg_streams:
                self.eeg_inlet = StreamInlet(eeg_streams[0])
                print(f"✓ Connected to EEG stream: {eeg_streams[0].name()}")
            else:
                print("✗ No EEG stream found")
                
            # Look for PPG stream (heart rate)
            print("Looking for PPG stream...")
            ppg_streams = resolve_byprop('type', 'PPG', timeout=timeout)
            if ppg_streams:
                self.ppg_inlet = StreamInlet(ppg_streams[0])
                print(f"✓ Connected to PPG stream: {ppg_streams[0].name()}")
            else:
                print("✗ No PPG stream found")
                
            # Look for Gyroscope stream
            print("Looking for Gyroscope stream...")
            gyro_streams = resolve_byprop('type', 'Gyroscope', timeout=timeout)
            if gyro_streams:
                self.gyro_inlet = StreamInlet(gyro_streams[0])
                print(f"✓ Connected to Gyroscope stream: {gyro_streams[0].name()}")
            else:
                print("✗ No Gyroscope stream found")
                
            # Look for Accelerometer stream
            print("Looking for Accelerometer stream...")
            acc_streams = resolve_byprop('type', 'Accelerometer', timeout=timeout)
            if acc_streams:
                self.acc_inlet = StreamInlet(acc_streams[0])
                print(f"✓ Connected to Accelerometer stream: {acc_streams[0].name()}")
            else:
                print("✗ No Accelerometer stream found")
                
        except Exception as e:
            print(f"Error during connection: {e}")
            return False
            
        # Check if at least one stream connected
        connected = any([self.eeg_inlet, self.ppg_inlet, self.gyro_inlet, self.acc_inlet])
        if connected:
            print("\n✓ Successfully connected to Muse S!")
        else:
            print("\n✗ Failed to connect to any Muse streams")
            print("\nMake sure:")
            print("1. Muse S is turned on and paired via Bluetooth")
            print("2. Muse streaming software (e.g., BlueMuse on Windows) is running")
            print("3. The headband is streaming data")
            
        return connected
    
    def read_eeg_sample(self):
        """Read a single EEG sample."""
        if not self.eeg_inlet:
            return None
            
        sample, timestamp = self.eeg_inlet.pull_sample(timeout=1.0)
        if sample is None:
            return None
            
        return {
            'timestamp': timestamp,
            'channels': sample,
            'tp9': sample[0] if len(sample) > 0 else None,
            'af7': sample[1] if len(sample) > 1 else None,
            'af8': sample[2] if len(sample) > 2 else None,
            'tp10': sample[3] if len(sample) > 3 else None,
        }
    
    def read_ppg_sample(self):
        """Read a single PPG (heart rate) sample."""
        if not self.ppg_inlet:
            return None
            
        sample, timestamp = self.ppg_inlet.pull_sample(timeout=1.0)
        if sample is None:
            return None
            
        return {
            'timestamp': timestamp,
            'values': sample
        }
    
    def read_gyro_sample(self):
        """Read a single gyroscope sample."""
        if not self.gyro_inlet:
            return None
            
        sample, timestamp = self.gyro_inlet.pull_sample(timeout=1.0)
        if sample is None:
            return None
            
        return {
            'timestamp': timestamp,
            'x': sample[0] if len(sample) > 0 else None,
            'y': sample[1] if len(sample) > 1 else None,
            'z': sample[2] if len(sample) > 2 else None,
        }
    
    def read_acc_sample(self):
        """Read a single accelerometer sample."""
        if not self.acc_inlet:
            return None
            
        sample, timestamp = self.acc_inlet.pull_sample(timeout=1.0)
        if sample is None:
            return None
            
        return {
            'timestamp': timestamp,
            'x': sample[0] if len(sample) > 0 else None,
            'y': sample[1] if len(sample) > 1 else None,
            'z': sample[2] if len(sample) > 2 else None,
        }
    
    def monitor(self, duration=10):
        """
        Monitor and display data from all available streams.
        
        Args:
            duration: How long to monitor in seconds
        """
        print(f"\nMonitoring Muse data for {duration} seconds...\n")
        start_time = time.time()
        
        while time.time() - start_time < duration:
            print(f"\r[{time.time() - start_time:.1f}s] ", end="")
            
            # Read EEG
            if self.eeg_inlet:
                eeg_data = self.read_eeg_sample()
                if eeg_data and eeg_data['channels']:
                    eeg_avg = np.mean(eeg_data['channels'])
                    print(f"EEG: {eeg_avg:7.2f}μV | ", end="")
            
            # Read PPG
            if self.ppg_inlet:
                ppg_data = self.read_ppg_sample()
                if ppg_data and ppg_data['values']:
                    ppg_avg = np.mean(ppg_data['values'])
                    print(f"PPG: {ppg_avg:7.2f} | ", end="")
            
            # Read Gyro
            if self.gyro_inlet:
                gyro_data = self.read_gyro_sample()
                if gyro_data and gyro_data['x'] is not None:
                    print(f"Gyro: ({gyro_data['x']:6.2f}, {gyro_data['y']:6.2f}, {gyro_data['z']:6.2f}) | ", end="")
            
            # Read Accelerometer
            if self.acc_inlet:
                acc_data = self.read_acc_sample()
                if acc_data and acc_data['x'] is not None:
                    print(f"Acc: ({acc_data['x']:6.2f}, {acc_data['y']:6.2f}, {acc_data['z']:6.2f})", end="")
            
            time.sleep(0.1)
        
        print("\n\nMonitoring complete!")


def main():
    """Main function to run the Muse interface."""
    print("=" * 60)
    print("Muse S Headband Interface")
    print("=" * 60)
    
    # Create interface
    muse = MuseInterface()
    
    # Connect to Muse
    if not muse.connect(timeout=10):
        print("\nFailed to connect. Exiting...")
        return
    
    # Monitor data
    try:
        muse.monitor(duration=30)
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    
    print("\nSession complete!")


if __name__ == "__main__":
    main()
