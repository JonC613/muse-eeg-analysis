# Muse S EEG Brain Activity Analysis Suite - AI Coding Instructions

## Project Architecture

This is a **Python-based EEG data acquisition and analysis platform** for Muse S headband using Lab Streaming Layer (LSL) protocol. The architecture follows a layered design:

**Data Flow:** Muse S Headband → LSL Stream (BlueMuse/muselsl) → MuseInterface → Recorder/Visualizer/Analyzer → CSV Storage → AI Analysis

**Core Components:**
- `muse_interface.py` - Low-level LSL data acquisition (4 streams: EEG, PPG, Gyroscope, Accelerometer)
- `muse_recorder.py` - Session recording to CSV with date-based organization (`recordings/YYYY-MM-DD/`)
- `muse_visualizer.py` & `muse_dashboard.py` - Real-time visualization (matplotlib desktop / Plotly web)
- `muse_ai_analyzer.py` - LLM-powered analysis using local Ollama/LM Studio server
- `muse_sleep_analyzer.py` - Sleep stage classification using EEG frequency bands
- `muse_compare_sessions.py` - Multi-session analysis and trend detection

**Integration Points:**
- **Google Drive** (`gdrive_mindmonitor_importer.py`) - Auto-import Mind Monitor mobile recordings with ZIP extraction and format conversion
- **Mind Monitor** (`import_mindmonitor_manual.py`) - Mobile app data at 259 Hz (higher quality than BlueMuse)

## Critical Conventions

### Data Format Standards
All CSVs follow this schema (see `muse_recorder.py:25-40`):
- **Timestamps:** Three formats for cross-platform sync: `timestamp_unix` (epoch), `timestamp_iso` (ISO 8601), `elapsed_time` (session relative)
- **EEG Channels:** `eeg_tp9`, `eeg_af7`, `eeg_af8`, `eeg_tp10` (order matches Muse hardware positions)
- **PPG:** `ppg_avg` (3-channel average from Muse raw PPG data)
- **Motion:** `gyro_x/y/z`, `acc_x/y/z` for head movement tracking

Mind Monitor files use different naming: `RAW_TP9`, `RAW_AF7`, etc. The importer (`gdrive_mindmonitor_importer.py:220-250`) auto-converts these to standard format.

### Frequency Band Analysis Pattern
Every analyzer implements the same FFT-based band calculation (see `muse_recorder.py:212-258`):
```python
# Standard bands used throughout codebase
Delta: 0.5-4 Hz (deep sleep)
Theta: 4-8 Hz (meditation, creativity)
Alpha: 8-13 Hz (relaxed awareness)
Beta: 13-30 Hz (focus, concentration)
Gamma: 30-50 Hz (high-level cognition)
```
**Implementation:** Use scipy welch PSD with 256 Hz sampling rate, 2-second windows (nperseg=512). See `MuseAnalyzer.calculate_band_powers()` for reference implementation.

### File Organization
- **Date-based folders:** `recordings/YYYY-MM-DD/` auto-created for each session
- **Naming convention:** `muse_session_{name}_{timestamp}.csv` or `muse_mindmonitor_{original_name}_{timestamp}.csv`
- **Metadata:** JSON sidecar files store session info (`.metadata.json`)
- **AI outputs:** `.ai_insights.txt` files stored alongside CSVs
- **Manual imports:** `recordings/manual/` for drag-and-drop, `recordings/manual/processed/` for originals

## Development Workflows

### Running a Full Session
```powershell
# 1. Ensure BlueMuse/muselsl is streaming (prerequisite)
# 2. Record session
python muse_recorder.py 60 meditation_session

# 3. Analyze with AI
python muse_ai_analyzer.py recordings/YYYY-MM-DD/muse_session_meditation_session_*.csv

# 4. Compare with previous sessions
python muse_compare_sessions.py session1.csv session2.csv
```

### Quick Analysis Script
Use `analyze_latest.bat` wrapper that auto-finds latest CSV and runs analyzer.

### Mind Monitor Mobile Workflow
1. Record on phone via Mind Monitor app → auto-uploads to Google Drive
2. Run: `python gdrive_mindmonitor_importer.py` (interactive selection) or drag files to `recordings/manual/` and run `python import_mindmonitor_manual.py`
3. Files auto-converted to Muse format with metadata extraction

### Testing Data Availability
Use `muse_connection_test.py` to verify LSL streams are active before recording.

## External Dependencies

### Required Services
- **BlueMuse** (Windows) or **muselsl** (Mac/Linux) - Must be running and streaming for live data acquisition
- **Ollama/LM Studio** - Local LLM server for AI analysis (default: `http://192.168.68.123:1234`)
  - Configured in `muse_ai_analyzer.py:16` - update `llm_url` parameter
  - Falls back to quick summary mode if unreachable

### API Integrations
- **Google Drive API:** OAuth2 credentials in `gdrive_credentials.json`, tokens in `gdrive_token.json`
  - First run opens browser for authorization
  - Requires Drive API enabled in Google Cloud Console (see `GDRIVE_SETUP.md`)

## Common Patterns

### Error Handling for Missing Data
All analyzers handle both old and new timestamp formats:
```python
# Pattern used in muse_ai_analyzer.py:27-32
if 'elapsed_time' in self.df.columns:
    time_col = 'elapsed_time'
elif 'timestamp' in self.df.columns:
    time_col = 'timestamp'
```

### Threading for Real-Time Collection
Visualizers use daemon threads for non-blocking data acquisition (see `muse_visualizer.py:119-148`). Main thread handles plotting, background thread pulls LSL samples.

