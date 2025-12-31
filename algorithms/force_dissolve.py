"""
Force-Dissolve Fleet Reduction for VRPTW
Reduces solution to target number of vehicles (typically 3 for R-series)

Key Features:
1. Iteratively dissolve smallest routes
2. Squeeze insertion with 10% time window + 5% capacity relaxation
3. Feasibility restoration after constraint violations
"""

import copy
from typing import List, Optional
from core.data_structures import Solution, Route, Customer, distance
from operators.intra_route_2opt import intra_route_2opt_inplace


def calculate_insertion_violation(
    route: Route,
    customer_id: int,
    position: int,
    time_tolerance: float = 0.10,
    capacity_tolerance: float = 0.05
) -> float:
    """
    Calculate constraint violation for insertion.
    
    Returns:
        Total violation score (0 = feasible, >0 = violation)
    """
    customer = route.customers_lookup[customer_id]
    
    # Check capacity violation
    new_load = route.current_load + customer.demand
    max_allowed_capacity = route.vehicle_capacity * (1.0 + capacity_tolerance)
    
    if new_load > max_allowed_capacity:
        capacity_violation = (new_load - max_allowed_capacity) / route.vehicle_capacity
    else:
        capacity_violation = 0.0
    
    # Check time window violation
    # Calculate arrival time at customer
    if position == 0:
        prev_departure = 0.0
        prev_location = route.depot
    else:
        if position - 1 < len(route.customer_ids):
            prev_customer = route.get_customer(position - 1)
            if position - 1 < len(route.arrival_times):
                prev_arrival = route.arrival_times[position - 1]
            else:
                prev_arrival = 0.0
            prev_service_start = max(prev_arrival, prev_customer.ready_time)
            prev_departure = prev_service_start + prev_customer.service_time
            prev_location = prev_customer
        else:
            prev_departure = 0.0
            prev_location = route.depot
    
    travel_time = distance(prev_location, customer)
    arrival = prev_departure + travel_time
    
    # Check with tolerance
    max_allowed_time = customer.due_date * (1.0 + time_tolerance)
    
    if arrival > max_allowed_time:
        time_violation = (arrival - max_allowed_time) / customer.due_date
    else:
        time_violation = 0.0
    
    return time_violation + capacity_violation


def squeeze_insert(
    solution: Solution,
    customer_id: int,
    time_tolerance: float = 0.10,
    capacity_tolerance: float = 0.05
) -> bool:
    """
    Insert customer with constraint relaxation (the "squeeze").
    
    Args:
        solution: Current solution
        customer_id: Customer to insert
        time_tolerance: Time window tolerance (10%)
        capacity_tolerance: Capacity tolerance (5%)
    
    Returns:
        True if insertion successful
    """
    customer = solution.routes[0].customers_lookup[customer_id]
    
    best_route = None
    best_pos = None
    best_violation = float('inf')
    
    # Try all positions in all routes
    for route in solution.routes:
        for pos in range(len(route.customer_ids) + 1):
            violation = calculate_insertion_violation(
                route, customer_id, pos, time_tolerance, capacity_tolerance
            )
            
            if violation < best_violation:
                best_violation = violation
                best_route = route
                best_pos = pos
    
    # Force insertion at best position (AFTER finding it)
    if best_route is not None:
        best_route.customer_ids.insert(best_pos, customer_id)
        best_route.current_load += customer.demand
        best_route._recalculate_from(max(0, best_pos - 1))
        
        # CRITICAL: Recalculate cost properly
        cost = best_route.calculate_cost_inplace()
        
        # Safety check: if cost is inf, something went wrong
        if cost == float('inf'):
            print(f"      WARNING: Squeeze insertion of customer {customer_id} resulted in inf cost")
            # Try to fix by recalculating from scratch
            best_route._recalculate_from(0)
            cost = best_route.calculate_cost_inplace()
            
            if cost == float('inf'):
                print(f"      ERROR: Customer {customer_id} still has inf cost after recalculation")
        
        return True
    
    return False


