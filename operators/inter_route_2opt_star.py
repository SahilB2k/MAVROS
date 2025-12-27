"""
Inter-Route 2-Opt* Operator - O(N²) Optimized
Smart filtering + adaptive sampling for 3x speedup
"""

from core.data_structures import Solution
import random


def inter_route_2opt_star(solution: Solution, max_attempts: int = 500) -> bool:
    """
    Optimized 2-Opt* with:
    - Geometric pruning (bbox overlap check)
    - Adaptive cut point sampling (not exhaustive)
    - Early capacity filtering
    - Best-improvement strategy
    
    Returns True if improving move found
    """
    if len(solution.routes) < 2:
        return False
    
    best_improvement = 0.0
    best_move = None
    global_attempts = 0
    
    # Prioritize high-cost route pairs
    route_priorities = []
    for i in range(len(solution.routes)):
        for j in range(i + 1, len(solution.routes)):
            route_a = solution.routes[i]
            route_b = solution.routes[j]
            
            if len(route_a.customer_ids) < 1 or len(route_b.customer_ids) < 1:
                continue
            
            # Geometric pruning: Skip non-overlapping routes
            if not route_a.overlaps_with(route_b, buffer=25.0):
                continue
            
            avg_cost = (route_a.total_cost / max(1, len(route_a.customer_ids)) +
                       route_b.total_cost / max(1, len(route_b.customer_ids)))
            route_priorities.append((avg_cost + random.random() * 0.1, i, j))
    
    route_priorities.sort(reverse=True)
    
    # Try route pairs in priority order
    for _, i, j in route_priorities:
        if global_attempts > max_attempts:
            break
            
        route_a = solution.routes[i]
        route_b = solution.routes[j]
        
        old_cost = route_a.total_cost + route_b.total_cost
        
        # OPTIMIZATION: Adaptive sampling strategy
        # For large routes (>15 customers), sample cut points instead of exhaustive search
        len_a = len(route_a.customer_ids)
        len_b = len(route_b.customer_ids)
        
        if len_a > 15 and len_b > 15:
            # Sample strategic cut points: early (20%), mid (40%), late (70%)
            cuts_a = [max(1, int(len_a * p)) for p in [0.2, 0.4, 0.6, 0.8]]
            cuts_b = [max(1, int(len_b * p)) for p in [0.2, 0.4, 0.6, 0.8]]
        elif len_a > 15:
            cuts_a = [max(1, int(len_a * p)) for p in [0.25, 0.5, 0.75]]
            cuts_b = list(range(1, len_b))
        elif len_b > 15:
            cuts_a = list(range(1, len_a))
            cuts_b = [max(1, int(len_b * p)) for p in [0.25, 0.5, 0.75]]
        else:
            # Small routes: exhaustive search
            cuts_a = list(range(1, len_a))
            cuts_b = list(range(1, len_b))
        
        pair_attempts = 0
        max_pair_attempts = min(50, len(cuts_a) * len(cuts_b))
        
        for cut_a in cuts_a:
            for cut_b in cuts_b:
                global_attempts += 1
                pair_attempts += 1
                
                if global_attempts > max_attempts or pair_attempts > max_pair_attempts:
                    break
                
                # Prepare swapped tails
                tail_a = route_a.customer_ids[cut_a:]
                tail_b = route_b.customer_ids[cut_b:]
                
                # OPTIMIZATION: Quick capacity pre-filter
                tail_a_demand = sum(route_a.customers_lookup[cid].demand for cid in tail_a)
                tail_b_demand = sum(route_b.customers_lookup[cid].demand for cid in tail_b)
                
                new_load_a = route_a.current_load - tail_a_demand + tail_b_demand
                new_load_b = route_b.current_load - tail_b_demand + tail_a_demand
                
                if (new_load_a > route_a.vehicle_capacity or
                    new_load_b > route_b.vehicle_capacity):
                    continue
                
                # Save state
                orig_ids_a = route_a.customer_ids[:]
                orig_ids_b = route_b.customer_ids[:]
                orig_load_a = route_a.current_load
                orig_load_b = route_b.current_load
                
                # Apply swap
                route_a.customer_ids = route_a.customer_ids[:cut_a] + tail_b
                route_b.customer_ids = route_b.customer_ids[:cut_b] + tail_a
                route_a.current_load = new_load_a
                route_b.current_load = new_load_b
                
                # Evaluate
                new_cost_a = route_a.calculate_cost_inplace()
                new_cost_b = route_b.calculate_cost_inplace()
                
                feasible = route_a.is_feasible() and route_b.is_feasible()
                
                if feasible:
                    new_cost = new_cost_a + new_cost_b
                    improvement = old_cost - new_cost
                    
                    if improvement > best_improvement + 1e-6:
                        best_improvement = improvement
                        best_move = (i, j, route_a.customer_ids[:], route_b.customer_ids[:],
                                   new_load_a, new_load_b)
                
                # Rollback
                route_a.customer_ids = orig_ids_a
                route_b.customer_ids = orig_ids_b
                route_a.current_load = orig_load_a
                route_b.current_load = orig_load_b
                route_a.calculate_cost_inplace()
                route_b.calculate_cost_inplace()
            
            if global_attempts > max_attempts or pair_attempts > max_pair_attempts:
                break
    
    # Apply best move
    if best_move is not None:
        i, j, new_ids_a, new_ids_b, new_load_a, new_load_b = best_move
        solution.routes[i].customer_ids = new_ids_a
        solution.routes[j].customer_ids = new_ids_b
        solution.routes[i].current_load = new_load_a
        solution.routes[j].current_load = new_load_b
        solution.routes[i].calculate_cost_inplace()
        solution.routes[j].calculate_cost_inplace()
        solution.update_cost()
        return True
    
    return False