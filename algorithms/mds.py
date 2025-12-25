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
from operators.inter_route_2opt_star import inter_route_2opt_star
from operators.cross_exchange import cross_exchange

# Global Configuration
MAX_ROUTE_SIZE = 100
EARLY_TERMINATION_THRESHOLD = 40

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

    # --- Phase 2 & 3: LNS + Deep Refinement with Simulated Annealing ---
    # Interleaved LNS and refinement for better exploration

    # Best solution tracking
    import copy
    best_solution_cost = solution.total_cost
    best_solution = copy.deepcopy(solution) # O(N) space, but necessary for restoration
    
    # SA Parameters - Tuned for fleet reduction
    current_temp = 1000.0  # Higher temp to accept worse moves that reduce fleet
    cooling_rate = 0.95
    import math
    import random

    iteration = 0
    no_improvement = 0
    
    # Combined loop: LNS -> Refinement -> SA Acceptance
    while iteration < max_iterations and no_improvement < early_termination:
        iteration += 1
        
        # Snapshot current state for SA rollback
        current_state_backup = copy.deepcopy(solution) 
        
        # 1. Perturbation (LNS) - Adaptive probability
        # run LNS more often at high temp
        lns_prob = 0.3 if current_temp > 100 else 0.1
        if random.random() < lns_prob:
             lns_destroy_repair(solution, removal_fraction=0.20 + (0.1 * random.random()), random_seed=iteration)
        
        # 1b. Inter-route operators (critical for fleet reduction)
        # Run every 5th iteration to balance quality vs speed
        if iteration % 5 == 0 and len(solution.routes) > 1:
            inter_route_2opt_star(solution, max_attempts=15)
            cross_exchange(solution, max_attempts=8)
        
        # 2. Deep Refinement (Local Search)
        global_improved = False
        critical_indices = identify_critical_route_indices(
            solution, top_n=min(top_n_critical, len(solution.routes))
        )

        for route_idx in critical_indices:
            route = solution.routes[route_idx]
            if len(route.customer_ids) < 2: continue
            
            route_improved = True
            while route_improved:
                route_improved = False
                # Intra-route operators
                if intra_route_2opt_inplace(route): route_improved = True
                elif or_opt_inplace(route, max_segment_len=3): route_improved = True
                elif temporal_shift_operator_inplace(route, temp_arrival_buffer): route_improved = True
                elif relocate_operator_inplace(route, temp_arrival_buffer, max_relocations=30): route_improved = True
                
                if route_improved: solution.update_cost()

        solution.update_cost()
        
        # 3. Simulated Annealing Acceptance Criteria
        new_cost = solution.total_cost
        curr_cost = current_state_backup.total_cost
        delta = new_cost - curr_cost
        
        # Track vehicle count change
        new_vehicles = len(solution.routes)
        old_vehicles = len(current_state_backup.routes)

        accepted = False
        
        # PRIORITY: Always accept fleet reduction (even if cost increases)
        if new_vehicles < old_vehicles:
            accepted = True
            no_improvement = 0
            if solution.total_base_cost < best_solution_cost:
                best_solution_cost = solution.total_base_cost
                best_solution = copy.deepcopy(solution)
        elif delta < 0:
            # Improvement in cost
            accepted = True
            no_improvement = 0
            if solution.total_base_cost < best_solution_cost:
                best_solution_cost = solution.total_base_cost
                best_solution = copy.deepcopy(solution)
        else:
            # Worsening - check SA probability
            try:
                prob = math.exp(-delta / current_temp)
            except OverflowError:
                prob = 0.0
                
            if random.random() < prob:
                accepted = True
                # Accepted bad move to escape local optima
                # print(f"DEBUG: SA Accepted worsening delta={delta:.2f} @ Temp={current_temp:.1f}")
            else:
                accepted = False
        
        if not accepted:
            # Revert to state before this iteration's changes
            solution = current_state_backup 
            no_improvement += 1
        
        # Cool down
        current_temp *= cooling_rate
        
        # Safety: Restore missing customers if any dropped
        restore_missing()
        
    # Return best found
    return best_solution