def force_dissolve_to_target(
    solution: Solution,
    target_vehicles: int = 3,
    time_tolerance: float = 0.10,
    capacity_tolerance: float = 0.05
) -> Solution:
    """
    Force-dissolve smallest routes until target vehicle count reached.
    
    Algorithm:
    1. While vehicles > target:
       a. Find smallest route
       b. Dissolve it (collect orphaned customers)
       c. Re-insert using squeeze (with relaxation)
    2. Restore strict feasibility
    
    Args:
        solution: Solution to reduce
        target_vehicles: Target number of vehicles (default 3)
        time_tolerance: Time window relaxation (default 10%)
        capacity_tolerance: Capacity relaxation (default 5%)
    
    Returns:
        Reduced solution
    """
    print(f"\n  Force-Dissolve: Starting reduction to {target_vehicles} vehicles...")
    print(f"  Current: {len(solution.routes)} vehicles, cost={solution.total_base_cost:.2f}")
    
    iteration = 0
    while len(solution.routes) > target_vehicles:
        iteration += 1
        
        # Find smallest route
        smallest_route = min(solution.routes, key=lambda r: len(r.customer_ids))
        smallest_size = len(smallest_route.customer_ids)
        
        print(f"    Iteration {iteration}: Dissolving route with {smallest_size} customers...")
        
        # Collect orphaned customers
        orphaned_ids = smallest_route.customer_ids.copy()
        
        # Remove route
        solution.routes.remove(smallest_route)
        
        # Re-insert orphaned customers with squeeze
        failed_insertions = []
        for cid in orphaned_ids:
            if not squeeze_insert(solution, cid, time_tolerance, capacity_tolerance):
                failed_insertions.append(cid)
        
        # Handle failed insertions
        if failed_insertions:
            print(f"      WARNING: {len(failed_insertions)} customers couldn't be squeezed in")
            
            # Create emergency route if we're not at target yet
            if len(solution.routes) < target_vehicles:
                depot = solution.routes[0].depot if solution.routes else None
                capacity = solution.routes[0].vehicle_capacity if solution.routes else 0
                customers_lookup = solution.routes[0].customers_lookup if solution.routes else {}
                
                emergency_route = Route(depot, capacity, customers_lookup)
                for cid in failed_insertions:
                    emergency_route.customer_ids.append(cid)
                    emergency_route.current_load += customers_lookup[cid].demand
                
                emergency_route._recalculate_from(0)
                emergency_route.calculate_cost_inplace()
                solution.routes.append(emergency_route)
            else:
                # Force into existing routes (may cause severe violations)
                for cid in failed_insertions:
                    # Just append to first route
                    route = solution.routes[0]
                    route.customer_ids.append(cid)
                    route.current_load += route.customers_lookup[cid].demand
                    route._recalculate_from(len(route.customer_ids) - 2)
                    route.calculate_cost_inplace()
        
        solution.update_cost()
        print(f"      Now: {len(solution.routes)} vehicles, cost={solution.total_base_cost:.2f}")
        
        # Safety check
        if iteration > 20:
            print(f"      WARNING: Force-dissolve exceeded 20 iterations, stopping")
            break
    
    print(f"  Force-Dissolve: Reached {len(solution.routes)} vehicles")
    
    # CRITICAL: Recalculate all route costs explicitly
    print(f"  Force-Dissolve: Recalculating all route costs...")
    for route in solution.routes:
        route._recalculate_from(0)
        cost = route.calculate_cost_inplace()
        if cost == float('inf'):
            print(f"    WARNING: Route has inf cost after force-dissolve")
    
    solution.update_cost()
    print(f"  Force-Dissolve: After recalculation: cost={solution.total_base_cost:.2f}")
    
    # Restore strict feasibility
    print(f"  Force-Dissolve: Restoring strict feasibility...")
    restore_strict_feasibility(solution)
    
    solution.update_cost()
    print(f"  Force-Dissolve: After feasibility restoration: cost={solution.total_base_cost:.2f}")
    
    # POST-FEASIBILITY POLISH: 30 iterations to minimize distance
    print(f"  Force-Dissolve: Running 30-iteration polish to minimize distance...")
    from operators.inter_route_relocate import inter_route_relocate_inplace
    
    for polish_iter in range(30):
        improved = False
        
        # Intra-route 2-opt
        for route in solution.routes:
            if intra_route_2opt_inplace(route):
                improved = True
        
        # Inter-route relocate
        if len(solution.routes) > 1:
            temp_buffer = [0.0] * 200
            if inter_route_relocate_inplace(solution, temp_buffer):
                improved = True
        
        # Relocate within routes
        for route in solution.routes:
            for i in range(len(route.customer_ids)):
                customer_id = route.customer_ids[i]
                best_pos = i
                best_cost = route.total_cost
                
                old_ids = route.customer_ids.copy()
                
                for new_pos in range(len(route.customer_ids)):
                    if new_pos == i:
                        continue
                    
                    route.customer_ids.pop(i)
                    route.customer_ids.insert(new_pos, customer_id)
                    route._recalculate_from(0)
                    cost = route.calculate_cost_inplace()
                    
                    if cost < best_cost and cost != float('inf'):
                        best_cost = cost
                        best_pos = new_pos
                    
                    route.customer_ids = old_ids.copy()
                    route._recalculate_from(0)
                
                if best_pos != i:
                    route.customer_ids.pop(i)
                    route.customer_ids.insert(best_pos, customer_id)
                    route._recalculate_from(0)
                    route.calculate_cost_inplace()
                    improved = True
        
        if polish_iter % 10 == 0:
            solution.update_cost()
            print(f"    Polish iteration {polish_iter}: cost={solution.total_base_cost:.2f}")
        
        if not improved:
            break
    
    solution.update_cost()
    print(f"  Force-Dissolve: Complete! {len(solution.routes)} vehicles, cost={solution.total_base_cost:.2f}")
    
    return solution


