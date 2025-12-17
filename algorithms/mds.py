"""
Selective Multi-Directional Search (MDS)
Optimized for Speed and Solution Quality (Vehicle Reduction focus)
"""

from typing import List, Set
from core.data_structures import Solution, Route
from evaluation.route_analyzer import identify_critical_route_indices
from operators.inter_route_relocate import inter_route_relocate_inplace
from operators.intra_route_2opt import intra_route_2opt_inplace
from operators.or_opt import or_opt_inplace
from operators.temporal_shift import temporal_shift_operator_inplace
from operators.swap import swap_operator_inplace
from operators.relocate import relocate_operator_inplace
from operators.lns_destroy_repair import lns_destroy_repair
from operators.route_empty import route_empty_inplace

# Global Configuration
MAX_ROUTE_SIZE = 100
EARLY_TERMINATION_THRESHOLD = 15

def selective_mds(solution: Solution,
                  max_iterations: int = 50,
                  top_n_critical: int = 5,
                  early_termination: int = EARLY_TERMINATION_THRESHOLD) -> Solution:
    """
    Enhanced Three-Phase MDS:
      Phase 1: Aggressive Fleet Reduction (Killing underfilled routes)
      Phase 2: Global Perturbation (LNS to escape local optima)
      Phase 3: Deep Route Refinement (Intra-route path optimization)
    """

    # --- Setup & Adaptive Parameters ---
    total_customers = sum(len(r.customer_ids) for r in solution.routes)
    if total_customers > 100:
        top_n_critical = 2  # Focus intensity on large instances
        max_iterations = min(max_iterations, 30)

    max_r_size = max((len(r.customer_ids) for r in solution.routes), default=0)
    temp_arrival_buffer = [0.0] * (max_r_size + 20)

    # --- Phase 1: Aggressive Vehicle Reduction ---
    # This is the most important step for matching OR-Tools quality
    improved_fleet = True
    while improved_fleet:
        improved_fleet = False
        
        # 1. Try inter-route relocation to shift load
        if inter_route_relocate_inplace(solution, temp_arrival_buffer):
            solution.update_cost()
            improved_fleet = True
            
        # 2. Specifically target 'killing' routes with < 6 customers
        if route_empty_inplace(solution):
            solution.update_cost()
            improved_fleet = True
            
        if not improved_fleet:
            break

    # --- Phase 2: Escape Local Optima (LNS) ---
    # Perform a few rounds of Destroy & Repair to reshuffle clusters
    for i in range(3):
        # Removal fraction 0.20 is a good balance for 100-customer instances
        if lns_destroy_repair(solution, removal_fraction=0.20, random_seed=42 + i):
            solution.update_cost()

    # --- Phase 3: Deep Refinement ---
    iteration = 0
    no_improvement = 0
    
    while iteration < max_iterations and no_improvement < early_termination:
        iteration += 1
        global_improved = False

        # Identify routes with high waiting time or high distance
        critical_indices = identify_critical_route_indices(
            solution, top_n=min(top_n_critical, len(solution.routes))
        )

        for route_idx in critical_indices:
            route = solution.routes[route_idx]
            if len(route.customer_ids) < 2:
                continue

            route_improved = True
            while route_improved:
                route_improved = False
                
                # Operator 1: Intra-route 2-opt (Essential for path cleaning)
                if intra_route_2opt_inplace(route):
                    route_improved = True
                
                # Operator 2: Or-Opt (Segment relocation 1-3)
                # Very effective at fixing time-window alignment
                elif or_opt_inplace(route, max_segment_len=3):
                    route_improved = True
                
                # Operator 3: Temporal Shift (Adjust depot departure)
                elif temporal_shift_operator_inplace(route, temp_arrival_buffer):
                    route_improved = True
                
                # Operator 4: Best-Fit Relocate (Micro-optimizing positions)
                elif relocate_operator_inplace(route, temp_arrival_buffer, max_relocations=30):
                    route_improved = True

                if route_improved:
                    global_improved = True
                    # Update only the current route and penalized solution cost
                    solution.update_cost() 

        if global_improved:
            no_improvement = 0
        else:
            no_improvement += 1

    solution.update_cost()
    return solution