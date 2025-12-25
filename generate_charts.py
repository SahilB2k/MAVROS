"""
Generate Comparison Charts for VRPTW Solver
Creates professional matplotlib visualizations comparing custom solver vs OR-Tools
"""

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import numpy as np
import os

# Ensure static directory exists
os.makedirs('static/charts', exist_ok=True)

# Comparison data (C102 instance with 100 customers)
custom_solver = {
    'cost': 2552.82,
    'vehicles': 13,
    'time': 27.85,
    'memory_mb': 8
}

ortools = {
    'cost': 1747.00,
    'vehicles': 12,
    'time': 30.00,
    'memory_mb': 150  # OR-Tools uses more memory
}

# Set style
plt.style.use('dark_background')
colors = {
    'custom': '#6366F1',
    'ortools': '#06B6D4',
    'accent': '#F97316'
}

# 1. Bar Chart Comparison
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.patch.set_facecolor('#0f172a')

metrics = ['Total Cost', 'Vehicles', 'Solve Time (s)']
custom_values = [custom_solver['cost'], custom_solver['vehicles'], custom_solver['time']]
ortools_values = [ortools['cost'], ortools['vehicles'], ortools['time']]

for idx, (ax, metric, custom_val, ortools_val) in enumerate(zip(axes, metrics, custom_values, ortools_values)):
    ax.set_facecolor('#1e293b')
    x = np.arange(2)
    width = 0.6
    
    bars = ax.bar(x, [custom_val, ortools_val], width, 
                   color=[colors['custom'], colors['ortools']],
                   edgecolor='white', linewidth=1.5)
    
    ax.set_ylabel(metric, fontsize=12, fontweight='bold', color='#f1f5f9')
    ax.set_xticks(x)
    ax.set_xticklabels(['Custom Solver', 'OR-Tools'], fontsize=10, color='#cbd5e1')
    ax.tick_params(colors='#cbd5e1')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#475569')
    ax.spines['bottom'].set_color('#475569')
    ax.grid(axis='y', alpha=0.2, linestyle='--')
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}' if idx == 2 else f'{int(height)}',
                ha='center', va='bottom', fontsize=11, fontweight='bold', color='#f1f5f9')

plt.suptitle('Performance Comparison: Custom Solver vs OR-Tools', 
             fontsize=16, fontweight='bold', color='#f1f5f9', y=1.02)
plt.tight_layout()
plt.savefig('static/charts/bar_comparison.png', dpi=150, bbox_inches='tight', facecolor='#0f172a')
plt.close()

# 2. Radar Chart - Multi-dimensional Performance
fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
fig.patch.set_facecolor('#0f172a')
ax.set_facecolor('#1e293b')

categories = ['Cost\nQuality', 'Fleet\nSize', 'Speed', 'Memory\nEfficiency']
N = len(categories)

# Normalize values (inverse for cost and vehicles, direct for speed and memory)
custom_normalized = [
    (ortools['cost'] / custom_solver['cost']) * 100,  # Lower cost is better
    (ortools['vehicles'] / custom_solver['vehicles']) * 100,  # Fewer vehicles is better
    (ortools['time'] / custom_solver['time']) * 100,  # Faster is better
    (ortools['memory_mb'] / custom_solver['memory_mb']) * 100  # Less memory is better
]

ortools_normalized = [100, 100, 100, 100]  # Baseline

angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
custom_normalized += custom_normalized[:1]
ortools_normalized += ortools_normalized[:1]
angles += angles[:1]

ax.plot(angles, ortools_normalized, 'o-', linewidth=2, label='OR-Tools', 
        color=colors['ortools'], markersize=8)
ax.fill(angles, ortools_normalized, alpha=0.15, color=colors['ortools'])

ax.plot(angles, custom_normalized, 'o-', linewidth=2, label='Custom Solver', 
        color=colors['custom'], markersize=8)
ax.fill(angles, custom_normalized, alpha=0.15, color=colors['custom'])

ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, fontsize=11, color='#f1f5f9', fontweight='bold')
ax.set_ylim(0, 150)
ax.set_yticks([50, 100, 150])
ax.set_yticklabels(['50%', '100%', '150%'], fontsize=9, color='#94a3b8')
ax.grid(color='#475569', linestyle='--', linewidth=0.5, alpha=0.5)
ax.spines['polar'].set_color('#475569')

plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11, 
           framealpha=0.9, facecolor='#1e293b', edgecolor='#475569')
plt.title('Multi-Dimensional Performance Analysis', fontsize=14, fontweight='bold', 
          color='#f1f5f9', pad=20)
