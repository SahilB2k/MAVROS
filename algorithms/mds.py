"""
Fast Multi-Directional Search (MDS) - Speed + Quality Balance
Target: 6-7s runtime with competitive quality
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


def selective_mds(solution: Solution,
                  max_iterations: int = 50,
                  top_n_critical: int = 5,
                  early_termination: int = 40) -> Solution:
    """
    Fast MDS with aggressive fleet reduction
    Phase 1: Fleet Reduction (quick ejection chains)
    Phase 2: Cost Optimization (fast local search)
    """
    
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
            
            if restored_any:
                to_restore = [mid for mid in missing_ids if restoration_counts[mid] <= 3]
                if to_restore:
                    solution.restore_missing_customers(to_restore, depot, vehicle_capacity)
                    solution.validate_coverage(total_customers)
    
    # Adaptive parameters based on problem size
    if total_customers > 100:
        top_n_critical = 2
        max_iterations = min(max_iterations, 30)
        early_termination = 20
        fleet_passes = 30
    elif total_customers < 30:
        max_iterations = min(max_iterations, 20)
        early_termination = 15
        fleet_passes = 20
    else:
        fleet_passes = 40
    
    # Precompute neighbor lists (faster than full distance calculations)
    from operators.candidate_pruning import build_candidate_list_for_customer
    
    all_customers_flat = []
    for r in solution.routes:
        for cid in r.customer_ids:
            all_customers_flat.append(r.customers_lookup[cid])
    
    k_neighbors = min(40, max(15, total_customers // 4))
    global_neighbors = {}
    for cust in all_customers_flat:
        global_neighbors[cust.id] = build_candidate_list_for_customer(cust, all_customers_flat, k=k_neighbors)
    
    max_r_size = max((len(r.customer_ids) for r in solution.routes), default=0)
    temp_arrival_buffer = [0.0] * (max_r_size + 20)
    
    # ===== PHASE 1: Fast Fleet Reduction =====
    print("Phase 1: Fleet Reduction")
    fleet_stable = False
    pass_count = 0
    
    while not fleet_stable and pass_count < fleet_passes:
        pass_count += 1
        fleet_stable = True
        
        current_vehicles = len(solution.routes)
        
        # Strategy 1: Inter-route relocate
        if inter_route_relocate_inplace(solution, temp_arrival_buffer, neighbors=global_neighbors):
            solution.update_cost()
            if len(solution.routes) < current_vehicles:
                fleet_stable = False
                continue
            fleet_stable = False
        
        restore_missing()
        
        # Strategy 2: Route emptying
        if route_empty_inplace(solution):
            solution.update_cost()
            fleet_stable = False
        
        # Strategy 3: Ejection chains (depth-2 only for speed)
        sorted_routes = sorted(range(len(solution.routes)), 
                             key=lambda i: len(solution.routes[i].customer_ids))
        
        for r_idx in sorted_routes[:3]:  # Only try 3 smallest routes
            if r_idx >= len(solution.routes):
                break
            route = solution.routes[r_idx]
            if 0 < len(route.customer_ids) < 6:
                if ejection_chain_reduction(solution, r_idx, max_depth=2):
                    solution.update_cost()
                    fleet_stable = False
                    break
        
        restore_missing()
        
        # Quick convergence check
        if pass_count % 10 == 0:
            if len(solution.routes) == current_vehicles:
                break
    
    print(f"  Fleet reduction complete: {len(solution.routes)} vehicles after {pass_count} passes")
    
    # ===== PHASE 2: Fast Cost Optimization =====
    print("Phase 2: Cost Optimization")
    
    best_solution_cost = solution.total_cost
    best_solution = copy.deepcopy(solution)
    
    # Fast SA parameters
    current_temp = 60.0
    cooling_rate = 0.93
    min_temp = 0.5
    reheat_temp = 40.0
    
    iteration = 0
    no_improvement = 0
    no_best_improvement = 0
    
    # Faster iteration limits
    effective_max_iter = min(max_iterations, 35) if total_customers > 80 else max_iterations
    
    while iteration < effective_max_iter and no_improvement < 60 and no_best_improvement < 40:
        iteration += 1
        
        current_state_backup = copy.deepcopy(solution)
        
        # Fast LNS (smaller removal for speed)
        lns_prob = 0.40 if current_temp > 40 else 0.20
        if random.random() < lns_prob:
            removal_frac = 0.20 + (0.15 * random.random())  # 20-35% removal
            lns_destroy_repair(solution, removal_fraction=removal_frac, random_seed=iteration)
        
        # Inter-route operators (every 2nd iteration for speed)
        if iteration % 2 == 0 and len(solution.routes) > 1:
            rand_val = random.random()
            
            if rand_val < 0.50:
                inter_route_2opt_star(solution, max_attempts=150)
            elif rand_val < 0.75:
                inter_route_relocate_inplace(solution, neighbors=global_neighbors)
            else:
                cross_exchange(solution, max_attempts=25)
        
        # Intra-route refinement (focused on critical routes)
        critical_indices = identify_critical_route_indices(
            solution, top_n=min(top_n_critical, len(solution.routes))
        )
        
        for route_idx in critical_indices:
            route = solution.routes[route_idx]
            if len(route.customer_ids) < 2:
                continue
            
            route_improved = True
            local_iter = 0
            
            while route_improved and local_iter < 4:  # Max 4 local iterations
                route_improved = False
                local_iter += 1
                
                if intra_route_2opt_inplace(route):
                    route_improved = True
                elif or_opt_inplace(route, max_segment_len=3, max_attempts=100):
                    route_improved = True
                elif relocate_operator_inplace(route, temp_arrival_buffer, max_relocations=20):
                    route_improved = True
                
                if route_improved:
                    solution.update_cost()
        
        solution.update_cost()
        
        # Fast SA acceptance
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
            prob = math.exp(-delta / current_temp) if current_temp > min_temp else 0.0
            
            if random.random() < prob:
                accepted = True
                no_best_improvement += 1
            else:
                accepted = False
                no_best_improvement += 1
        
        if not accepted:
            solution = current_state_backup
            no_improvement += 1
        
        # Fast cooling
        current_temp = max(min_temp, current_temp * cooling_rate)
        
        # Reheat if stuck
        if no_best_improvement >= 6 and current_temp < reheat_temp:
            current_temp = reheat_temp
            no_best_improvement = 0
        
        restore_missing()
        
        # Progress reporting (less frequent)
        if iteration % 15 == 0:
            print(f"  Iter {iteration}: Cost={solution.total_base_cost:.2f}, Vehicles={len(solution.routes)}, Temp={current_temp:.2f}")
    
    print(f"Optimization complete: {iteration} iterations")
    return best_solution