"""
Cross-Exchange Operator
Swaps segments between two routes for better route configurations.
"""

from core.data_structures import Solution
import copy

def cross_exchange(solution: Solution, max_attempts: int = 50) -> bool:
    """
    Perform cross-exchange moves between route pairs.
    
    Optimized version:
    - No deepcopy - uses in-place trial evaluation with rollback
    - Incremental cost calculation
    - Increased search attempts
    - Segment lengths 1-3 for better exploration
    
    Returns True if any improving move was found.
    """
    if len(solution.routes) < 2:
        return False
    
    best_improvement = 0.0
    best_move = None
    attempts = 0
    
    # Try all pairs of routes
    for i in range(len(solution.routes)):
        for j in range(i + 1, len(solution.routes)):
            route_a = solution.routes[i]
            route_b = solution.routes[j]
            
            # Skip if either route is too small
            if len(route_a.customer_ids) < 1 or len(route_b.customer_ids) < 1:
                continue
            
            # Calculate current cost once
            old_cost = route_a.total_cost + route_b.total_cost
            
            # Try swapping segments of length 1-3
            for seg_len in [1, 2, 3]:
                for pos_a in range(len(route_a.customer_ids) - seg_len + 1):
                    for pos_b in range(len(route_b.customer_ids) - seg_len + 1):
                        attempts += 1
                        if attempts > max_attempts:
                            break
                        
                        # Extract segments
                        seg_a = route_a.customer_ids[pos_a:pos_a + seg_len]
                        seg_b = route_b.customer_ids[pos_b:pos_b + seg_len]
                        
                        # Calculate load changes incrementally
                        seg_a_demand = sum(route_a.customers_lookup[cid].demand for cid in seg_a)
                        seg_b_demand = sum(route_b.customers_lookup[cid].demand for cid in seg_b)
                        
                        new_load_a = route_a.current_load - seg_a_demand + seg_b_demand
                        new_load_b = route_b.current_load - seg_b_demand + seg_a_demand
                        
                        # Quick capacity check
                        if (new_load_a > route_a.vehicle_capacity or
                            new_load_b > route_b.vehicle_capacity):
                            continue
                        
                        # Save original state for rollback
                        orig_ids_a = route_a.customer_ids[:]
                        orig_ids_b = route_b.customer_ids[:]
                        orig_load_a = route_a.current_load
                        orig_load_b = route_b.current_load
                        
                        # Apply swap in-place
                        route_a.customer_ids = (
                            route_a.customer_ids[:pos_a] + 
                            seg_b + 
                            route_a.customer_ids[pos_a + seg_len:]
                        )
                        route_b.customer_ids = (
                            route_b.customer_ids[:pos_b] + 
                            seg_a + 
                            route_b.customer_ids[pos_b + seg_len:]
                        )
                        route_a.current_load = new_load_a
                        route_b.current_load = new_load_b
                        
                        # Recalculate costs and check feasibility
                        new_cost_a = route_a.calculate_cost_inplace()
                        new_cost_b = route_b.calculate_cost_inplace()
                        
                        feasible = route_a.is_feasible() and route_b.is_feasible()
                        
                        if feasible:
                            # Check if this is an improvement
                            new_cost = new_cost_a + new_cost_b
                            improvement = old_cost - new_cost
                            
                            if improvement > best_improvement + 1e-6:
                                best_improvement = improvement
                                best_move = (i, j, route_a.customer_ids[:], route_b.customer_ids[:],
                                           new_load_a, new_load_b)
                        
                        # Rollback changes
                        route_a.customer_ids = orig_ids_a
                        route_b.customer_ids = orig_ids_b
                        route_a.current_load = orig_load_a
                        route_b.current_load = orig_load_b
                        route_a.calculate_cost_inplace()
                        route_b.calculate_cost_inplace()
                    
                    if attempts > max_attempts:
                        break
                
                if attempts > max_attempts:
                    break
            
            if attempts > max_attempts:
                break
        
        if attempts > max_attempts:
            break
    
    # Apply best move if found
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
