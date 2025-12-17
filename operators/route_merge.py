"""
Route merging operator for consolidating underfilled routes
Memory efficient: in-place operations only
"""

from typing import Dict, TYPE_CHECKING
from core.data_structures import Solution, Route

if TYPE_CHECKING:
    from core.data_structures import Customer


def merge_underfilled_routes(solution: Solution, 
                             vehicle_capacity: int,
                             customers_lookup: Dict[int, 'Customer'],
                             utilization_threshold: float = 0.5) -> Solution:
    """
    Merge routes that are underutilized (low capacity utilization).
    Attempts to merge customers from smaller/underfilled routes into larger ones.
    
    Args:
        solution: Current solution to improve
        vehicle_capacity: Vehicle capacity constraint
        customers_lookup: Dictionary mapping customer IDs to Customer objects
        utilization_threshold: Minimum utilization to consider a route "underfilled" (0.0-1.0)
    
    Returns:
        Modified solution (same object, modified in place)
    """
    if len(solution.routes) < 2:
        return solution
    
    # Sort routes by load (ascending - smaller routes first)
    routes = solution.routes
    routes_with_load = [(r, r.current_load) for r in routes]
    routes_with_load.sort(key=lambda x: x[1])
    
    merged = True
    while merged:
        merged = False
        solution.update_cost()
        current_obj = solution.total_cost
        
        # Try to merge smaller routes into larger ones
        for i, (src_route, src_load) in enumerate(routes_with_load):
            if src_load / vehicle_capacity > utilization_threshold:
                continue  # Route is sufficiently filled
            
            if len(src_route.customer_ids) == 0:
                continue
            
            # Try merging into other routes
            for j, (dst_route, dst_load) in enumerate(routes_with_load):
                if i == j or dst_route is src_route:
                    continue
                
                # Check if all customers from src can fit into dst
                if dst_load + src_load > vehicle_capacity:
                    continue
                
                # Try moving all customers from src to dst
                customers_to_move = list(src_route.customer_ids)
                moved_all = True
                
                for cust_id in customers_to_move:
                    # Try inserting at end of dst route
                    if not dst_route.insert_inplace(cust_id, len(dst_route.customer_ids)):
                        moved_all = False
                        break
                
                if moved_all:
                    # Successfully merged - remove src route
                    solution.routes = [r for r in solution.routes if r is not src_route]
                    solution.update_cost()
                    
                    # Verify improvement
                    if solution.total_cost < current_obj - 1e-6 or len(solution.routes) < len(routes):
                        merged = True
                        # Rebuild routes_with_load
                        routes = solution.routes
                        routes_with_load = [(r, r.current_load) for r in routes]
                        routes_with_load.sort(key=lambda x: x[1])
                        break
                    else:
                        # Rollback - move customers back
                        for cust_id in customers_to_move:
                            pos = dst_route.customer_ids.index(cust_id)
                            dst_route.customer_ids.pop(pos)
                            dst_route.arrival_times.pop(pos)
                            dst_route.current_load -= customers_lookup[cust_id].demand
                            src_route.customer_ids.append(cust_id)
                            src_route.arrival_times.append(0.0)
                            src_route.current_load += customers_lookup[cust_id].demand
                        
                        # Recalculate schedules
                        src_route._recalculate_from(0)
                        src_route.calculate_cost_inplace()
                        dst_route._recalculate_from(0)
                        dst_route.calculate_cost_inplace()
                        solution.update_cost()
                else:
                    # Rollback partial moves
                    for cust_id in customers_to_move:
                        if cust_id in dst_route.customer_ids:
                            pos = dst_route.customer_ids.index(cust_id)
                            dst_route.customer_ids.pop(pos)
                            dst_route.arrival_times.pop(pos)
                            dst_route.current_load -= customers_lookup[cust_id].demand
                    dst_route._recalculate_from(0)
                    dst_route.calculate_cost_inplace()
            
            if merged:
                break
    
    solution.update_cost()
    return solution

