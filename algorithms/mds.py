"""
Fast Multi-Directional Search (MDS) - Enhanced Fleet Reduction for R-series
Target: 6-7s runtime with optimal vehicle count
"""

import copy
import math
import random
from typing import List, Set
from core.data_structures import Solution, Route, distance
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


def aggressive_route_merging(solution: Solution, max_attempts: int = 100) -> bool:
    """
    Enhanced route merging with spatial clustering for R-series instances
    Returns True if any routes were merged
    """
    if len(solution.routes) < 2:
        return False
    
    merged_any = False
    attempts = 0
    
    while attempts < max_attempts:
        attempts += 1
        
        if len(solution.routes) < 2:
            break
        
        best_merge_pair = None
        best_merge_cost = float('inf')
        
        for i in range(len(solution.routes)):
            route_i = solution.routes[i]
            
            if len(route_i.customer_ids) == 0:
                continue
            
            centroid_i = route_i.get_centroid()
            
            for j in range(i + 1, len(solution.routes)):
                route_j = solution.routes[j]
                
                if len(route_j.customer_ids) == 0:
                    continue
                
                if route_i.current_load + route_j.current_load > route_i.vehicle_capacity:
                    continue
                
                centroid_j = route_j.get_centroid()
                centroid_dist = math.sqrt((centroid_i[0] - centroid_j[0])**2 + 
                                        (centroid_i[1] - centroid_j[1])**2)
                
                temp_route = Route(route_i.depot, route_i.vehicle_capacity, route_i.customers_lookup)
                temp_route.customer_ids = list(route_i.customer_ids) + list(route_j.customer_ids)
                temp_route.departure_time = min(route_i.departure_time, route_j.departure_time)
                temp_route.current_load = route_i.current_load + route_j.current_load
                temp_route._recalculate_from(0)
                
                if not temp_route.is_feasible():
                    continue
                
                merge_cost = temp_route.calculate_cost_inplace()
                
                if merge_cost < best_merge_cost:
                    best_merge_cost = merge_cost
                    best_merge_pair = (i, j, temp_route)
        
        if best_merge_pair is not None:
            i, j, merged_route = best_merge_pair
            
            solution.routes[i] = merged_route
            solution.routes.pop(j)
            solution.update_cost()
            merged_any = True
        else:
            break
    
    return merged_any


def enhanced_ejection_chain(solution: Solution, target_route_idx: int, max_depth: int = 4) -> bool:
    """
    Enhanced ejection chain with adaptive depth for difficult routes
    Returns True if route was successfully emptied
    """
    if target_route_idx >= len(solution.routes):
        return False
    
    target_route = solution.routes[target_route_idx]
    
    if len(target_route.customer_ids) == 0:
        solution.routes.pop(target_route_idx)
        solution.update_cost()
        return True
    
    customers_to_relocate = list(target_route.customer_ids)
    
    if len(customers_to_relocate) > 8:
        max_depth = min(max_depth, 3)
    
    for depth in range(1, max_depth + 1):
        relocated_all = True
        
        for cust_id in customers_to_relocate:
            best_route_idx = None
            best_position = None
            best_delta = float('inf')
            
            for r_idx, route in enumerate(solution.routes):
                if r_idx == target_route_idx:
                    continue
                
                for pos in range(len(route.customer_ids) + 1):
                    delta, feasible = route.get_move_delta_cost_for_external_customer(cust_id, pos)
                    
                    if feasible and delta < best_delta:
                        best_delta = delta
                        best_route_idx = r_idx
                        best_position = pos
            
            if best_route_idx is None and depth < max_depth:
                relocated_all = False
                break
            elif best_route_idx is None:
                return False
            else:
                if solution.routes[best_route_idx].insert_inplace(cust_id, best_position):
                    # Safety check: only remove if customer is still in target route
                    if cust_id in target_route.customer_ids:
                        target_route.customer_ids.remove(cust_id)
                        target_route.current_load -= target_route.customers_lookup[cust_id].demand
                        target_route._recalculate_from(0)
                        target_route.calculate_cost_inplace()
                else:
                    relocated_all = False
                    break
        
        if relocated_all and len(target_route.customer_ids) == 0:
            solution.routes.pop(target_route_idx)
            solution.update_cost()
            return True
    
    return False


def smart_route_selection_for_elimination(solution: Solution) -> List[int]:
    """
    Intelligently select routes for elimination based on multiple criteria
    Returns list of route indices sorted by elimination priority
    """
    if len(solution.routes) <= 1:
        return []
    
    route_scores = []
    
    for idx, route in enumerate(solution.routes):
        if len(route.customer_ids) == 0:
            route_scores.append((idx, -1000.0))
            continue
        
        size_score = len(route.customer_ids)
        
        load_ratio = route.current_load / route.vehicle_capacity
        utilization_score = 1.0 - load_ratio
        
        avg_slack = route.get_average_slack()
        slack_score = avg_slack / 100.0
        
        centroid = route.get_centroid()
        min_dist_to_other = float('inf')
        
        for other_idx, other_route in enumerate(solution.routes):
            if other_idx == idx or len(other_route.customer_ids) == 0:
                continue
            
            other_centroid = other_route.get_centroid()
            dist = math.sqrt((centroid[0] - other_centroid[0])**2 + 
                           (centroid[1] - other_centroid[1])**2)
            
            if dist < min_dist_to_other:
                min_dist_to_other = dist
        
        proximity_score = 1.0 / (min_dist_to_other + 1.0)
        
        total_score = (
            size_score * 3.0 +
            utilization_score * 2.0 +
            slack_score * 1.5 +
            proximity_score * 2.5
        )
        
        route_scores.append((idx, total_score))
    
    route_scores.sort(key=lambda x: x[1])
    
    return [idx for idx, _ in route_scores]


