"""
Adaptive Repair Phase for VRPTW
Dissolves routes with <5 customers and uses ejection chains for re-insertion

Key Features:
1. Route dissolution (routes with <5 customers)
2. Ejection chain re-insertion with 5% time window tolerance
3. Post-repair feasibility restoration (2-opt + relocate)
"""

import copy
from typing import List, Optional
from core.data_structures import Solution, Route, Customer
from operators.intra_route_2opt import intra_route_2opt_inplace


def can_insert_with_tolerance(
    route: Route,
    customer_id: int,
    position: int,
    tolerance: float = 0.05
) -> bool:
    """
    Check if customer can be inserted with 5% time window tolerance.
    
    Args:
        route: Route to insert into
        customer_id: Customer to insert
        position: Position to insert at
        tolerance: Time window violation tolerance (default 5%)
    
    Returns:
        True if insertion is feasible with tolerance
    """
    customer = route.customers_lookup[customer_id]
    
    # Save state
    old_ids = route.customer_ids.copy()
    old_arrivals = route.arrival_times.copy()
    old_load = route.current_load
    
    # Try insertion
    if route.insert_inplace(customer_id, position):
        # Check if feasible
        route.customer_ids = old_ids
        route.arrival_times = old_arrivals
        route.current_load = old_load
        return True
    
    # Restore and check with tolerance
    route.customer_ids = old_ids
    route.arrival_times = old_arrivals
    route.current_load = old_load
    
    # Manual check with tolerance
    # Calculate arrival time at customer
    if position == 0:
        prev_departure = 0.0
        prev_location = route.depot
    else:
        prev_customer = route.get_customer(position - 1)
        if position - 1 < len(route.arrival_times):
            prev_arrival = route.arrival_times[position - 1]
        else:
            prev_arrival = 0.0
        prev_service_start = max(prev_arrival, prev_customer.ready_time)
        prev_departure = prev_service_start + prev_customer.service_time
        prev_location = prev_customer
    
    from core.data_structures import distance
    travel_time = distance(prev_location, customer)
    arrival = prev_departure + travel_time
    
    # Check with tolerance
    max_allowed = customer.due_date * (1.0 + tolerance)
    
    if arrival <= max_allowed:
        # Check capacity
        if route.current_load + customer.demand <= route.vehicle_capacity:
            return True
    
    return False


def ejection_chain_insertion(
    solution: Solution,
    customer_id: int,
    tolerance: float = 0.05,
    max_chain_depth: int = 3
) -> bool:
    """
    Try to insert customer using ejection chain.
    
    Algorithm:
    1. Try direct insertion with tolerance
    2. If fails, try ejecting one customer from route
    3. Recursively insert ejected customer elsewhere
    
    Args:
        solution: Current solution
        customer_id: Customer to insert
        tolerance: Time window tolerance (5%)
        max_chain_depth: Maximum ejection chain depth
    
    Returns:
        True if insertion successful
    """
    customer = solution.routes[0].customers_lookup[customer_id]
    
    # Try direct insertion in all routes
    for route in solution.routes:
        for pos in range(len(route.customer_ids) + 1):
            if can_insert_with_tolerance(route, customer_id, pos, tolerance):
                # Force insertion (may violate constraints temporarily)
                old_ids = route.customer_ids.copy()
                route.customer_ids.insert(pos, customer_id)
                route.current_load += customer.demand
                route._recalculate_from(max(0, pos - 1))
                route.calculate_cost_inplace()
                return True
    
    # Try ejection chains (if depth allows)
    if max_chain_depth > 0:
        for route_idx, route in enumerate(solution.routes):
            for pos in range(len(route.customer_ids) + 1):
                # Try ejecting each customer in route
                for eject_idx in range(len(route.customer_ids)):
                    ejected_id = route.customer_ids[eject_idx]
                    
                    # Temporarily remove ejected customer
                    old_ids = route.customer_ids.copy()
                    old_load = route.current_load
                    ejected_customer = route.customers_lookup[ejected_id]
                    
                    route.customer_ids.pop(eject_idx)
                    route.current_load -= ejected_customer.demand
                    route._recalculate_from(max(0, eject_idx - 1))
                    
                    # Try inserting new customer
                    if can_insert_with_tolerance(route, customer_id, pos, tolerance):
                        # Success! Now recursively insert ejected customer
                        route.customer_ids.insert(pos, customer_id)
                        route.current_load += customer.demand
                        route._recalculate_from(max(0, pos - 1))
                        route.calculate_cost_inplace()
                        
                        # Try to insert ejected customer elsewhere
                        if ejection_chain_insertion(solution, ejected_id, tolerance, max_chain_depth - 1):
                            return True
                    
                    # Restore if failed
                    route.customer_ids = old_ids
                    route.current_load = old_load
                    route._recalculate_from(0)
    
    return False


