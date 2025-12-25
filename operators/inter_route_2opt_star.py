"""
Inter-Route 2-Opt* Operator
Exchanges route tails between two routes to enable better route configurations and merging.
"""

from core.data_structures import Solution
import copy

def inter_route_2opt_star(solution: Solution, max_attempts: int = 50) -> bool:
    """
    Perform inter-route 2-Opt* moves to exchange route tails.
    
    This operator is critical for fleet reduction as it can:
    1. Balance load between routes
    2. Create opportunities for route merging
    3. Reduce total distance by finding better route combinations
    
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
            if len(route_a.customer_ids) < 2 or len(route_b.customer_ids) < 2:
                continue
            
            # Try different cut points
            for cut_a in range(1, len(route_a.customer_ids)):
                for cut_b in range(1, len(route_b.customer_ids)):
                    attempts += 1
                    if attempts > max_attempts:
                        break
                    
                    # Calculate current cost
                    old_cost = route_a.total_cost + route_b.total_cost
                    
                    # Create trial routes by swapping tails
                    new_route_a = copy.deepcopy(route_a)
                    new_route_b = copy.deepcopy(route_b)
                    
                    # Swap tails: A gets B's tail, B gets A's tail
                    tail_a = route_a.customer_ids[cut_a:]
                    tail_b = route_b.customer_ids[cut_b:]
                    
                    new_route_a.customer_ids = route_a.customer_ids[:cut_a] + tail_b
                    new_route_b.customer_ids = route_b.customer_ids[:cut_b] + tail_a
                    
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
    
    # Apply best move if found
    if best_move is not None:
        i, j, new_route_a, new_route_b = best_move
        solution.routes[i] = new_route_a
        solution.routes[j] = new_route_b
        solution.update_cost()
        return True
    
    return False
