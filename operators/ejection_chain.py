"""
Ejection Chain Operator (Depth-2)
- Critical for Fleet Reduction (13 -> 12 vehicles).
- Moves a customer from Target Route to Route A, ejecting a victim from A to B.
- Uses O(N^2) optimizations: Geometric Pruning and Smart Victim Selection.
"""

from core.data_structures import Solution, Route
from typing import List, Optional, Tuple


def ejection_chain_reduction(solution: Solution, target_route_idx: int, max_depth: int = 3) -> bool:
    """
    Variable Depth Ejection Chain (up to Depth-3).
    
    Level 1: Direct relocate C from Target -> Route A
    Level 2: C -> Route A (eject V1) -> Route B (insert V1)
    Level 3: C -> Route A (eject V1) -> Route B (eject V2) -> Route C (insert V1, V2)
    
    Optimizations:
    - Smart victim selection (high demand, loose time windows)
    - Early capacity filtering
    - Geometric pruning
    - Adaptive depth (tries Level 1, then 2, then 3 only if needed)
    
    Returns True if route was reduced/emptied
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
        
        move_success = False
        customer = target_route.customers_lookup[customer_id]
        
        # ===== LEVEL 1: Simple Relocate =====
        for other_idx, other_route in enumerate(solution.routes):
            if other_idx == target_route_idx:
                continue
            
            if other_route.current_load + customer.demand > other_route.vehicle_capacity:
                continue
            
            if not _is_customer_near_route(customer, other_route, threshold=3.0):
                continue
            
            best_pos = -1
            best_cost = float('inf')
            positions = _get_smart_positions(other_route, customer)
            
            for pos in positions:
                delta, feasible = other_route.get_move_delta_cost_for_external_customer(customer_id, pos)
                if feasible and delta < best_cost:
                    best_cost = delta
                    best_pos = pos
            
            if best_pos != -1:
                if other_route.insert_inplace(customer_id, best_pos):
                    old_idx = target_route.customer_ids.index(customer_id)
                    target_route.customer_ids.pop(old_idx)
                    target_route.arrival_times.pop(old_idx)
                    target_route.current_load -= customer.demand
                    target_route._recalculate_from(max(0, old_idx - 1))
                    target_route.calculate_cost_inplace()
                    move_success = True
                    total_moves += 1
                    break
        
        if move_success:
            continue
        
        # ===== LEVEL 2: Depth-2 Ejection Chain =====
        if max_depth >= 2:
            move_success = _try_depth_2_chain(solution, target_route, target_route_idx, customer_id, customer)
            if move_success:
                total_moves += 1
                continue
        
        # ===== LEVEL 3: Depth-3 Ejection Chain (NEW!) =====
        if max_depth >= 3:
            move_success = _try_depth_3_chain(solution, target_route, target_route_idx, customer_id, customer)
            if move_success:
                total_moves += 1
                continue
    
    solution.update_cost()
    return total_moves > 0


def _try_depth_2_chain(solution: Solution, target_route: Route, target_idx: int, 
                       customer_id: int, customer) -> bool:
    """
    Depth-2 Chain: C -> Route A (eject V1) -> Route B (insert V1)
    """
    for route_a_idx, route_a in enumerate(solution.routes):
        if route_a_idx == target_idx:
            continue
        
        if not _is_customer_near_route(customer, route_a, threshold=3.0):
            continue
        
        a_ids_backup = list(route_a.customer_ids)
        a_load_backup = route_a.current_load
        
        victim_candidates = _rank_victims(route_a)
        
        for victim_id in victim_candidates[:6]:  # Increased from 5 to 6
            victim = route_a.customers_lookup[victim_id]
            
            # Remove victim from A
            v_idx = route_a.customer_ids.index(victim_id)
            route_a.customer_ids.pop(v_idx)
            route_a.arrival_times.pop(v_idx)
            route_a.current_load -= victim.demand
            route_a._recalculate_from(max(0, v_idx - 1))
            
            # Try insert C into A
            best_pos_c = -1
            if route_a.current_load + customer.demand <= route_a.vehicle_capacity:
                positions = _get_smart_positions(route_a, customer)
                for pos_c in positions:
                    d, f = route_a.get_move_delta_cost_for_external_customer(customer_id, pos_c)
                    if f:
                        best_pos_c = pos_c
                        break
            
            if best_pos_c != -1:
                if route_a.insert_inplace(customer_id, best_pos_c):
                    # Try insert victim into route B
                    victim_moved = False
                    
                    for route_b_idx, route_b in enumerate(solution.routes):
                        if route_b_idx == target_idx or route_b_idx == route_a_idx:
                            continue
                        
                        if not _is_customer_near_route(victim, route_b, threshold=3.0):
                            continue
                        
                        positions_v = _get_smart_positions(route_b, victim)
                        for pos_v in positions_v:
                            d_v, f_v = route_b.get_move_delta_cost_for_external_customer(victim_id, pos_v)
                            if f_v:
                                if route_b.insert_inplace(victim_id, pos_v):
                                    victim_moved = True
                                    break
                        if victim_moved:
                            break
                    
                    if victim_moved:
                        # SUCCESS
                        old_idx = target_route.customer_ids.index(customer_id)
                        target_route.customer_ids.pop(old_idx)
                        target_route.arrival_times.pop(old_idx)
                        target_route.current_load -= customer.demand
                        target_route._recalculate_from(max(0, old_idx - 1))
                        target_route.calculate_cost_inplace()
                        return True
            
            # Restore route A
            route_a.customer_ids = list(a_ids_backup)
            route_a.current_load = a_load_backup
            route_a._recalculate_from(0)
            route_a.calculate_cost_inplace()
    
    return False


def _try_depth_3_chain(solution: Solution, target_route: Route, target_idx: int,
                       customer_id: int, customer) -> bool:
    """
    Depth-3 Chain: C -> Route A (eject V1) -> Route B (eject V2) -> Route C (insert V1, V2)
    
    This is the "untangler" for complex route dependencies.
    """
    for route_a_idx, route_a in enumerate(solution.routes):
        if route_a_idx == target_idx:
            continue
        
        if not _is_customer_near_route(customer, route_a, threshold=3.5):
            continue
        
        a_ids_backup = list(route_a.customer_ids)
        a_load_backup = route_a.current_load
        
        victim1_candidates = _rank_victims(route_a)
        
        # Try top 3 victims from Route A
        for victim1_id in victim1_candidates[:3]:
            victim1 = route_a.customers_lookup[victim1_id]
            
            # Remove V1 from A
            v1_idx = route_a.customer_ids.index(victim1_id)
            route_a.customer_ids.pop(v1_idx)
            route_a.arrival_times.pop(v1_idx)
            route_a.current_load -= victim1.demand
            route_a._recalculate_from(max(0, v1_idx - 1))
            
            # Try insert C into A
            if route_a.current_load + customer.demand <= route_a.vehicle_capacity:
                positions_c = _get_smart_positions(route_a, customer)
                c_inserted = False
                
                for pos_c in positions_c:
                    d, f = route_a.get_move_delta_cost_for_external_customer(customer_id, pos_c)
                    if f and route_a.insert_inplace(customer_id, pos_c):
                        c_inserted = True
                        break
                
                if c_inserted:
                    # Now try Depth-3: V1 -> Route B (eject V2) -> Route C (insert V1, V2)
                    chain_success = False
                    
                    for route_b_idx, route_b in enumerate(solution.routes):
                        if route_b_idx == target_idx or route_b_idx == route_a_idx:
                            continue
                        
                        if not _is_customer_near_route(victim1, route_b, threshold=3.5):
                            continue
                        
                        b_ids_backup = list(route_b.customer_ids)
                        b_load_backup = route_b.current_load
                        
                        victim2_candidates = _rank_victims(route_b)
                        
                        # Try top 3 victims from Route B
                        for victim2_id in victim2_candidates[:3]:
                            victim2 = route_b.customers_lookup[victim2_id]
                            
                            # Remove V2 from B
                            v2_idx = route_b.customer_ids.index(victim2_id)
                            route_b.customer_ids.pop(v2_idx)
                            route_b.arrival_times.pop(v2_idx)
                            route_b.current_load -= victim2.demand
                            route_b._recalculate_from(max(0, v2_idx - 1))
                            
                            # Try insert V1 into B
                            v1_inserted = False
                            if route_b.current_load + victim1.demand <= route_b.vehicle_capacity:
                                positions_v1 = _get_smart_positions(route_b, victim1)
                                for pos_v1 in positions_v1:
                                    d, f = route_b.get_move_delta_cost_for_external_customer(victim1_id, pos_v1)
                                    if f and route_b.insert_inplace(victim1_id, pos_v1):
                                        v1_inserted = True
                                        break
                            
                            if v1_inserted:
                                # Try insert both V2 into any route C
                                both_inserted = False
                                
                                for route_c_idx, route_c in enumerate(solution.routes):
                                    if route_c_idx in [target_idx, route_a_idx, route_b_idx]:
                                        continue
                                    
                                    # Try insert V2
                                    if route_c.current_load + victim2.demand <= route_c.vehicle_capacity:
                                        positions_v2 = _get_smart_positions(route_c, victim2)
                                        for pos_v2 in positions_v2:
                                            d, f = route_c.get_move_delta_cost_for_external_customer(victim2_id, pos_v2)
                                            if f and route_c.insert_inplace(victim2_id, pos_v2):
                                                both_inserted = True
                                                break
                                    
                                    if both_inserted:
                                        break
                                
                                if both_inserted:
                                    # SUCCESS! Complete Depth-3 chain
                                    old_idx = target_route.customer_ids.index(customer_id)
                                    target_route.customer_ids.pop(old_idx)
                                    target_route.arrival_times.pop(old_idx)
                                    target_route.current_load -= customer.demand
                                    target_route._recalculate_from(max(0, old_idx - 1))
                                    target_route.calculate_cost_inplace()
                                    chain_success = True
                                    break
                            
                            # Restore Route B for next victim2 trial
                            if not chain_success:
                                route_b.customer_ids = list(b_ids_backup)
                                route_b.current_load = b_load_backup
                                route_b._recalculate_from(0)
                                route_b.calculate_cost_inplace()
                        
                        if chain_success:
                            break
                    
                    if chain_success:
                        return True
            
            # Restore Route A for next victim1 trial
            route_a.customer_ids = list(a_ids_backup)
            route_a.current_load = a_load_backup
            route_a._recalculate_from(0)
            route_a.calculate_cost_inplace()
    
    return False


def _is_customer_near_route(customer, route: Route, threshold: float = 3.0) -> bool:
    """
    Geometric pruning with configurable threshold.
    threshold=3.0 is more relaxed than previous 2.5 (finds more moves)
    """
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


def _get_smart_positions(route: Route, customer) -> List[int]:
    """
    Smart position sampling - same as before but called more intelligently
    """
    n = len(route.customer_ids)
    
    if n < 8:
        return list(range(n + 1))
    elif n < 15:
        return [0, n // 4, n // 2, 3 * n // 4, n]
    else:
        return [0, n // 3, 2 * n // 3, n]


def _rank_victims(route: Route) -> List[int]:
    """
    Enhanced victim ranking with better scoring.
    Prioritizes customers that are easier to relocate.
    """
    customers_lookup = route.customers_lookup
    customer_ids = route.customer_ids
    
    if not customer_ids:
        return []
    
    scores = []
    n = len(customer_ids)
    
    for i, cid in enumerate(customer_ids):
        cust = customers_lookup[cid]
        
        # Score components
        demand_score = cust.demand * 0.5  # Higher demand = better victim (easier to insert)
        window_slack = cust.due_date - cust.ready_time
        slack_score = min(window_slack / 80.0, 2.0)  # Normalized, capped at 2.0
        
        # Position score: strongly prefer boundaries
        if i == 0 or i == n - 1:
            position_score = 3.0  # Increased from 2.0
        elif i == 1 or i == n - 2:
            position_score = 2.0  # Increased from 1.5
        else:
            position_score = 1.0
        
        # Combined score (reweighted for better balance)
        total_score = demand_score * 0.35 + slack_score * 0.30 + position_score * 0.35
        scores.append((total_score, cid))
    
    scores.sort(reverse=True)
    return [cid for _, cid in scores]