plt.savefig('static/charts/radar_comparison.png', dpi=150, bbox_inches='tight', facecolor='#0f172a')
plt.close()

# 3. Quality Gap Visualization
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('#0f172a')
ax.set_facecolor('#1e293b')

cost_gap = ((custom_solver['cost'] - ortools['cost']) / ortools['cost']) * 100
vehicle_gap = ((custom_solver['vehicles'] - ortools['vehicles']) / ortools['vehicles']) * 100
time_advantage = ((ortools['time'] - custom_solver['time']) / ortools['time']) * 100
memory_advantage = ((ortools['memory_mb'] - custom_solver['memory_mb']) / ortools['memory_mb']) * 100

metrics = ['Cost Gap', 'Vehicle Gap', 'Speed\nAdvantage', 'Memory\nAdvantage']
values = [cost_gap, vehicle_gap, time_advantage, memory_advantage]
colors_list = ['#F59E0B' if v > 0 else '#10B981' for v in values]

bars = ax.barh(metrics, values, color=colors_list, edgecolor='white', linewidth=1.5)

ax.axvline(x=0, color='#cbd5e1', linestyle='-', linewidth=2)
ax.set_xlabel('Percentage Difference (%)', fontsize=12, fontweight='bold', color='#f1f5f9')
ax.set_title('Performance Gap Analysis\n(Positive = Custom Solver Better, Negative = OR-Tools Better)', 
             fontsize=14, fontweight='bold', color='#f1f5f9', pad=15)
ax.tick_params(colors='#cbd5e1')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#475569')
ax.spines['bottom'].set_color('#475569')
ax.grid(axis='x', alpha=0.2, linestyle='--')

# Add value labels
for bar, value in zip(bars, values):
    width = bar.get_width()
    label_x = width + (5 if width > 0 else -5)
    ax.text(label_x, bar.get_y() + bar.get_height()/2, 
            f'{value:+.1f}%',
            ha='left' if width > 0 else 'right', va='center', 
            fontsize=11, fontweight='bold', color='#f1f5f9')

plt.tight_layout()
plt.savefig('static/charts/gap_analysis.png', dpi=150, bbox_inches='tight', facecolor='#0f172a')
plt.close()

# 4. Trade-off Analysis
fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('#0f172a')
ax.set_facecolor('#1e293b')

# Scatter plot showing cost vs time trade-off
ax.scatter(ortools['time'], ortools['cost'], s=500, c=colors['ortools'], 
           alpha=0.7, edgecolors='white', linewidth=2, label='OR-Tools', zorder=3)
ax.scatter(custom_solver['time'], custom_solver['cost'], s=500, c=colors['custom'], 
           alpha=0.7, edgecolors='white', linewidth=2, label='Custom Solver', zorder=3)

# Add labels
ax.text(ortools['time'], ortools['cost'] - 50, 'OR-Tools\n(Higher Quality)', 
        ha='center', va='top', fontsize=10, fontweight='bold', color='#f1f5f9',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#1e293b', edgecolor=colors['ortools'], linewidth=2))
ax.text(custom_solver['time'], custom_solver['cost'] + 50, 'Custom Solver\n(Faster)', 
        ha='center', va='bottom', fontsize=10, fontweight='bold', color='#f1f5f9',
        bbox=dict(boxstyle='round,pad=0.5', facecolor='#1e293b', edgecolor=colors['custom'], linewidth=2))

ax.set_xlabel('Solve Time (seconds)', fontsize=12, fontweight='bold', color='#f1f5f9')
ax.set_ylabel('Total Cost', fontsize=12, fontweight='bold', color='#f1f5f9')
ax.set_title('Cost vs Speed Trade-off Analysis', fontsize=14, fontweight='bold', color='#f1f5f9', pad=15)
ax.tick_params(colors='#cbd5e1')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#475569')
ax.spines['bottom'].set_color('#475569')
ax.grid(alpha=0.2, linestyle='--', color='#475569')
ax.legend(fontsize=11, framealpha=0.9, facecolor='#1e293b', edgecolor='#475569')

plt.tight_layout()
plt.savefig('static/charts/tradeoff_analysis.png', dpi=150, bbox_inches='tight', facecolor='#0f172a')
plt.close()

print("✓ All comparison charts generated successfully!")
print("  - static/charts/bar_comparison.png")
print("  - static/charts/radar_comparison.png")
print("  - static/charts/gap_analysis.png")
print("  - static/charts/tradeoff_analysis.png")
