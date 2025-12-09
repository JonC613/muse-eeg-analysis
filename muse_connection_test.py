"""
Muse S Connection Quality Test
Real-time electrode contact and signal quality checker
"""

import time
import numpy as np
from pylsl import StreamInlet, resolve_bypred
import winsound


class MuseConnectionTester:
    """Test Muse S electrode connection quality in real-time."""
    
    def __init__(self):
        """Initialize connection tester."""
        self.eeg_inlet = None
        self.test_duration = 10  # seconds
        self.sample_buffer = {
            'tp9': [],
            'af7': [],
            'af8': [],
            'tp10': []
        }
        
        # Quality thresholds (based on EEG signal characteristics)
        self.thresholds = {
            'excellent': {'std_max': 20, 'mean_range': (-50, 50)},
            'good': {'std_max': 50, 'mean_range': (-100, 100)},
            'fair': {'std_max': 100, 'mean_range': (-200, 200)},
            'poor': {'std_max': float('inf'), 'mean_range': (-float('inf'), float('inf'))}
        }
    
    def connect_to_muse(self):
        """Connect to Muse S EEG stream."""
        print("Searching for Muse S...")
        print("Make sure BlueMuse is running and streaming data.\n")
        
        try:
            # Look for any Muse EEG stream
            print("Looking for Muse EEG stream...")
            streams = resolve_bypred("type='EEG'", timeout=10)
            
            if not streams:
                print("❌ No EEG stream found!")
                print("\nTroubleshooting:")
                print("1. Open BlueMuse")
                print("2. Click 'Start Streaming' on your Muse device")
                print("3. Verify headband is on and connected")
                print("4. Check that BlueMuse shows 'Streaming' status")
                return False
            
            self.eeg_inlet = StreamInlet(streams[0])
            info = self.eeg_inlet.info()
            
            print(f"✓ Connected to: {info.name()}")
            print(f"  Channels: {info.channel_count()}")
            print(f"  Sample rate: {info.nominal_srate()} Hz\n")
            
            return True
            
        except Exception as e:
            print(f"❌ Error connecting: {e}")
            return False
    
    def collect_sample_data(self):
        """Collect sample data for analysis."""
        print(f"Collecting {self.test_duration} seconds of data...")
        print("Stay still and relaxed.\n")
        
        start_time = time.time()
        sample_count = 0
        
        while time.time() - start_time < self.test_duration:
            # Get sample
            sample, timestamp = self.eeg_inlet.pull_sample(timeout=1.0)
            
            if sample:
                # Store in buffers (TP9, AF7, AF8, TP10)
                self.sample_buffer['tp9'].append(sample[0])
                self.sample_buffer['af7'].append(sample[1])
                self.sample_buffer['af8'].append(sample[2])
                self.sample_buffer['tp10'].append(sample[3])
                
                sample_count += 1
                
                # Progress indicator
                elapsed = time.time() - start_time
                if int(elapsed) % 2 == 0 and elapsed > 0:
                    progress = int((elapsed / self.test_duration) * 100)
                    print(f"\rProgress: {progress}% ({sample_count} samples)", end="", flush=True)
        
        print(f"\n✓ Collected {sample_count} samples\n")
        return sample_count > 0
    
    def analyze_signal_quality(self):
        """Analyze signal quality for each electrode."""
        print("="*70)
        print("ELECTRODE SIGNAL QUALITY REPORT")
        print("="*70)
        
        results = {}
        
        for channel, data in self.sample_buffer.items():
            if not data:
                continue
            
            # Calculate statistics
            data_array = np.array(data)
            mean = np.mean(data_array)
            std = np.std(data_array)
            min_val = np.min(data_array)
            max_val = np.max(data_array)
            range_val = max_val - min_val
            
            # Determine quality
            quality = self._determine_quality(mean, std)
            
            results[channel] = {
                'mean': mean,
                'std': std,
                'min': min_val,
                'max': max_val,
                'range': range_val,
                'quality': quality
            }
        
        return results
    
    def _determine_quality(self, mean, std):
        """Determine signal quality based on statistics."""
        if std <= self.thresholds['excellent']['std_max'] and \
           self.thresholds['excellent']['mean_range'][0] <= mean <= self.thresholds['excellent']['mean_range'][1]:
            return 'EXCELLENT'
        elif std <= self.thresholds['good']['std_max'] and \
             self.thresholds['good']['mean_range'][0] <= mean <= self.thresholds['good']['mean_range'][1]:
            return 'GOOD'
        elif std <= self.thresholds['fair']['std_max'] and \
             self.thresholds['fair']['mean_range'][0] <= mean <= self.thresholds['fair']['mean_range'][1]:
            return 'FAIR'
        else:
            return 'POOR'
    
    def print_results(self, results):
        """Print formatted results."""
        quality_colors = {
            'EXCELLENT': '✓',
            'GOOD': '✓',
            'FAIR': '⚠',
            'POOR': '✗'
        }
        
        quality_order = {
            'EXCELLENT': 0,
            'GOOD': 1,
            'FAIR': 2,
            'POOR': 3
        }
        
        # Print header
        print(f"\n{'Electrode':<12} {'Quality':<12} {'Mean (µV)':<12} {'Std (µV)':<12} {'Range (µV)':<12}")
        print("-"*70)
        
        # Print each channel
        for channel, stats in results.items():
            quality = stats['quality']
            symbol = quality_colors.get(quality, '?')
            
            print(f"{channel.upper():<12} {symbol} {quality:<10} {stats['mean']:>10.1f} {stats['std']:>11.1f} {stats['range']:>11.1f}")
        
        print("-"*70)
        
        # Overall assessment
        worst_quality = max(results.values(), key=lambda x: quality_order[x['quality']])['quality']
        
        print(f"\nOVERALL STATUS: {quality_colors[worst_quality]} {worst_quality}")
        print()
        
        # Recommendations
        self._print_recommendations(results)
        
        # Play sound based on quality
        self._play_quality_sound(worst_quality)
    
    def _print_recommendations(self, results):
        """Print specific recommendations based on results."""
        print("RECOMMENDATIONS:")
        print("-"*70)
        
        has_issues = False
        
        for channel, stats in results.items():
            quality = stats['quality']
            
            if quality == 'POOR':
                has_issues = True
                print(f"\n{channel.upper()} - POOR CONTACT:")
                print(f"  • Signal noise is very high (std: {stats['std']:.1f} µV)")
                
                if channel in ['af7', 'af8']:
                    print(f"  → Check forehead electrode position")
                    print(f"  → Push hair away from electrode")
                    print(f"  → Dampen electrode slightly")
                    print(f"  → Ensure flat contact on forehead")
                else:
                    print(f"  → Check ear electrode position (behind ear)")
                    print(f"  → Adjust ear loop for snug fit")
                    print(f"  → Ensure contact on mastoid bone")
            
            elif quality == 'FAIR':
                has_issues = True
                print(f"\n{channel.upper()} - FAIR CONTACT:")
                print(f"  • Signal has moderate noise (std: {stats['std']:.1f} µV)")
                
                if channel in ['af7', 'af8']:
                    print(f"  → Try repositioning 2-3mm up or down")
                    print(f"  → Check for hair interference")
                else:
                    print(f"  → Adjust ear sensor placement")
                    print(f"  → Ensure firm contact")
        
        if not has_issues:
            print("\n✓ All electrodes have good contact!")
            print("  → You're ready to record high-quality data")
            print("  → Consider running a session now")
        else:
            print("\n⚠ Adjust electrode placement and re-test before recording")
        
        print()
    
    def _play_quality_sound(self, quality):
        """Play sound based on overall quality."""
        try:
            if quality == 'EXCELLENT' or quality == 'GOOD':
                # Success: 3 ascending beeps
                for freq in [800, 1000, 1200]:
                    winsound.Beep(freq, 150)
                    time.sleep(0.05)
            elif quality == 'FAIR':
                # Warning: 2 medium beeps
                for _ in range(2):
                    winsound.Beep(600, 200)
                    time.sleep(0.1)
            else:
                # Error: 3 descending beeps
                for freq in [600, 500, 400]:
                    winsound.Beep(freq, 200)
                    time.sleep(0.05)
        except:
            pass  # Ignore sound errors
    
    def run_test(self):
        """Run the complete connection test."""
        print("="*70)
        print("MUSE S CONNECTION QUALITY TEST")
        print("="*70)
        print()
        print("This test will:")
        print("  1. Connect to your Muse S headband")
        print("  2. Collect 10 seconds of EEG data")
        print("  3. Analyze signal quality for each electrode")
        print("  4. Provide recommendations for improvement")
        print()
        print("Make sure:")
        print("  ✓ Muse S is on your head")
        print("  ✓ BlueMuse is running and streaming")
        print("  ✓ You're sitting comfortably")
        print()
        input("Press ENTER to start the test...")
        print()
        
        # Connect
        if not self.connect_to_muse():
            return
        
        # Collect data
        if not self.collect_sample_data():
            print("❌ Failed to collect data")
            return
        
        # Analyze
        results = self.analyze_signal_quality()
        
        # Print results
        self.print_results(results)
        
        # Ask to re-test
        print("\nOptions:")
        print("  1. Re-test (after adjusting electrodes)")
        print("  2. Exit")
        choice = input("\nChoice (1/2): ").strip()
        
        if choice == '1':
            # Clear buffers
            for channel in self.sample_buffer:
                self.sample_buffer[channel] = []
            print("\n" + "="*70 + "\n")
            self.run_test()


def main():
    """Main function."""
    tester = MuseConnectionTester()
    tester.run_test()


if __name__ == "__main__":
    main()
