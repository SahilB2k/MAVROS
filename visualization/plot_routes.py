"""
Route visualization using matplotlib
Generate plots then discard (memory efficient)
"""

from typing import Optional
from core.data_structures import Solution, Customer
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from pathlib import Path


def plot_solution(solution: Solution,
                 depot: Customer,
                 customers_lookup: dict,
                 output_file: Optional[str] = None,
                 show: bool = False) -> None:
    """
    Plot solution routes
    
    Memory efficient: Generate plot, save to file, then discard
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Plot depot
    ax.scatter(depot.x, depot.y, c='red', s=200, marker='s', label='Depot', zorder=5)
    
    # Plot customers
    customer_x = []
    customer_y = []
    for customer in customers_lookup.values():
        if customer.id != depot.id:
            customer_x.append(customer.x)
            customer_y.append(customer.y)
    
    ax.scatter(customer_x, customer_y, c='blue', s=50, label='Customers', zorder=3)
    
    # Plot routes with different colors
    colors = plt.cm.tab10(range(len(solution.routes)))
    for route_idx, route in enumerate(solution.routes):
        color = colors[route_idx]
        
        # Draw route path
        route_x = [depot.x]
        route_y = [depot.y]
        
        for customer_id in route.customer_ids:
            customer = customers_lookup[customer_id]
            route_x.append(customer.x)
            route_y.append(customer.y)
        
        route_x.append(depot.x)
        route_y.append(depot.y)
        
        ax.plot(route_x, route_y, color=color, linewidth=2, alpha=0.6, zorder=1)
        ax.scatter([depot.x] + [customers_lookup[cid].x for cid in route.customer_ids],
                   [depot.y] + [customers_lookup[cid].y for cid in route.customer_ids],
                   c=[color], s=50, zorder=2)
    
    ax.set_xlabel('X Coordinate')
    ax.set_ylabel('Y Coordinate')
    ax.set_title(f'VRPTW Solution: {solution.num_vehicles} vehicles, Cost: {solution.total_cost:.2f}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Save or show
    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    
    if show:
        plt.show()
    
    # Close figure to free memory
    plt.close(fig)
    del fig, ax


def plot_comparison(solution1: Solution,
                   solution2: Solution,
                   depot: Customer,
                   customers_lookup: dict,
                   labels: tuple = ("Solution 1", "Solution 2"),
                   output_file: Optional[str] = None) -> None:
    """
    Plot two solutions side by side for comparison
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    for ax, solution, label in [(ax1, solution1, labels[0]), (ax2, solution2, labels[1])]:
        # Plot depot
        ax.scatter(depot.x, depot.y, c='red', s=200, marker='s', label='Depot', zorder=5)
        
        # Plot customers
        customer_x = [c.x for c in customers_lookup.values() if c.id != depot.id]
        customer_y = [c.y for c in customers_lookup.values() if c.id != depot.id]
        ax.scatter(customer_x, customer_y, c='blue', s=50, label='Customers', zorder=3)
        
        # Plot routes
        colors = plt.cm.tab10(range(len(solution.routes)))
        for route_idx, route in enumerate(solution.routes):
            color = colors[route_idx]
            
            route_x = [depot.x] + [customers_lookup[cid].x for cid in route.customer_ids] + [depot.x]
            route_y = [depot.y] + [customers_lookup[cid].y for cid in route.customer_ids] + [depot.y]
            
            ax.plot(route_x, route_y, color=color, linewidth=2, alpha=0.6, zorder=1)
        
        ax.set_xlabel('X Coordinate')
        ax.set_ylabel('Y Coordinate')
        ax.set_title(f'{label}: {solution.num_vehicles} vehicles, Cost: {solution.total_cost:.2f}')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Comparison plot saved to {output_file}")
    
    plt.close(fig)
    del fig, ax1, ax2







