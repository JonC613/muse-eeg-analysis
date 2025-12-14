# Mind Monitor Optimized Workflow

Mind Monitor is achieving perfect 259 Hz sampling - better than BlueMuse! Here's how to optimize your workflow.

## Current Setup Assessment

✓ **Sample Rate:** 259 Hz (101% of target - excellent!)
✓ **Data Quality:** 99% complete samples
✓ **Format Compatibility:** Auto-converts to Muse format
✓ **Mobile Recording:** Record anywhere, anytime

---

## Optimal Mind Monitor Settings

### 1. Recording Configuration

**Open Mind Monitor App → Settings:**

1. **Sampling Mode:**
   - ✓ **"Continuous Mode"** (already enabled - you're getting 259 Hz)
   - ✗ NOT "1 Second Polling" (creates sparse data)

2. **Data Channels to Record:**
   - ✓ RAW EEG (TP9, AF7, AF8, TP10)
   - ✓ PPG (Heart Rate)
   - ✓ Gyroscope (Movement tracking)
   - ✓ Accelerometer (Stillness detection)
   - ○ Optional: FFT bands (already calculated in post-processing)

3. **File Format:**
   - ✓ CSV export
   - ✓ Include timestamps
   - ✓ Include all sensor data

4. **Google Drive Sync:**
   - ✓ Auto-upload enabled (for backup)
   - Location: Choose dedicated folder (e.g., "MuseEEG")

---

## Streamlined Workflow

### Daily Meditation/Recording Sessions

```
1. PREPARE (30 seconds)
   → Open Mind Monitor app
   → Put on Muse S headband
   → Check electrode contact (app shows quality)
   → Adjust for good signal (all green)

2. RECORD (your session duration)
   → Tap "Record" in Mind Monitor
   → Do your meditation/activity
   → App auto-saves to phone + Google Drive

3. IMPORT TO PC (automated)
   
   Option A - Manual Import (fast):
   → Export CSV from Mind Monitor
   → Save to: recordings\manual\
   → Run: python import_mindmonitor_manual.py
   
   Option B - Google Drive (automatic):
   → Wait for auto-sync (usually instant)
   → Run: python gdrive_mindmonitor_importer.py
   → Select file or import all

4. ANALYZE (automatic)
   → Run: python muse_ai_analyzer.py recordings\YYYY-MM-DD\filename.csv
   → Get instant AI insights from LM Studio
   → View brainwave distribution, meditation quality, recommendations
```

---

## File Organization Best Practices

### Mind Monitor Export Naming
Files export as: `mindMonitor_YYYY-MM-DD--HH-MM-SS_*.csv`

### After Import
Auto-organized to:
```
recordings/
├── 2025-12-08/
│   ├── muse_mindmonitor_mindMonitor_2025-12-08--20-21-22_*.csv
│   ├── muse_mindmonitor_mindMonitor_2025-12-08--20-21-22_*.metadata.json
│   └── muse_mindmonitor_mindMonitor_2025-12-08--20-21-22_*.ai_insights.txt
└── manual/
    └── processed/  (archived originals)
```

---

## Quick Analysis Commands

### 1. Import Latest Mind Monitor File
```powershell
python import_mindmonitor_manual.py
```
Auto-processes all files in `recordings\manual\`

### 2. AI Analysis (LM Studio)
```powershell
python muse_ai_analyzer.py recordings\2025-12-08\muse_mindmonitor_*.csv
```

### 3. Visualize Session
```powershell
python muse_visualizer.py recordings\2025-12-08\muse_mindmonitor_*.csv
```

### 4. Compare Two Sessions
```powershell
python muse_compare_sessions.py session1.csv session2.csv
```

### 5. Sleep Analysis
```powershell
python muse_sleep_analyzer.py recordings\2025-12-08\muse_mindmonitor_*.csv
```

### 6. CPAP Correlation (for overnight recordings)
```powershell
python muse_cpap_correlator.py recordings\muse_*.csv "D:\DATALOG\YYYYMMDD\*_BRP.cpap_report.json"
```

---

## Automation Scripts

### Create Quick-Launch Batch File

**`analyze_latest.bat`:**
```batch
@echo off
cd /d "C:\dev\musepython"
call venv\Scripts\activate.bat

echo Importing Mind Monitor files...
python import_mindmonitor_manual.py

echo.
echo Running AI Analysis on latest...
for /f "delims=" %%i in ('dir /b /od recordings\2025-*\muse_mindmonitor_*.csv 2^>nul ^| findstr /v ".ai_insights"') do set latest=%%i
python muse_ai_analyzer.py "recordings\2025-12-08\%latest%"

pause
```

**Usage:** Just double-click `analyze_latest.bat` after exporting from Mind Monitor

---

## Session Tags & Organization

### Add Session Names
When importing manually, rename files for easy tracking:
```
mindMonitor_2025-12-08--20-21-22.csv
  → mindMonitor_meditation_morning.csv
  → mindMonitor_sleep_overnight.csv
  → mindMonitor_focus_work.csv
```

The importer preserves these names in the output.

---

## Quality Optimization Tips

### Before Recording:
1. **Electrode Contact:**
   - Mind Monitor shows signal quality in real-time
   - All 4 electrodes should be GREEN
   - If yellow/red: adjust headband position
   - Moisten contact points if dry

2. **Stillness:**
   - Find comfortable position
   - Support head if lying down
   - Minimize jaw movement

3. **Battery:**
   - Charge Muse S before sessions
   - Charge phone for longer recordings

### During Recording:
- Keep phone nearby (Bluetooth range)
- Don't switch apps (Mind Monitor running)
- Airplane mode OK (Bluetooth stays on)

### After Recording:
- Export CSV immediately
- Don't delete from app until backed up
- Copy to `recordings\manual\` or wait for Google Drive sync

---

## Advanced: Real-Time Feedback

Mind Monitor has built-in biofeedback:
- **Soundscapes:** Respond to meditation depth
- **Birds chirp** = good focus
- **Storms** = mind wandering

Pair with your analysis:
1. Record session with Mind Monitor feedback
2. Export CSV after
3. AI analysis shows objective metrics
4. Compare subjective (how it felt) vs objective (what EEG showed)

---

## Troubleshooting

### "Low sample rate" warning after import
- Check Mind Monitor settings
- Should see "Continuous Mode" not "1s Polling"
- Update Mind Monitor app if old version

### "Data quality: 50% valid EEG"
- Poor electrode contact during recording
- Check headband positioning
- May have moved during session
- Still usable but less reliable

### Google Drive import not working
- Requires OAuth setup (see GDRIVE_SETUP.md)
- Manual import is faster anyway
- Only use Google Drive for backup/sync

### File too large
- Mind Monitor CSVs can be 5-10 MB for long sessions
- Normal for high sample rate
- Python tools handle large files fine

---

## Performance Comparison

| Tool | Sample Rate | Quality | Mobility | Setup |
|------|-------------|---------|----------|-------|
| **Mind Monitor** | ✓ 259 Hz | ✓ 99% | ✓ Mobile | Easy |
| BlueMuse (current) | ✗ 52 Hz | ✓ 100% | ✗ PC only | Complex |

**Verdict:** Mind Monitor is superior for your use case.

---

## Next Steps

1. **Create analyze_latest.bat** for one-click analysis
2. **Set up weekly progress tracking:**
   ```powershell
   python muse_compare_sessions.py week1.csv week2.csv
   ```
3. **Try overnight sleep recording:**
   - Record full night with Mind Monitor
   - Run sleep_analyzer.py
   - Correlate with CPAP data

4. **Build meditation habit:**
   - Daily 10-min sessions
   - Track progress with AI analysis
   - Watch Delta/Alpha ratios improve over time

---

## Summary: Your Optimized Stack

✓ **Recording:** Mind Monitor (259 Hz, mobile, auto-backup)
✓ **Import:** `import_mindmonitor_manual.py` (instant, quality check)
✓ **Analysis:** `muse_ai_analyzer.py` (LM Studio, detailed insights)
✓ **Sleep:** `muse_cpap_correlator.py` (CPAP + EEG correlation)
✓ **Visualization:** `muse_visualizer.py` (charts, hypnograms)

**You have a complete, professional-grade EEG analysis pipeline!**
