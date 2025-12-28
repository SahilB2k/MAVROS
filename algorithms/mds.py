"""
Selective Multi-Directional Search (MDS) - Balanced Quality Optimization
Tuned for: Better Cost & Fleet Count while maintaining 6-7s speed
Key improvements:
- Increased fleet reduction passes (40 → 80)
- Relaxed geometric filters (2.5 → 3.0)
- Better SA temperature schedule
"""

import copy
import math
import random
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
from operators.ejection_chain import ejection_chain_reduction

# Import aggressive cost optimizer if available
try:
    from operators.aggressive_cost_optimizer import aggressive_cost_reduction
    HAS_AGGRESSIVE_OPTIMIZER = True
except ImportError:
    HAS_AGGRESSIVE_OPTIMIZER = False
    print("Note: aggressive_cost_optimizer not found, using standard optimization only")


def selective_mds(solution: Solution,
                  max_iterations: int = 50,
                  top_n_critical: int = 5,
                  early_termination: int = 40) -> Solution:
    """
    Three-Phase Optimized MDS with Quality Focus:
    Phase 1: Fleet Reduction (MORE PASSES for better fleet count)
    Phase 2: Cost Optimization (Relaxed filters for hidden moves)
    Phase 3: Fine-tuning (focused refinement)
    
    Maintains O(N²) complexity through smart filtering
    """
    
    # Setup
    total_customers = solution.get_total_customers()
    solution.validate_coverage(total_customers)
    
    all_required_ids = set(solution.get_all_customer_ids())
    if len(all_required_ids) != total_customers:
        raise ValueError(f"ID mismatch: {len(all_required_ids)} unique vs {total_customers} total")
    
    depot = solution.routes[0].depot if solution.routes else None
    vehicle_capacity = solution.routes[0].vehicle_capacity if solution.routes else 0
    restoration_counts = {}
    
    def restore_missing():
        """Safety net for customer restoration"""
        current_ids = set(solution.get_all_customer_ids())
        missing_ids = list(all_required_ids - current_ids)
        if missing_ids and depot:
            restored_any = False
            for mid in missing_ids:
                restoration_counts[mid] = restoration_counts.get(mid, 0) + 1
                if restoration_counts[mid] <= 3:
                    restored_any = True
                else:
                    print(f"WARNING: Customer {mid} restored {restoration_counts[mid]} times")
            
            if restored_any:
                to_restore = [mid for mid in missing_ids if restoration_counts[mid] <= 3]
                if to_restore:
                    solution.restore_missing_customers(to_restore, depot, vehicle_capacity)
                    solution.validate_coverage(total_customers)
    
    # Adaptive parameters
    if total_customers > 100:
        top_n_critical = 2
        max_iterations = min(max_iterations, 35)
        early_termination = 25
    elif total_customers < 30:
        max_iterations = min(max_iterations, 25)
        early_termination = 15
    
    # Precompute neighbor lists
    from operators.candidate_pruning import build_candidate_list_for_customer
    
    all_customers_flat = []
    for r in solution.routes:
        for cid in r.customer_ids:
            all_customers_flat.append(r.customers_lookup[cid])
    
    k_neighbors = min(50, max(20, total_customers // 3))
    global_neighbors = {}
    for cust in all_customers_flat:
        global_neighbors[cust.id] = build_candidate_list_for_customer(cust, all_customers_flat, k=k_neighbors)
    
    max_r_size = max((len(r.customer_ids) for r in solution.routes), default=0)
    temp_arrival_buffer = [0.0] * (max_r_size + 20)
    
    # ===== PHASE 1: Aggressive Fleet Reduction (INCREASED PASSES) =====
    print("Phase 1: Fleet Reduction (Enhanced)")
    fleet_stable = False
    fleet_passes = 0
    max_fleet_passes = 80 if total_customers > 50 else 50  # INCREASED from 40/25
    
    while not fleet_stable and fleet_passes < max_fleet_passes:
        fleet_passes += 1
        fleet_stable = True
        
        current_vehicles = len(solution.routes)
        customers_before = solution.get_total_customers()
        
        # Strategy 1: Inter-route relocate
        if inter_route_relocate_inplace(solution, temp_arrival_buffer, neighbors=global_neighbors):
            solution.update_cost()
            if len(solution.routes) < current_vehicles:
                fleet_stable = False
                continue
            fleet_stable = False
        
        customers_after = solution.get_total_customers()
        if customers_after < customers_before:
            restore_missing()
            if any(restoration_counts.get(cid, 0) > 3 for cid in all_required_ids - set(solution.get_all_customer_ids())):
                break
        
        # Strategy 2: Route emptying
        customers_before = solution.get_total_customers()
        if route_empty_inplace(solution):
            solution.update_cost()
            fleet_stable = False
        
        # Strategy 3: Ejection chains with DEPTH-3 (stubborn routes)
        sorted_routes = sorted(range(len(solution.routes)), 
                             key=lambda i: len(solution.routes[i].customer_ids))
        
        for r_idx in sorted_routes:
            if r_idx >= len(solution.routes):
                break
            route = solution.routes[r_idx]
            # Try Depth-3 for routes with 3-8 customers (wider range)
            if 0 < len(route.customer_ids) < 9:  # INCREASED from 5 to 9
                if ejection_chain_reduction(solution, r_idx, max_depth=3):  # Depth-3
                    solution.update_cost()
                    fleet_stable = False
                    break
        
        customers_after = solution.get_total_customers()
        if customers_after < customers_before:
            restore_missing()
            if any(restoration_counts.get(cid, 0) > 3 for cid in all_required_ids - set(solution.get_all_customer_ids())):
                break
        
        # Convergence check (more patient)
        if fleet_passes % 15 == 0:  # Check every 15 passes instead of 10
            if len(solution.routes) == current_vehicles:
                consecutive_no_change = 15
                if fleet_passes > 30 and consecutive_no_change >= 15:  # More patient
                    break
    
    print(f"  Fleet reduction complete: {len(solution.routes)} vehicles after {fleet_passes} passes")
    
    # ===== PHASE 1.5: AGGRESSIVE COST REDUCTION (NEW!) =====
    if HAS_AGGRESSIVE_OPTIMIZER:
        print("Phase 1.5: Aggressive Cost Reduction")
        aggressive_passes = 3
        for agg_pass in range(aggressive_passes):
            if aggressive_cost_reduction(solution, max_attempts=200):
                solution.update_cost()
                print(f"  Pass {agg_pass+1}: Cost reduced to {solution.total_base_cost:.2f}")
            else:
                break  # No more improvements
    
    # ===== PHASE 2 & 3: Cost Optimization with Improved SA =====
    print("Phase 2+3: Cost Optimization (Relaxed Filters)")
    
    best_solution_cost = solution.total_cost
    best_solution = copy.deepcopy(solution)
    
    # SA parameters - Better temperature schedule
    current_temp = 100.0  # INCREASED from 80.0 for more exploration
    cooling_rate = 0.92   # Slightly slower cooling
    min_temp = 0.5
    reheat_temp = 50.0    # Higher reheat temp
    
    iteration = 0
    no_improvement = 0
    no_best_improvement = 0
    
    # Adaptive max iterations
    effective_max_iter = max_iterations
    if total_customers > 80:
        effective_max_iter = min(max_iterations, 40)  # Slightly increased
    
    while iteration < effective_max_iter and no_improvement < early_termination and no_best_improvement < 25:
        iteration += 1
        
        current_state_backup = copy.deepcopy(solution)
        
        # Perturbation strategy (more aggressive)
        lns_prob = 0.40 if current_temp > 50 else 0.20  # INCREASED from 0.35/0.15
        if random.random() < lns_prob:
            removal_frac = 0.25 + (0.15 * random.random())  # Slightly larger removals
            lns_destroy_repair(solution, removal_fraction=removal_frac, random_seed=iteration)
        
        # Inter-route operators (every 3rd iteration)
        inter_route_improved = False
        if len(solution.routes) > 1 and iteration % 3 == 0:
            rand_val = random.random()
            
            if rand_val < 0.40:  # More emphasis on 2-opt*
                if inter_route_2opt_star(solution, max_attempts=100):  # INCREASED from 80
                    inter_route_improved = True
            elif rand_val < 0.70:
                if inter_route_relocate_inplace(solution, neighbors=global_neighbors):
                    inter_route_improved = True
            else:
                if cross_exchange(solution, max_attempts=30):  # INCREASED from 25
                    inter_route_improved = True
        
        # Intra-route refinement
        global_improved = False
        critical_indices = identify_critical_route_indices(
            solution, top_n=min(top_n_critical, len(solution.routes))
        )
        
        for route_idx in critical_indices:
            route = solution.routes[route_idx]
            if len(route.customer_ids) < 2:
                continue
            
            route_improved = True
            local_iter = 0
            max_local_iter = 6  # INCREASED from 5
            
            while route_improved and local_iter < max_local_iter:
                route_improved = False
                local_iter += 1
                
                if intra_route_2opt_inplace(route):
                    route_improved = True
                elif or_opt_inplace(route, max_segment_len=4, max_attempts=150):  # Increased segment length and attempts
                    route_improved = True
                elif temporal_shift_operator_inplace(route, temp_arrival_buffer):
                    route_improved = True
                elif relocate_operator_inplace(route, temp_arrival_buffer, max_relocations=30):  # INCREASED
                    route_improved = True
                
                if route_improved:
                    solution.update_cost()
        
        solution.update_cost()
        
        # SA acceptance (more tolerant of cost increases early on)
        new_cost = solution.total_cost
        curr_cost = current_state_backup.total_cost
        delta = new_cost - curr_cost
        
        new_vehicles = len(solution.routes)
        old_vehicles = len(current_state_backup.routes)
        
        accepted = False
        
        # Priority: Always accept fleet reduction
        if new_vehicles < old_vehicles:
            accepted = True
            no_improvement = 0
            no_best_improvement = 0
            if solution.total_base_cost < best_solution_cost:
                best_solution_cost = solution.total_base_cost
                best_solution = copy.deepcopy(solution)
        elif delta < -0.001:
            accepted = True
            no_improvement = 0
            if solution.total_base_cost < best_solution_cost - 0.001:
                best_solution_cost = solution.total_base_cost
                best_solution = copy.deepcopy(solution)
                no_best_improvement = 0
            else:
                no_best_improvement += 1
        else:
            try:
                prob = math.exp(-delta / current_temp) if current_temp > min_temp else 0.0
            except OverflowError:
                prob = 0.0
            
            if random.random() < prob:
                accepted = True
                no_best_improvement += 1
            else:
                accepted = False
                no_best_improvement += 1
        
        if not accepted:
            solution = current_state_backup
            no_improvement += 1
        
        # Cooling
        current_temp = max(min_temp, current_temp * cooling_rate)
        
        # Reheat if stuck (more frequent)
        if no_best_improvement >= 8 and current_temp < reheat_temp:  # CHANGED from 10 to 8
            current_temp = reheat_temp
            no_best_improvement = 0
        
        # Safety restoration
        restore_missing()
        
        # Progress reporting
        if iteration % 10 == 0:
            print(f"  Iter {iteration}: Cost={solution.total_base_cost:.2f}, Vehicles={len(solution.routes)}, Temp={current_temp:.2f}")
    
    print(f"Optimization complete: {iteration} iterations")
    return best_solution