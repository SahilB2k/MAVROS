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
    total_customers = solution.get_total_customers()
    # Validate coverage BEFORE doing any optimization to catch construction bugs early
    solution.validate_coverage(total_customers)
    
    # Track required IDs for restoration safety net
    all_required_ids = set(solution.get_all_customer_ids())
    if len(all_required_ids) != total_customers:
        raise ValueError(f"Mismatch: {len(all_required_ids)} unique IDs but {total_customers} total customers")
    
    # Get depot and capacity for restoration (if needed)
    depot = solution.routes[0].depot if solution.routes else None
    vehicle_capacity = solution.routes[0].vehicle_capacity if solution.routes else 0

    # Track restoration counts per customer ID to prevent infinite loops
    restoration_counts = {}  # customer_id -> count

    def restore_missing():
        current_ids = set(solution.get_all_customer_ids())
        missing_ids = list(all_required_ids - current_ids)
        if missing_ids and depot:
            # Check restoration limits
            restored_any = False
            for mid in missing_ids:
                restoration_counts[mid] = restoration_counts.get(mid, 0) + 1
                if restoration_counts[mid] <= 3:
                    print(f"Restored customer {mid} to maintain 100% coverage.")
                    restored_any = True
                else:
                    print(f"WARNING: Customer {mid} restored {restoration_counts[mid]} times - skipping further restoration.")
            
            if restored_any:
                # Only restore customers that haven't exceeded the limit
                to_restore = [mid for mid in missing_ids if restoration_counts[mid] <= 3]
                if to_restore:
                    solution.restore_missing_customers(to_restore, depot, vehicle_capacity)
                    solution.validate_coverage(total_customers)
    
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
        
        # Track customer count before operator
        customers_before = solution.get_total_customers()
        
        # 1. Try inter-route relocation to shift load
        if inter_route_relocate_inplace(solution, temp_arrival_buffer):
            solution.update_cost()
            improved_fleet = True
        
        # Integrity check after inter_route_relocate
        customers_after = solution.get_total_customers()
        if customers_after < customers_before:
            missing_count = customers_before - customers_after
            print(f"WARNING: inter_route_relocate dropped {missing_count} customers. Restoring...")
            restore_missing()
            # If restoration limit exceeded, break to prevent infinite loop
            if any(restoration_counts.get(cid, 0) > 3 for cid in all_required_ids - set(solution.get_all_customer_ids())):
                break
        
        # 2. Specifically target 'killing' routes with < 6 customers
        customers_before = solution.get_total_customers()
        if route_empty_inplace(solution):
            solution.update_cost()
            improved_fleet = True
        
        # Integrity check after route_empty
        customers_after = solution.get_total_customers()
        if customers_after < customers_before:
            missing_count = customers_before - customers_after
            print(f"WARNING: route_empty dropped {missing_count} customers. Restoring...")
            restore_missing()
            # If restoration limit exceeded, break to prevent infinite loop
            if any(restoration_counts.get(cid, 0) > 3 for cid in all_required_ids - set(solution.get_all_customer_ids())):
                break
            
        if not improved_fleet:
            break

    # --- Phase 2: Escape Local Optima (LNS) ---
    # Perform a few rounds of Destroy & Repair to reshuffle clusters
    for i in range(3):
        customers_before = solution.get_total_customers()
        # Removal fraction 0.20 is a good balance for 100-customer instances
        if lns_destroy_repair(solution, removal_fraction=0.20, random_seed=42 + i):
            solution.update_cost()
        
        # Integrity check after LNS
        customers_after = solution.get_total_customers()
        if customers_after < customers_before:
            missing_count = customers_before - customers_after
            print(f"WARNING: LNS dropped {missing_count} customers. Restoring...")
            restore_missing()
            # If restoration limit exceeded, skip remaining LNS iterations
            if any(restoration_counts.get(cid, 0) > 3 for cid in all_required_ids - set(solution.get_all_customer_ids())):
                break
        elif customers_after > customers_before:
            # LNS should not add customers (only restore), but validate anyway
            solution.validate_coverage(total_customers)

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
                
                # Track customer count before operator
                customers_before = solution.get_total_customers()
                
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

                # Integrity check after each operator
                customers_after = solution.get_total_customers()
                if customers_after < customers_before:
                    missing_count = customers_before - customers_after
                    print(f"WARNING: Operator dropped {missing_count} customers. Restoring...")
                    restore_missing()
                    # If restoration limit exceeded, skip this route optimization
                    if any(restoration_counts.get(cid, 0) > 3 for cid in all_required_ids - set(solution.get_all_customer_ids())):
                        break

                if route_improved:
                    global_improved = True
                    # Update only the current route and penalized solution cost
                    solution.update_cost()

        # After each outer iteration, ensure coverage is intact (but limit restorations)
        restore_missing() 

        if global_improved:
            no_improvement = 0
        else:
            no_improvement += 1

        # After each outer iteration, ensure coverage is intact
        restore_missing()

    solution.update_cost()
    
    # Final validation: ensure no customers were dropped during optimization
    solution.validate_coverage(total_customers)
    
    return solution