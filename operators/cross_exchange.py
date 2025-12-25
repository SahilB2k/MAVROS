"""
Cross-Exchange Operator
Swaps segments between two routes for better route configurations.
"""

from core.data_structures import Solution
import copy

def cross_exchange(solution: Solution, max_attempts: int = 30) -> bool:
    """
    Perform cross-exchange moves between route pairs.
    
    Swaps segments (1-2 customers) between routes to:
    1. Improve route quality
    2. Balance loads
    3. Enable route merging opportunities
    
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
            
            # Try swapping segments of length 1-2
            for seg_len in [1, 2]:
                for pos_a in range(len(route_a.customer_ids) - seg_len + 1):
                    for pos_b in range(len(route_b.customer_ids) - seg_len + 1):
                        attempts += 1
                        if attempts > max_attempts:
                            break
                        
                        # Calculate current cost
                        old_cost = route_a.total_cost + route_b.total_cost
                        
                        # Create trial routes
                        new_route_a = copy.deepcopy(route_a)
                        new_route_b = copy.deepcopy(route_b)
                        
                        # Extract segments
                        seg_a = route_a.customer_ids[pos_a:pos_a + seg_len]
                        seg_b = route_b.customer_ids[pos_b:pos_b + seg_len]
                        
                        # Swap segments
                        new_route_a.customer_ids = (
                            route_a.customer_ids[:pos_a] + 
                            seg_b + 
                            route_a.customer_ids[pos_a + seg_len:]
                        )
                        new_route_b.customer_ids = (
                            route_b.customer_ids[:pos_b] + 
                            seg_a + 
                            route_b.customer_ids[pos_b + seg_len:]
                        )
                        
                        # Update loads
                        new_route_a.current_load = sum(
                            new_route_a.customers_lookup[cid].demand 
                            for cid in new_route_a.customer_ids
                        )
                        new_route_b.current_load = sum(
                            new_route_b.customers_lookup[cid].demand 
                            for cid in new_route_b.customer_ids
                        )
                        
                        # Check capacity
                        if (new_route_a.current_load > new_route_a.vehicle_capacity or
                            new_route_b.current_load > new_route_b.vehicle_capacity):
                            continue
                        
                        # Recalculate costs and check feasibility
                        new_cost_a = new_route_a.calculate_cost_inplace()
                        new_cost_b = new_route_b.calculate_cost_inplace()
                        
                        if not new_route_a.is_feasible() or not new_route_b.is_feasible():
                            continue
                        
                        # Check if this is an improvement
                        new_cost = new_cost_a + new_cost_b
                        improvement = old_cost - new_cost
                        
                        if improvement > best_improvement:
                            best_improvement = improvement
                            best_move = (i, j, new_route_a, new_route_b)
                    
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
        i, j, new_route_a, new_route_b = best_move
        solution.routes[i] = new_route_a
        solution.routes[j] = new_route_b
        solution.update_cost()
        return True
    
    return False
