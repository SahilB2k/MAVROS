"""
AGGRESSIVE COST REDUCTION MODULE
Add this to your operators/ directory as aggressive_cost_optimizer.py

This module implements high-intensity operators that aggressively reduce cost:
1. String Relocation (move sequences between routes)
2. Intensive 3-Opt within routes
3. Route Splitting & Merging
"""

from core.data_structures import Solution, Route
from typing import List, Tuple
import random


def aggressive_cost_reduction(solution: Solution, max_attempts: int = 200) -> bool:
    """
    Apply aggressive cost reduction strategies.
    Call this AFTER fleet reduction but BEFORE final refinement.
    
    Returns True if any improvement found.
    """
    improved = False
    
    # Strategy 1: String Relocation (move 2-3 consecutive customers)
    if string_relocation(solution, max_attempts=max_attempts // 3):
        improved = True
        solution.update_cost()
    
    # Strategy 2: Intensive Intra-Route 3-Opt
    if intensive_3opt_all_routes(solution, max_attempts=max_attempts // 3):
        improved = True
        solution.update_cost()
    
    # Strategy 3: Route Splitting with Reinsertion
    if split_and_reinsert(solution, max_attempts=max_attempts // 3):
        improved = True
        solution.update_cost()
    
    return improved


def string_relocation(solution: Solution, max_attempts: int = 100) -> bool:
    """
    Move strings of 2-3 consecutive customers between routes.
    More powerful than single-customer relocate.
    """
    if len(solution.routes) < 2:
        return False
    
    best_improvement = 0.0
    best_move = None
    attempts = 0
    
    # Try relocating strings from each route
    for src_idx in range(len(solution.routes)):
        src_route = solution.routes[src_idx]
        
        if len(src_route.customer_ids) < 3:
            continue
        
        # Try different string lengths (2-3 customers)
        for string_len in [2, 3]:
            if len(src_route.customer_ids) < string_len:
                continue
            
            # Try each starting position
            for start_pos in range(len(src_route.customer_ids) - string_len + 1):
                if attempts >= max_attempts:
                    break
                
                string_customers = src_route.customer_ids[start_pos:start_pos + string_len]
                string_demand = sum(src_route.customers_lookup[cid].demand for cid in string_customers)
                
                old_src_cost = src_route.total_cost
                
                # Try inserting into other routes
                for dst_idx in range(len(solution.routes)):
                    if dst_idx == src_idx:
                        continue
                    
                    dst_route = solution.routes[dst_idx]
                    
                    # Quick capacity check
                    if dst_route.current_load + string_demand > dst_route.vehicle_capacity:
                        continue
                    
                    # Try each insertion position
                    for insert_pos in range(len(dst_route.customer_ids) + 1):
                        attempts += 1
                        if attempts >= max_attempts:
                            break
                        
                        old_dst_cost = dst_route.total_cost
                        
                        # Save states
                        src_backup = list(src_route.customer_ids)
                        dst_backup = list(dst_route.customer_ids)
                        src_load_backup = src_route.current_load
                        dst_load_backup = dst_route.current_load
                        
                        # Remove from source
                        for cid in string_customers:
                            src_route.customer_ids.remove(cid)
                        src_route.current_load -= string_demand
                        
                        # Insert into destination
                        for i, cid in enumerate(string_customers):
                            dst_route.customer_ids.insert(insert_pos + i, cid)
                        dst_route.current_load += string_demand
                        
                        # Recalculate costs
                        src_route._recalculate_from(0)
                        dst_route._recalculate_from(0)
                        new_src_cost = src_route.calculate_cost_inplace()
                        new_dst_cost = dst_route.calculate_cost_inplace()
                        
                        # Check feasibility and improvement
                        if src_route.is_feasible() and dst_route.is_feasible():
                            improvement = (old_src_cost + old_dst_cost) - (new_src_cost + new_dst_cost)
                            
                            if improvement > best_improvement + 0.01:
                                best_improvement = improvement
                                best_move = (src_idx, dst_idx, 
                                           list(src_route.customer_ids), 
                                           list(dst_route.customer_ids),
                                           src_route.current_load,
                                           dst_route.current_load)
                        
                        # Restore
                        src_route.customer_ids = src_backup
                        dst_route.customer_ids = dst_backup
                        src_route.current_load = src_load_backup
                        dst_route.current_load = dst_load_backup
                        src_route._recalculate_from(0)
                        dst_route._recalculate_from(0)
                        src_route.calculate_cost_inplace()
                        dst_route.calculate_cost_inplace()
    
    # Apply best move
    if best_move is not None:
        src_idx, dst_idx, new_src_ids, new_dst_ids, new_src_load, new_dst_load = best_move
        solution.routes[src_idx].customer_ids = new_src_ids
        solution.routes[dst_idx].customer_ids = new_dst_ids
        solution.routes[src_idx].current_load = new_src_load
        solution.routes[dst_idx].current_load = new_dst_load
        solution.routes[src_idx].calculate_cost_inplace()
        solution.routes[dst_idx].calculate_cost_inplace()
        return True
    
    return False


def intensive_3opt_all_routes(solution: Solution, max_attempts: int = 100) -> bool:
    """
    Apply intensive 3-opt to all routes (especially high-cost ones).
    3-opt can untangle complex crossing patterns that 2-opt misses.
    """
    improved = False
    
    # Sort routes by cost density (cost per customer)
    route_indices = list(range(len(solution.routes)))
    route_indices.sort(key=lambda i: solution.routes[i].total_cost / max(1, len(solution.routes[i].customer_ids)), 
                      reverse=True)
    
    # Apply 3-opt to top routes
    for route_idx in route_indices[:min(5, len(route_indices))]:
        route = solution.routes[route_idx]
        
        if len(route.customer_ids) < 4:
            continue
        
        if intra_route_3opt(route, max_attempts=max_attempts // 5):
            improved = True
            solution.update_cost()
    
    return improved


def intra_route_3opt(route: Route, max_attempts: int = 50) -> bool:
    """
    3-opt within a single route.
    Removes 3 edges and reconnects in the best possible way.
    """
    n = len(route.customer_ids)
    if n < 4:
        return False
    
    best_improvement = 0.0
    best_sequence = None
    attempts = 0
    
    # Try different 3-opt configurations
    for i in range(n - 2):
        for j in range(i + 1, n - 1):
            for k in range(j + 1, n):
                attempts += 1
                if attempts >= max_attempts:
                    break
                
                # Original sequence: [0...i][i+1...j][j+1...k][k+1...n]
                # Try different reconnections
                
                # Configuration 1: Reverse middle segment
                seq1 = (route.customer_ids[:i+1] + 
                       route.customer_ids[i+1:j+1][::-1] + 
                       route.customer_ids[j+1:])
                
                # Configuration 2: Reverse last segment
                seq2 = (route.customer_ids[:j+1] + 
                       route.customer_ids[j+1:k+1][::-1] + 
                       route.customer_ids[k+1:])
                
                # Configuration 3: Swap middle and last segments
                seq3 = (route.customer_ids[:i+1] + 
                       route.customer_ids[j+1:k+1] + 
                       route.customer_ids[i+1:j+1] + 
                       route.customer_ids[k+1:])
                
                for seq in [seq1, seq2, seq3]:
                    old_cost = route.total_cost
                    old_ids = route.customer_ids[:]
                    
                    route.customer_ids = seq
                    route._recalculate_from(0)
                    new_cost = route.calculate_cost_inplace()
                    
                    if route.is_feasible():
                        improvement = old_cost - new_cost
                        if improvement > best_improvement + 0.01:
                            best_improvement = improvement
                            best_sequence = seq[:]
                    
                    # Restore
                    route.customer_ids = old_ids
                    route._recalculate_from(0)
                    route.calculate_cost_inplace()
                
                if attempts >= max_attempts:
                    break
            if attempts >= max_attempts:
                break
    
    # Apply best sequence
    if best_sequence is not None:
        route.customer_ids = best_sequence
        route._recalculate_from(0)
        route.calculate_cost_inplace()
        return True
    
    return False


def split_and_reinsert(solution: Solution, max_attempts: int = 50) -> bool:
    """
    Split routes at weak points and reinsert customers optimally.
    Finds better customer-to-route assignments.
    """
    if len(solution.routes) < 2:
        return False
    
    improved = False
    
    # Find routes with high waiting time (suboptimal)
    high_wait_routes = []
    for i, route in enumerate(solution.routes):
        if len(route.customer_ids) > 0:
            wait_time = route.get_waiting_time()
            avg_wait = wait_time / len(route.customer_ids)
            if avg_wait > 5.0:  # Significant waiting
                high_wait_routes.append((avg_wait, i))
    
    high_wait_routes.sort(reverse=True)
    
    # Process top 2 routes with high waiting time
    for _, route_idx in high_wait_routes[:2]:
        route = solution.routes[route_idx]
        
        if len(route.customer_ids) < 3:
            continue
        
        # Find customers with high waiting time
        wait_contributions = route.get_waiting_contributions()
        wait_contributions.sort(key=lambda x: x[1], reverse=True)
        
        # Try relocating top 2 high-wait customers
        for cust_id, wait in wait_contributions[:2]:
            if cust_id not in route.customer_ids:
                continue
            
            customer = route.customers_lookup[cust_id]
            old_route_cost = route.total_cost
            
            # Remove from current route
            old_idx = route.customer_ids.index(cust_id)
            route.customer_ids.pop(old_idx)
            route.current_load -= customer.demand
            route._recalculate_from(0)
            new_route_cost = route.calculate_cost_inplace()
            
            # Try inserting into ALL other routes (exhaustive for these critical customers)
            best_insert = None
            best_delta = float('inf')
            
            for other_idx, other_route in enumerate(solution.routes):
                if other_idx == route_idx:
                    continue
                
                if other_route.current_load + customer.demand > other_route.vehicle_capacity:
                    continue
                
                for pos in range(len(other_route.customer_ids) + 1):
                    delta, feasible = other_route.get_move_delta_cost_for_external_customer(cust_id, pos)
                    if feasible:
                        total_delta = (new_route_cost - old_route_cost) + delta
                        if total_delta < best_delta - 0.01:
                            best_delta = total_delta
                            best_insert = (other_idx, pos)
            
            # Apply best insertion or restore
            if best_insert is not None and best_delta < -0.01:
                other_idx, pos = best_insert
                solution.routes[other_idx].insert_inplace(cust_id, pos)
                improved = True
            else:
                # Restore to original route
                route.customer_ids.insert(old_idx, cust_id)
                route.current_load += customer.demand
                route._recalculate_from(0)
                route.calculate_cost_inplace()
    
    return improved