def adaptive_repair_phase(
    solution: Solution,
    min_customers_per_route: int = 5,
    tolerance: float = 0.05
) -> Solution:
    """
    Adaptive Repair Phase - Dissolve small routes and re-insert customers.
    
    Algorithm:
    1. Identify routes with <5 customers
    2. Dissolve these routes (collect orphaned customers)
    3. Re-insert using ejection chains with 5% tolerance
    4. Restore feasibility with local search
    
    Args:
        solution: Solution to repair
        min_customers_per_route: Minimum customers per route (default 5)
        tolerance: Time window tolerance during repair (default 5%)
    
    Returns:
        Repaired solution
    """
    print(f"\n  Adaptive Repair: Starting repair phase...")
    
    # Identify small routes
    small_routes = []
    large_routes = []
    
    for route in solution.routes:
        if len(route.customer_ids) < min_customers_per_route:
            small_routes.append(route)
        else:
            large_routes.append(route)
    
    if not small_routes:
        print(f"  Adaptive Repair: No small routes found (all routes have >={min_customers_per_route} customers)")
        return solution
    
    print(f"  Adaptive Repair: Found {len(small_routes)} routes with <{min_customers_per_route} customers")
    
    # Collect orphaned customers
    orphaned_ids = []
    for route in small_routes:
        orphaned_ids.extend(route.customer_ids)
    
    print(f"  Adaptive Repair: Dissolving {len(small_routes)} routes, re-inserting {len(orphaned_ids)} customers")
    
    # Update solution to only keep large routes
    solution.routes = large_routes
    
    # Re-insert orphaned customers using ejection chains
    failed_insertions = []
    for cid in orphaned_ids:
        if not ejection_chain_insertion(solution, cid, tolerance, max_chain_depth=3):
            failed_insertions.append(cid)
    
    # Handle failed insertions - create emergency routes
    if failed_insertions:
        print(f"  Adaptive Repair: {len(failed_insertions)} customers couldn't be inserted, creating emergency routes")
        depot = solution.routes[0].depot if solution.routes else None
        capacity = solution.routes[0].vehicle_capacity if solution.routes else 0
        customers_lookup = solution.routes[0].customers_lookup if solution.routes else {}
        
        for cid in failed_insertions:
            new_route = Route(depot, capacity, customers_lookup)
            new_route.customer_ids = [cid]
            new_route.current_load = customers_lookup[cid].demand
            new_route.departure_time = 0.0
            new_route.calculate_cost_inplace()
            solution.routes.append(new_route)
    
    solution.update_cost()
    
    # Post-repair feasibility restoration
    print(f"  Adaptive Repair: Restoring feasibility with local search...")
    restore_feasibility(solution)
    
    # Final stats
    route_sizes = [len(r.customer_ids) for r in solution.routes]
    print(f"  Adaptive Repair: Complete! {len(solution.routes)} routes, sizes: min={min(route_sizes)}, max={max(route_sizes)}, avg={sum(route_sizes)/len(route_sizes):.1f}")
    print(f"  Adaptive Repair: Final cost: {solution.total_base_cost:.2f}")
    
    return solution


def restore_feasibility(solution: Solution, max_iterations: int = 5):
    """
    Restore strict feasibility after repair phase.
    
    Uses:
    1. Intra-route 2-opt to reduce travel time
    2. Customer relocation to better positions
    
    Args:
        solution: Solution to restore
        max_iterations: Maximum iterations per route
    """
    for route in solution.routes:
        # Run 2-opt multiple times
        for _ in range(max_iterations):
            improved = intra_route_2opt_inplace(route)
            if not improved:
                break
        
        # Try relocating each customer to best position
        for i in range(len(route.customer_ids)):
            customer_id = route.customer_ids[i]
            customer = route.customers_lookup[customer_id]
            
            # Find best position
            best_pos = i
            best_cost = route.total_cost
            
            # Save state
            old_ids = route.customer_ids.copy()
            old_cost = route.total_cost
            
            # Try all positions
            for new_pos in range(len(route.customer_ids)):
                if new_pos == i:
                    continue
                
                # Remove from current position
                route.customer_ids.pop(i)
                
                # Insert at new position
                route.customer_ids.insert(new_pos, customer_id)
                route._recalculate_from(0)
                route.calculate_cost_inplace()
                
                if route.total_cost < best_cost:
                    best_cost = route.total_cost
                    best_pos = new_pos
                
                # Restore
                route.customer_ids = old_ids.copy()
            
            # Apply best relocation
            if best_pos != i:
                route.customer_ids.pop(i)
                route.customer_ids.insert(best_pos, customer_id)
                route._recalculate_from(0)
                route.calculate_cost_inplace()
    
    solution.update_cost()