def restore_strict_feasibility(
    solution: Solution,
    max_iterations: int = 20
) -> None:
    """
    Restore strict feasibility after constraint violations.
    
    Uses:
    1. Intra-route 2-opt to reduce travel time
    2. Customer relocation within routes
    3. Inter-route relocate to fix violations
    
    Args:
        solution: Solution to restore
        max_iterations: Maximum restoration iterations
    """
    for iteration in range(max_iterations):
        violations_fixed = False
        
        # Intra-route optimization
        for route in solution.routes:
            # Run 2-opt
            for _ in range(3):
                if intra_route_2opt_inplace(route):
                    violations_fixed = True
            
            # Try relocating each customer to best position within route
            for i in range(len(route.customer_ids)):
                customer_id = route.customer_ids[i]
                best_pos = i
                best_cost = route.total_cost
                
                # Save state
                old_ids = route.customer_ids.copy()
                
                # Try all positions
                for new_pos in range(len(route.customer_ids)):
                    if new_pos == i:
                        continue
                    
                    # Move customer
                    route.customer_ids.pop(i)
                    route.customer_ids.insert(new_pos, customer_id)
                    route._recalculate_from(0)
                    route.calculate_cost_inplace()
                    
                    if route.is_feasible() and route.total_cost < best_cost:
                        best_cost = route.total_cost
                        best_pos = new_pos
                    
                    # Restore
                    route.customer_ids = old_ids.copy()
                    route._recalculate_from(0)
                
                # Apply best move
                if best_pos != i:
                    route.customer_ids.pop(i)
                    route.customer_ids.insert(best_pos, customer_id)
                    route._recalculate_from(0)
                    route.calculate_cost_inplace()
                    violations_fixed = True
        
        # Inter-route relocate (if violations still exist)
        for route_idx, route in enumerate(solution.routes):
            if not route.is_feasible():
                # Try moving customers to other routes
                for i in range(len(route.customer_ids) - 1, -1, -1):
                    customer_id = route.customer_ids[i]
                    customer = route.customers_lookup[customer_id]
                    
                    # Try other routes
                    for other_route in solution.routes:
                        if other_route == route:
                            continue
                        
                        # Try all positions
                        for pos in range(len(other_route.customer_ids) + 1):
                            # Save states
                            old_route_ids = route.customer_ids.copy()
                            old_other_ids = other_route.customer_ids.copy()
                            
                            # Remove from current route
                            route.customer_ids.pop(i)
                            route.current_load -= customer.demand
                            route._recalculate_from(max(0, i - 1))
                            
                            # Insert into other route
                            other_route.customer_ids.insert(pos, customer_id)
                            other_route.current_load += customer.demand
                            other_route._recalculate_from(max(0, pos - 1))
                            
                            # Check if both feasible
                            if route.is_feasible() and other_route.is_feasible():
                                violations_fixed = True
                                break
                            else:
                                # Rollback
                                route.customer_ids = old_route_ids
                                other_route.customer_ids = old_other_ids
                                route._recalculate_from(0)
                                other_route._recalculate_from(0)
                        
                        if violations_fixed:
                            break
                    
                    if violations_fixed:
                        break
        
        # Check if all feasible
        all_feasible = all(r.is_feasible() for r in solution.routes)
        
        if all_feasible:
            print(f"    Feasibility restored after {iteration + 1} iterations")
            break
        
        if not violations_fixed:
            print(f"    WARNING: Could not fix all violations after {iteration + 1} iterations")
            break
    
    # Final check
    infeasible_routes = [i for i, r in enumerate(solution.routes) if not r.is_feasible()]
    if infeasible_routes:
        print(f"    WARNING: Routes {infeasible_routes} remain infeasible")
