"""
Fast Ejection Chain Operator (Depth-2)
Optimized for fleet reduction with minimal overhead
"""

from core.data_structures import Solution, Route, distance
from typing import List


def ejection_chain_reduction(solution: Solution, target_route_idx: int, max_depth: int = 2) -> bool:
    """
    Fast ejection chain with depth-2 limit (depth-3 too slow for real-time)
    
    Level 1: Direct relocate C from Target -> Route A
    Level 2: C -> Route A (eject V1) -> Route B (insert V1)
    """
    if target_route_idx >= len(solution.routes):
        return False
    
    target_route = solution.routes[target_route_idx]
    if len(target_route.customer_ids) == 0:
        return True
    
    customers_to_move = list(target_route.customer_ids)
    total_moves = 0
    
    for customer_id in customers_to_move:
        if customer_id not in target_route.customer_ids:
            continue
        
        customer = target_route.customers_lookup[customer_id]
        
        # ===== LEVEL 1: Direct Relocate =====
        for other_idx, other_route in enumerate(solution.routes):
            if other_idx == target_route_idx:
                continue
            
            if other_route.current_load + customer.demand > other_route.vehicle_capacity:
                continue
            
            if not _is_customer_near_route(customer, other_route, threshold=3.5):
                continue
            
            # Try smart positions only
            positions = _get_fast_positions(other_route)
            
            for pos in positions:
                delta, feasible = other_route.get_move_delta_cost_for_external_customer(customer_id, pos)
                if feasible:
                    if other_route.insert_inplace(customer_id, pos):
                        old_idx = target_route.customer_ids.index(customer_id)
                        target_route.customer_ids.pop(old_idx)
                        target_route.arrival_times.pop(old_idx)
                        target_route.current_load -= customer.demand
                        target_route._recalculate_from(max(0, old_idx - 1))
                        target_route.calculate_cost_inplace()
                        total_moves += 1
                        break
            
            if customer_id not in target_route.customer_ids:
                break
        
        if customer_id not in target_route.customer_ids:
            continue
        
        # ===== LEVEL 2: Depth-2 Chain (fast version) =====
        if max_depth >= 2:
            if _try_fast_depth_2_chain(solution, target_route, target_route_idx, customer_id, customer):
                total_moves += 1
    
    solution.update_cost()
    return total_moves > 0


def _try_fast_depth_2_chain(solution: Solution, target_route: Route, target_idx: int, 
                            customer_id: int, customer) -> bool:
    """
    Fast depth-2: Try top 3 victims only
    """
    for route_a_idx, route_a in enumerate(solution.routes):
        if route_a_idx == target_idx:
            continue
        
        if not _is_customer_near_route(customer, route_a, threshold=3.5):
            continue
        
        # Backup
        a_ids_backup = list(route_a.customer_ids)
        a_load_backup = route_a.current_load
        
        # Try only top 3 victims
        victim_candidates = _rank_victims_fast(route_a)[:3]
        
        for victim_id in victim_candidates:
            victim = route_a.customers_lookup[victim_id]
            
            # Remove victim from A
            v_idx = route_a.customer_ids.index(victim_id)
            route_a.customer_ids.pop(v_idx)
            route_a.arrival_times.pop(v_idx)
            route_a.current_load -= victim.demand
            route_a._recalculate_from(max(0, v_idx - 1))
            
            # Try insert customer into A
            if route_a.current_load + customer.demand <= route_a.vehicle_capacity:
                positions = _get_fast_positions(route_a)
                
                for pos_c in positions:
                    d, f = route_a.get_move_delta_cost_for_external_customer(customer_id, pos_c)
                    if f and route_a.insert_inplace(customer_id, pos_c):
                        # Try insert victim into any route B
                        for route_b_idx, route_b in enumerate(solution.routes):
                            if route_b_idx in [target_idx, route_a_idx]:
                                continue
                            
                            if not _is_customer_near_route(victim, route_b, threshold=3.5):
                                continue
                            
                            positions_v = _get_fast_positions(route_b)
                            for pos_v in positions_v:
                                d_v, f_v = route_b.get_move_delta_cost_for_external_customer(victim_id, pos_v)
                                if f_v and route_b.insert_inplace(victim_id, pos_v):
                                    # SUCCESS
                                    old_idx = target_route.customer_ids.index(customer_id)
                                    target_route.customer_ids.pop(old_idx)
                                    target_route.arrival_times.pop(old_idx)
                                    target_route.current_load -= customer.demand
                                    target_route._recalculate_from(max(0, old_idx - 1))
                                    target_route.calculate_cost_inplace()
                                    return True
                        
                        # Failed - restore A
                        break
            
            # Restore route A
            route_a.customer_ids = list(a_ids_backup)
            route_a.current_load = a_load_backup
            route_a._recalculate_from(0)
            route_a.calculate_cost_inplace()
    
    return False


def _is_customer_near_route(customer, route: Route, threshold: float = 3.5) -> bool:
    """Fast geometric pruning"""
    if not route.customer_ids:
        return True
    
    bbox = route.bbox
    avg_span = ((bbox[2] - bbox[0]) + (bbox[3] - bbox[1])) / 2
    
    if avg_span == 0:
        return True
    
    cx, cy = customer.x, customer.y
    min_x, min_y, max_x, max_y = bbox
    
    buffer = threshold * avg_span
    if (cx < min_x - buffer or cx > max_x + buffer or
        cy < min_y - buffer or cy > max_y + buffer):
        return False
    
    return True


def _get_fast_positions(route: Route) -> List[int]:
    """Fast position sampling - only boundaries and middle"""
    n = len(route.customer_ids)
    
    if n < 5:
        return list(range(n + 1))
    elif n < 10:
        return [0, n // 2, n]
    else:
        return [0, n // 3, 2 * n // 3, n]


def _rank_victims_fast(route: Route) -> List[int]:
    """
    Fast victim ranking - prioritize boundaries
    """
    customer_ids = route.customer_ids
    
    if not customer_ids:
        return []
    
    # For speed, just prioritize boundaries
    n = len(customer_ids)
    if n <= 2:
        return customer_ids
    
    # Boundaries first, then others
    ranked = [customer_ids[0], customer_ids[-1]]
    
    if n > 2:
        ranked.extend(customer_ids[1:-1])
    
    return ranked