### Audio Notifications
Windows-specific: `winsound.Beep(frequency, duration)` signals recording completion (see `muse_recorder.py:184-200`). Use try/except for cross-platform compatibility.

## Key Files Reference
- **Architecture overview:** `PROJECT_SUMMARY.md` (includes real session results with % distributions)
- **Mobile setup:** `MIND_MONITOR_WORKFLOW.md` (259 Hz mobile recording guide)
- **Google Drive troubleshooting:** `GDRIVE_TROUBLESHOOTING.md`
- **Quick analysis:** `analyze_latest.bat` (finds most recent CSV automatically)

## Implementation Patterns

### FFT Band Power Calculation
Standard implementation across all analyzers (see `muse_recorder.py:212-258`):
```python
# Use scipy.signal.welch for production, or numpy FFT for real-time
from scipy import signal
window_size = 512  # 2 seconds at 256 Hz
hop_size = 128     # 50% overlap

# For each window segment:
fft_vals = np.fft.rfft(segment)
fft_freq = np.fft.rfftfreq(window_size, 1.0/fs)
fft_power = np.abs(fft_vals) ** 2

# Extract band power by frequency range
for band_name, (low, high) in bands.items():
    idx = np.where((fft_freq >= low) & (fft_freq <= high))
    power = np.mean(fft_power[idx])
```

### Real-Time Visualization Setup
Matplotlib pattern for live updating (see `muse_visualizer.py:48-100`):
```python
# Use GridSpec for flexible layouts
from matplotlib.gridspec import GridSpec
gs = GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.3)

# Dark theme for EEG displays
plt.style.use('dark_background')

# Thread-safe data collection
import threading
def collect_data():
    while self.is_running:
        sample, timestamp = self.muse.read_eeg_sample()
        with self.data_lock:
            self.buffer.append(sample)
threading.Thread(target=collect_data, daemon=True).start()

# Animation with FuncAnimation
from matplotlib.animation import FuncAnimation
ani = FuncAnimation(fig, update_plot, interval=50, blit=False)
```

### Data Export Formats
All analyzers follow consistent export patterns:
- **CSV primary format:** Timestamped sensor data with headers
- **JSON metadata:** Session info in `.metadata.json` sidecar files
- **JSON reports:** Sleep analysis exports to `.sleep_report.json` with stage classifications
- **Text insights:** AI analysis saves to `.ai_insights.txt` for human readability
- **PNG plots:** Generated visualizations saved alongside CSVs with `_analysis.png` suffix

## Hardware Troubleshooting

### LSL Stream Connection Issues
Common problems and solutions (see `muse_connection_test.py:35-58`):

**No streams found:**
```powershell
# 1. Verify BlueMuse is running
# 2. Check Windows Services for "Lab Streaming Layer"
# 3. Test with connection checker:
python muse_connection_test.py
```

**Intermittent disconnections:**
- Muse S battery below 20% causes unstable streaming
- Bluetooth interference from other devices (move away from WiFi routers)
- Poor electrode contact (see quality checker below)

**Electrode Contact Quality:**
```powershell
python muse_connection_test.py
# Shows real-time quality for each electrode (TP9, AF7, AF8, TP10)
# Thresholds: std < 20 = excellent, < 50 = good, < 100 = fair
```

**BlueMuse vs muselsl:**
- BlueMuse (Windows): ~256 Hz, easier setup, GUI control
- muselsl (Mac/Linux): Command-line, requires `muselsl stream` before recording
- Mind Monitor mobile: 259 Hz (best quality), requires import workflow

### LM Studio/Ollama Configuration
AI analysis fallback behavior (see `muse_ai_analyzer.py:210-230`):

**Connection handling:**
```python
# Default URL: http://192.168.68.123:1234
# Falls back to quick summary if unreachable
try:
    response = requests.post(llm_url + "/v1/chat/completions", ...)
except requests.exceptions.ConnectionError:
    print("Using quick summary mode (no AI required)")
    return self.get_quick_summary()
```

**Server requirements:**
- Any OpenAI-compatible endpoint works (Ollama, LM Studio, vLLM)
- Model must support chat completions endpoint
- Recommended: 7B+ parameter models for quality insights
- Timeout: 120 seconds for long sessions (adjustable in code)

### Performance Optimization

**Recording large sessions:**
- CSV writing is buffered - no performance impact up to 1 hour sessions
- Memory usage: ~1 MB per minute of recording (4 EEG + PPG + motion)
- For overnight sessions: Use `muse_sleep_analyzer.py` which processes in 30-second windows

**Visualization frame rates:**
- Desktop visualizer: 20 FPS cap (50ms interval) - sufficient for 256 Hz data display
- Web dashboard: 2 FPS updates to reduce browser load
- Reduce `buffer_size` from 500 to 250 samples if experiencing lag

**Analysis speed:**
- FFT calculation: ~1 second per minute of data
- AI analysis: 10-60 seconds depending on LLM and session length
- Multi-session comparison: Parallel processing not implemented - sequential only

## Testing Approach
No formal test suite. Test with actual hardware:
1. `python muse_connection_test.py` - Verify LSL streams and electrode quality (10-second test)
2. `python check_muse_ppg.py` - Validate PPG data quality and heart rate detection
3. Record short 10-second sessions for rapid iteration: `python muse_recorder.py 10 test`
4. Compare outputs with known-good sessions in `recordings/` using `muse_compare_sessions.py`
