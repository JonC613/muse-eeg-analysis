"""
Compare multiple Muse S sessions side-by-side
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from muse_ai_analyzer import MuseAIAnalyzer


def compare_sessions(*csv_files):
    """Compare multiple Muse sessions."""
    
    print("\n" + "="*80)
    print("MUSE S SESSION COMPARISON")
    print("="*80)
    
    sessions = []
    for csv_file in csv_files:
        analyzer = MuseAIAnalyzer(csv_file)
        metrics = analyzer.calculate_metrics()
        sessions.append({
            'name': Path(csv_file).stem,
            'file': csv_file,
            'metrics': metrics,
            'analyzer': analyzer
        })
    
    # Print comparison table
    print(f"\n{'Session':<30} {'Duration':<12} {'Samples':<10} {'Still %':<10}")
    print("-" * 80)
    for s in sessions:
        m = s['metrics']
        print(f"{s['name']:<30} {m['duration_seconds']:>8.1f}s   {m['total_samples']:>7}   {m['motion']['still_percentage']:>7.1f}%")
    
    # Brain wave comparison
    print("\n" + "="*80)
    print("BRAIN WAVE COMPARISON (% of total power)")
    print("="*80)
    print(f"\n{'Session':<30} {'Delta':<10} {'Theta':<10} {'Alpha':<10} {'Beta':<10} {'Gamma':<10}")
    print("-" * 80)
    
    for s in sessions:
        bp = s['metrics']['band_powers']
        print(f"{s['name']:<30} {bp['delta']:>7.1f}%  {bp['theta']:>7.1f}%  {bp['alpha']:>7.1f}%  {bp['beta']:>7.1f}%  {bp['gamma']:>7.1f}%")
    
    # Interpretation
    print("\n" + "="*80)
    print("KEY OBSERVATIONS")
    print("="*80)
    
    if len(sessions) >= 2:
        # Compare first vs last
        first = sessions[0]['metrics']['band_powers']
        last = sessions[-1]['metrics']['band_powers']
        
        print(f"\nComparing: {sessions[0]['name']} → {sessions[-1]['name']}")
        print("-" * 80)
        
        changes = {}
        for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']:
            change = last[band] - first[band]
            changes[band] = change
            direction = "↑" if change > 0 else "↓"
            print(f"{band.capitalize():8} {direction} {abs(change):>6.1f}% {'(increase)' if change > 0 else '(decrease)'}")
        
        # Interpretations
        print("\nInterpretation:")
        if changes['theta'] > 10:
            print("  🧘 SIGNIFICANT INCREASE in theta - Enhanced meditative/creative state")
        if changes['alpha'] > 5:
            print("  😌 INCREASE in alpha - More relaxed and calm")
        if changes['beta'] < -5:
            print("  🔽 DECREASE in beta - Reduced active thinking/analytical processing")
        if changes['delta'] > 10:
            print("  😴 INCREASE in delta - More drowsy/deeply relaxed")
        elif changes['delta'] < -10:
            print("  ⚡ DECREASE in delta - Less drowsy, more alert")
        if changes['gamma'] > 2:
            print("  🧠 INCREASE in gamma - Enhanced cognitive processing")
        
        # Movement comparison
        first_motion = sessions[0]['metrics']['motion']
        last_motion = sessions[-1]['metrics']['motion']
        motion_change = last_motion['still_percentage'] - first_motion['still_percentage']
        
        if abs(motion_change) > 1:
            direction = "more still" if motion_change > 0 else "more movement"
            print(f"  🎯 Physical stillness changed: {abs(motion_change):.1f}% {direction}")
    
    # Create visualization
    create_comparison_plot(sessions)
    
    return sessions


def create_comparison_plot(sessions):
    """Create visual comparison of sessions."""
    
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle('Muse S Session Comparison', fontsize=16, fontweight='bold')
    
    n_sessions = len(sessions)
    colors = plt.cm.Set3(np.linspace(0, 1, n_sessions))
    
    # 1. Brain Wave Comparison (Bar chart)
    ax1 = plt.subplot(2, 3, 1)
    ax1.set_title('Brain Wave Distribution', fontweight='bold')
    
    bands = ['delta', 'theta', 'alpha', 'beta', 'gamma']
    x = np.arange(len(bands))
    width = 0.8 / n_sessions
    
    for i, s in enumerate(sessions):
        bp = s['metrics']['band_powers']
        values = [bp[band] for band in bands]
        offset = (i - n_sessions/2) * width + width/2
        ax1.bar(x + offset, values, width, label=s['name'][:20], color=colors[i], alpha=0.8)
    
    ax1.set_xlabel('Frequency Band')
    ax1.set_ylabel('Power (%)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma'])
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # 2. Relaxation vs Focus (Scatter)
    ax2 = plt.subplot(2, 3, 2)
    ax2.set_title('Relaxation vs Focus', fontweight='bold')
    
    for i, s in enumerate(sessions):
        bp = s['metrics']['band_powers']
        relaxation = bp['alpha'] + bp['theta']
        focus = bp['beta'] + bp['gamma']
        ax2.scatter(relaxation, focus, s=200, color=colors[i], 
                   label=s['name'][:20], alpha=0.7, edgecolors='black', linewidth=2)
        ax2.annotate(f"{i+1}", (relaxation, focus), ha='center', va='center', 
                    fontweight='bold', fontsize=10)
    
    ax2.set_xlabel('Relaxation (Alpha + Theta %)')
    ax2.set_ylabel('Focus (Beta + Gamma %)')
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)
    
    # 3. Movement Comparison
    ax3 = plt.subplot(2, 3, 3)
    ax3.set_title('Physical Stillness', fontweight='bold')
    
    session_names = [s['name'][:15] for s in sessions]
    still_pcts = [s['metrics']['motion']['still_percentage'] for s in sessions]
    
    bars = ax3.barh(session_names, still_pcts, color=colors, alpha=0.8)
    ax3.set_xlabel('Still Time (%)')
    ax3.set_xlim([0, 100])
    ax3.grid(True, alpha=0.3, axis='x')
    
    # Add value labels
    for i, (bar, pct) in enumerate(zip(bars, still_pcts)):
        ax3.text(pct - 5, i, f'{pct:.1f}%', va='center', ha='right', 
                fontweight='bold', color='white')
    
    # 4. Delta vs Theta (mental state quadrant)
    ax4 = plt.subplot(2, 3, 4)
    ax4.set_title('Mental State Map (Delta vs Theta)', fontweight='bold')
    
    for i, s in enumerate(sessions):
        bp = s['metrics']['band_powers']
        ax4.scatter(bp['delta'], bp['theta'], s=200, color=colors[i],
                   label=s['name'][:20], alpha=0.7, edgecolors='black', linewidth=2)
        ax4.annotate(f"{i+1}", (bp['delta'], bp['theta']), ha='center', va='center',
                    fontweight='bold', fontsize=10)
    
    ax4.set_xlabel('Delta (Deep Relaxation) %')
    ax4.set_ylabel('Theta (Meditation/Creativity) %')
    ax4.axhline(y=20, color='gray', linestyle='--', alpha=0.5, label='High Theta')
    ax4.axvline(x=50, color='gray', linestyle='--', alpha=0.5, label='High Delta')
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)
    
    # 5. Time Series - Band Power Changes
    ax5 = plt.subplot(2, 3, 5)
    ax5.set_title('Session Progression', fontweight='bold')
    
    if n_sessions >= 2:
        # Show trend across sessions
        session_nums = list(range(1, n_sessions + 1))
        
        for band in ['theta', 'alpha', 'beta']:
            values = [s['metrics']['band_powers'][band] for s in sessions]
            ax5.plot(session_nums, values, marker='o', linewidth=2, 
                    markersize=8, label=band.capitalize(), alpha=0.8)
        
        ax5.set_xlabel('Session Number')
        ax5.set_ylabel('Power (%)')
        ax5.set_xticks(session_nums)
        ax5.legend()
        ax5.grid(True, alpha=0.3)
    
    # 6. Summary Stats
    ax6 = plt.subplot(2, 3, 6)
    ax6.axis('off')
    ax6.set_title('Session Summary', fontweight='bold')
    
    summary_text = ""
    for i, s in enumerate(sessions, 1):
        m = s['metrics']
        bp = m['band_powers']
        dominant = max(bp.items(), key=lambda x: x[1])
        
        summary_text += f"\n{i}. {s['name'][:25]}\n"
        summary_text += f"   Duration: {m['duration_seconds']:.1f}s\n"
        summary_text += f"   Dominant: {dominant[0].upper()} ({dominant[1]:.1f}%)\n"
        summary_text += f"   Stillness: {m['motion']['still_percentage']:.1f}%\n"
    
    ax6.text(0.1, 0.9, summary_text, fontsize=9, verticalalignment='top',
            fontfamily='monospace', transform=ax6.transAxes)
    
    plt.tight_layout()
    
    # Save plot
    output_file = Path('recordings') / 'session_comparison.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✓ Comparison plot saved to: {output_file}")
    
    plt.show()


def main():
    """Main function."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python muse_compare_sessions.py <csv_file1> <csv_file2> [csv_file3] ...")
        print("\nExample:")
        print("  python muse_compare_sessions.py recordings\\session1.csv recordings\\session2.csv")
        return
    
    csv_files = sys.argv[1:]
    compare_sessions(*csv_files)


if __name__ == "__main__":
    main()
