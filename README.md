# Muse S Headband Interface

A simple Python application to connect to and read data from the Muse S headband using Lab Streaming Layer (LSL).

## Prerequisites

1. **Muse S Headband** - Turned on and charged
2. **Bluetooth Connection** - Pair your Muse S with your computer
3. **BlueMuse** (Windows) or **Muse LSL** - Software to stream Muse data over LSL
   - Windows: Download [BlueMuse](https://github.com/kowalej/BlueMuse/releases)
   - Mac/Linux: Use [muselsl](https://github.com/alexandrebarachant/muse-lsl)

## Installation

1. Activate your virtual environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Run the main interface:
```powershell
python muse_interface.py
```

This will:
- Search for Muse data streams (EEG, PPG, Gyroscope, Accelerometer)
- Connect to all available streams
- Monitor and display real-time data for 30 seconds

### Custom Usage

You can also use the MuseInterface class in your own scripts:

```python
from muse_interface import MuseInterface

# Create interface
muse = MuseInterface()

# Connect to Muse
if muse.connect():
    # Read single EEG sample
    eeg_data = muse.read_eeg_sample()
    print(f"EEG channels: {eeg_data['channels']}")
    
    # Read PPG (heart rate) sample
    ppg_data = muse.read_ppg_sample()
    print(f"PPG values: {ppg_data['values']}")
    
    # Monitor for custom duration
    muse.monitor(duration=60)  # Monitor for 60 seconds
```

## Data Streams

The Muse S provides the following data streams:

- **EEG**: 4 channels (TP9, AF7, AF8, TP10) - Brain wave activity
- **PPG**: Photoplethysmography - Heart rate and blood flow
- **Gyroscope**: 3-axis rotation data
- **Accelerometer**: 3-axis movement data

## Troubleshooting

If you can't connect to the Muse:

1. Ensure Muse S is turned on (LED should be blinking or solid)
2. Make sure Muse is paired via Bluetooth with your computer
3. Start BlueMuse (Windows) or muse-lsl stream (Mac/Linux)
4. In BlueMuse, click "Start Streaming" after the device appears
5. Check that the streaming software shows data flowing

## Notes

## Privacy

This repository contains reusable integration and analysis code only. Generated recordings, exports, research notes, credentials, and analysis artifacts are intentionally excluded from version control. Use synthetic data for demos and never commit personal biometric or location data.

- The app uses Lab Streaming Layer (LSL) protocol
- Default monitoring duration is 30 seconds
- Press Ctrl+C to stop monitoring early
- EEG values are in microvolts (μV)