def selective_mds(solution: Solution,
                  max_iterations: int = 50,
                  top_n_critical: int = 5,
                  early_termination: int = 40) -> Solution:
    """
    Fast MDS with enhanced fleet reduction for R-series
    Phase 1: Aggressive Fleet Reduction
    Phase 2: Cost Optimization
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
    
    if total_customers > 100:
        top_n_critical = 2
        max_iterations = min(max_iterations, 30)
        early_termination = 20
        fleet_passes = 35
        ejection_max_depth = 3
    elif total_customers < 30:
        max_iterations = min(max_iterations, 20)
        early_termination = 15
        fleet_passes = 25
        ejection_max_depth = 5
    else:
        fleet_passes = 80  # INCREASED from 45 for better reduction
        ejection_max_depth = 4
    
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
    
    print("Phase 1: Aggressive Fleet Reduction")
    fleet_stable = False
    pass_count = 0
    
    initial_vehicle_count = len(solution.routes)
    
    while not fleet_stable and pass_count < fleet_passes:
        pass_count += 1
        fleet_stable = True
        
        current_vehicles = len(solution.routes)
        
        if inter_route_relocate_inplace(solution, temp_arrival_buffer, neighbors=global_neighbors):
            solution.update_cost()
            if len(solution.routes) < current_vehicles:
                fleet_stable = False
                continue
            fleet_stable = False
        
        restore_missing()
        
        if route_empty_inplace(solution):
            solution.update_cost()
            fleet_stable = False
        
        if aggressive_route_merging(solution, max_attempts=30):
            solution.update_cost()
            fleet_stable = False
        
        priority_routes = smart_route_selection_for_elimination(solution)
        
        # FIX: Try ALL routes (not just top 5) and increase customer threshold
        for r_idx in priority_routes:  # Try ALL routes
            if r_idx >= len(solution.routes):
                break
            
            route = solution.routes[r_idx]
            
            # FIX: Increased from 8 to 20 to handle larger routes
            if 0 < len(route.customer_ids) <= 20:
                if enhanced_ejection_chain(solution, r_idx, max_depth=ejection_max_depth):
                    solution.update_cost()
                    fleet_stable = False
                    break
        
        restore_missing()
        
        # FIX: Removed early termination - let it run full passes
        # Early termination was stopping at 60% of passes
        if pass_count % 15 == 0:
            if len(solution.routes) == current_vehicles:
                # Only break if NO improvement AND we've done enough passes
                if pass_count > fleet_passes * 0.8:
                    break
    
    vehicles_reduced = initial_vehicle_count - len(solution.routes)
    print(f"  Fleet reduction: {initial_vehicle_count} → {len(solution.routes)} (-{vehicles_reduced} vehicles) in {pass_count} passes")
    
    print("Phase 2: Cost Optimization")
    
    best_solution_cost = solution.total_cost
    best_solution = copy.deepcopy(solution)
    
    current_temp = 60.0
    cooling_rate = 0.93
    min_temp = 0.5
    reheat_temp = 40.0
    
    iteration = 0
    no_improvement = 0
    no_best_improvement = 0
    
    effective_max_iter = min(max_iterations, 35) if total_customers > 80 else max_iterations
    
    while iteration < effective_max_iter and no_improvement < 60 and no_best_improvement < 40:
        iteration += 1
        
        current_state_backup = copy.deepcopy(solution)
        
        lns_prob = 0.40 if current_temp > 40 else 0.20
        if random.random() < lns_prob:
            removal_frac = 0.20 + (0.15 * random.random())
            lns_destroy_repair(solution, removal_fraction=removal_frac, random_seed=iteration)
        
        if iteration % 2 == 0 and len(solution.routes) > 1:
            rand_val = random.random()
            
            if rand_val < 0.50:
                inter_route_2opt_star(solution, max_attempts=150)
            elif rand_val < 0.75:
                inter_route_relocate_inplace(solution, neighbors=global_neighbors)
            else:
                cross_exchange(solution, max_attempts=25)
        
        critical_indices = identify_critical_route_indices(
            solution, top_n=min(top_n_critical, len(solution.routes))
        )
        
        for route_idx in critical_indices:
            route = solution.routes[route_idx]
            if len(route.customer_ids) < 2:
                continue
            
            route_improved = True
            local_iter = 0
            
            while route_improved and local_iter < 4:
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
        
        new_cost = solution.total_cost
        curr_cost = current_state_backup.total_cost
        delta = new_cost - curr_cost
        
        new_vehicles = len(solution.routes)
        old_vehicles = len(current_state_backup.routes)
        
        accepted = False
        
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
        
        current_temp = max(min_temp, current_temp * cooling_rate)
        
        if no_best_improvement >= 6 and current_temp < reheat_temp:
            current_temp = reheat_temp
            no_best_improvement = 0
        
        restore_missing()
        
        if iteration % 15 == 0:
            print(f"  Iter {iteration}: Cost={solution.total_base_cost:.2f}, Vehicles={len(solution.routes)}, Temp={current_temp:.2f}")
    
    print(f"Optimization complete: {iteration} iterations")
    print(f"Final solution: {len(best_solution.routes)} vehicles, cost={best_solution.total_base_cost:.2f}")
    
    return best_solution