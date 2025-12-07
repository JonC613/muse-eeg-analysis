"""
Muse S AI-Powered Analyzer using Ollama or LM Studio
Analyzes EEG data and provides insights using local LLM
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import requests


class MuseAIAnalyzer:
    """Analyze Muse S data using Ollama or LM Studio LLM for insights."""
    
    def __init__(self, csv_file, llm_url="http://localhost:11434", llm_type="ollama"):
        """
        Initialize with CSV file and LLM URL.
        
        Args:
            csv_file: Path to CSV file
            llm_url: URL of LLM server (default: http://localhost:11434 for Ollama)
            llm_type: 'ollama' or 'lmstudio' (default: 'ollama')
        """
        self.csv_file = Path(csv_file)
        self.llm_url = llm_url
        self.llm_type = llm_type.lower()
        print(f"Loading data from: {self.csv_file}")
        self.df = pd.read_csv(csv_file)
        print(f"✓ Loaded {len(self.df)} samples ({self.df['timestamp'].max():.1f} seconds)")
    
    def calculate_metrics(self):
        """Calculate key metrics from the session."""
        # EEG statistics
        eeg_channels = ['eeg_tp9', 'eeg_af7', 'eeg_af8', 'eeg_tp10']
        eeg_stats = {}
        for ch in eeg_channels:
            eeg_stats[ch] = {
                'mean': float(self.df[ch].mean()),
                'std': float(self.df[ch].std()),
                'min': float(self.df[ch].min()),
                'max': float(self.df[ch].max())
            }
        
        # Calculate frequency bands for frontal channel (AF7)
        band_powers = self._calculate_band_powers('eeg_af7')
        
        # Motion metrics
        gyro_movement = np.sqrt(
            self.df['gyro_x']**2 + 
            self.df['gyro_y']**2 + 
            self.df['gyro_z']**2
        )
        
        motion_stats = {
            'mean_movement': float(gyro_movement.mean()),
            'max_movement': float(gyro_movement.max()),
            'movement_variance': float(gyro_movement.std()),
            'still_percentage': float((gyro_movement < 10).sum() / len(gyro_movement) * 100)
        }
        
        # Heart rate from PPG (simplified)
        ppg_mean = float(self.df['ppg_avg'].mean())
        ppg_std = float(self.df['ppg_avg'].std())
        
        return {
            'duration_seconds': float(self.df['timestamp'].max()),
            'total_samples': len(self.df),
            'eeg_statistics': eeg_stats,
            'band_powers': band_powers,
            'motion': motion_stats,
            'ppg': {
                'mean': ppg_mean,
                'std': ppg_std
            }
        }
    
    def _calculate_band_powers(self, channel, fs=256):
        """Calculate average power in each frequency band."""
        eeg_data = self.df[channel].dropna().values
        
        if len(eeg_data) < 256:
            return None
        
        # Use full signal for average band power
        fft_vals = np.fft.rfft(eeg_data)
        fft_freq = np.fft.rfftfreq(len(eeg_data), 1.0/fs)
        fft_power = np.abs(fft_vals) ** 2
        
        bands = {
            'delta': (0.5, 4),    # Deep sleep
            'theta': (4, 8),      # Drowsiness, meditation
            'alpha': (8, 13),     # Relaxed, calm
            'beta': (13, 30),     # Active thinking, focus
            'gamma': (30, 50)     # High cognitive processing
        }
        
        band_powers = {}
        for band_name, (low, high) in bands.items():
            idx = np.where((fft_freq >= low) & (fft_freq <= high))
            power = float(np.mean(fft_power[idx])) if len(idx[0]) > 0 else 0
            band_powers[band_name] = power
        
        # Normalize to percentages
        total_power = sum(band_powers.values())
        if total_power > 0:
            band_powers = {k: (v/total_power)*100 for k, v in band_powers.items()}
        
        return band_powers
    
    def get_ollama_insights(self, model="llama3.2"):
        """Get AI insights using Ollama or LM Studio."""
        print(f"\n{'='*60}")
        print(f"Analyzing with {self.llm_type.upper()} ({model})...")
        print(f"{'='*60}\n")
        
        # Calculate metrics
        metrics = self.calculate_metrics()
        
        # Create prompt
        prompt = f"""You are an expert neuroscientist analyzing EEG brainwave data from a Muse S headband session.

Session Data:
- Duration: {metrics['duration_seconds']:.1f} seconds
- Total samples: {metrics['total_samples']}

Brain Wave Frequency Bands (as % of total power):
- Delta (0.5-4 Hz): {metrics['band_powers']['delta']:.1f}% - Deep sleep, unconscious
- Theta (4-8 Hz): {metrics['band_powers']['theta']:.1f}% - Drowsiness, meditation, creativity
- Alpha (8-13 Hz): {metrics['band_powers']['alpha']:.1f}% - Relaxed, calm, present
- Beta (13-30 Hz): {metrics['band_powers']['beta']:.1f}% - Active thinking, focus, alertness
- Gamma (30-50 Hz): {metrics['band_powers']['gamma']:.1f}% - Peak concentration, learning

Head Movement:
- Average movement: {metrics['motion']['mean_movement']:.1f}°/s
- Still time: {metrics['motion']['still_percentage']:.1f}% of session
- Movement variance: {metrics['motion']['movement_variance']:.1f}

EEG Signal Quality:
- Frontal left (AF7): mean={metrics['eeg_statistics']['eeg_af7']['mean']:.1f}µV, std={metrics['eeg_statistics']['eeg_af7']['std']:.1f}µV
- Frontal right (AF8): mean={metrics['eeg_statistics']['eeg_af8']['mean']:.1f}µV, std={metrics['eeg_statistics']['eeg_af8']['std']:.1f}µV

Please provide a detailed analysis covering:
1. Mental State: What does the distribution of brain wave frequencies suggest about the person's mental state during this session?
2. Focus & Attention: Evaluate their level of focus and attention based on beta/gamma waves
3. Relaxation: Assess their relaxation level based on alpha waves
4. Meditation Quality: If this was a meditation session, rate the quality
5. Movement Impact: How did physical stillness affect the data quality?
6. Recommendations: Specific suggestions to improve meditation/focus based on these patterns

Be specific, cite the actual numbers, and provide actionable insights."""

        try:
            # Call LLM API
            if self.llm_type == "lmstudio":
                # LM Studio uses OpenAI-compatible API
                response = requests.post(
                    f"{self.llm_url}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are an expert neuroscientist analyzing EEG brainwave data."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 2000
                    },
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    insight = result['choices'][0]['message']['content']
                else:
                    print(f"Error: LM Studio returned status {response.status_code}")
                    print(response.text)
                    return None
                    
            else:
                # Ollama API
                response = requests.post(
                    f"{self.llm_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    insight = result.get('response', 'No response from model')
                else:
                    print(f"Error: Ollama returned status {response.status_code}")
                    print(response.text)
                    return None
            
            print("AI INSIGHTS")
            print("=" * 60)
            print(insight)
            print("=" * 60)
            
            # Save insights to file (same directory as CSV)
            output_file = self.csv_file.with_suffix('.ai_insights.txt')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"Muse S Session AI Analysis\n")
                f.write(f"Session: {self.csv_file.name}\n")
                f.write(f"Model: {model}\n")
                f.write(f"{'='*60}\n\n")
                f.write(f"METRICS:\n")
                f.write(json.dumps(metrics, indent=2))
                f.write(f"\n\n{'='*60}\n\n")
                f.write(f"AI INSIGHTS:\n")
                f.write(insight)
            
            print(f"\n✓ Insights saved to: {output_file}")
            
            return insight
                
        except requests.exceptions.ConnectionError:
            if self.llm_type == "lmstudio":
                print(f"❌ Could not connect to LM Studio at {self.llm_url}")
                print("   Make sure LM Studio is running and serving on the correct port:")
                print("   1. Open LM Studio")
                print("   2. Load a model")
                print("   3. Start the local server (Developer tab)")
                print(f"   4. Verify URL: {self.llm_url}")
            else:
                print(f"❌ Could not connect to Ollama at {self.llm_url}")
                print("   1. Install Ollama from https://ollama.ai")
                print("   2. Run: ollama serve")
                print(f"   3. Pull model: ollama pull {model}")
            return None
        except Exception as e:
            print(f"Error calling {self.llm_type}: {e}")
            return None
    
    def get_quick_summary(self):
        """Get a quick text summary without AI."""
        metrics = self.calculate_metrics()
        bp = metrics['band_powers']
        
        # Determine dominant state
        dominant = max(bp.items(), key=lambda x: x[1])
        
        states = {
            'delta': 'Deep relaxation or sleep-like state',
            'theta': 'Meditative or creative state',
            'alpha': 'Calm and relaxed state',
            'beta': 'Active and focused state',
            'gamma': 'Peak concentration state'
        }
        
        print("\n" + "="*60)
        print("QUICK SUMMARY")
        print("="*60)
        print(f"\nSession Duration: {metrics['duration_seconds']:.1f} seconds")
        print(f"\nDominant Brain State: {dominant[0].upper()} ({dominant[1]:.1f}%)")
        print(f"  → {states[dominant[0]]}")
        print(f"\nBrain Wave Distribution:")
        for band, power in bp.items():
            bar = '█' * int(power / 2)
            print(f"  {band.capitalize():8} {power:5.1f}% {bar}")
        
        print(f"\nMovement:")
        print(f"  Still for {metrics['motion']['still_percentage']:.1f}% of session")
        print(f"  Avg movement: {metrics['motion']['mean_movement']:.1f}°/s")
        
        # Simple interpretations
        print(f"\nInterpretation:")
        if bp['alpha'] > 40:
            print("  ✓ High alpha indicates good relaxation")
        if bp['beta'] > 35:
            print("  ⚡ High beta indicates active mental engagement")
        if bp['theta'] > 30:
            print("  🧘 High theta suggests meditative state")
        if metrics['motion']['still_percentage'] > 80:
            print("  🎯 Excellent physical stillness")
        
        print("="*60)


def main():
    """Main function."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python muse_ai_analyzer.py <csv_file> [model] [--lmstudio [url]]")
        print("\nExamples (Ollama - default):")
        print("  python muse_ai_analyzer.py recordings\\muse_session_20231206_120000.csv")
        print("  python muse_ai_analyzer.py recordings\\muse_session_20231206_120000.csv llama3.2")
        print("\nExamples (LM Studio):")
        print("  python muse_ai_analyzer.py recordings\\muse_session_20231206_120000.csv model_name --lmstudio")
        print("  python muse_ai_analyzer.py recordings\\muse_session_20231206_120000.csv model_name --lmstudio http://192.168.1.100:1234")
        return
    
    csv_file = sys.argv[1]
    model = "llama3.2"
    llm_type = "ollama"
    llm_url = "http://localhost:11434"
    
    # Parse arguments
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--lmstudio":
            llm_type = "lmstudio"
            llm_url = "http://localhost:1234"
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                llm_url = sys.argv[i + 1]
                i += 1
        elif not arg.startswith("--"):
            model = arg
        i += 1
    
    analyzer = MuseAIAnalyzer(csv_file, llm_url=llm_url, llm_type=llm_type)
    
    # Always show quick summary
    analyzer.get_quick_summary()
    
    # Try AI insights
    print(f"\nAttempting AI analysis with {model}...")
    analyzer.get_ollama_insights(model=model)


if __name__ == "__main__":
    main()
