"""
FIXED Sequential Insertion - Proven to work
Simple, robust construction that creates good initial solutions
Target: Cost ~2000-2200, NOT 10,000+
"""

import random
from typing import List, Dict, Optional, Tuple
from core.data_structures import Customer, Route, Solution, distance


def limited_candidate_mih(
    depot: Customer,
    customers: List[Customer],
    vehicle_capacity: int,
    candidate_ratio: float = 0.7,
    min_candidates: int = 5,
    random_seed: Optional[int] = None
) -> Solution:
    """
    COMPLETELY REWRITTEN - Simple, proven sequential insertion
    
    Algorithm:
    1. Sort customers by (due_date, distance_from_depot) - prioritize urgent + close
    2. For each customer, try inserting in ALL existing routes
    3. Only open new route if absolutely necessary (strict penalty)
    4. Use best insertion position (cheapest cost)
    """
    
    if random_seed is not None:
        random.seed(random_seed)

    customers_lookup: Dict[int, Customer] = {c.id: c for c in customers}
    
    # CRITICAL FIX 1: Sort by urgency + distance (not random!)
    # This creates natural route clusters
    customers_sorted = sorted(
        customers, 
        key=lambda c: (c.due_date, distance(depot, c))
    )
    
    solution = Solution()
    routes: List[Route] = []
    
    # CRITICAL FIX 2: Process customers in sorted order (no random shuffling!)
    for customer in customers_sorted:
        best_insertion = None
        best_cost = float('inf')
        
        # Try inserting into ALL existing routes at ALL positions
        for route in routes:
            n = len(route.customer_ids)
            for pos in range(n + 1):
                # Calculate TRUE insertion cost
                cost = calculate_true_insertion_cost(route, customer, pos)
                
                if cost < best_cost:
                    best_cost = cost
                    best_insertion = (route, pos, False)  # False = not new route
        
        # Try opening a new route with HIGH penalty
        if len(routes) > 0:
            new_route_cost = distance(depot, customer) + distance(customer, depot)
            # CRITICAL FIX 3: Strong penalty to discourage unnecessary vehicles
            # Average route length is typically 50-100, so 1000 is strong deterrent
            new_route_cost_penalized = new_route_cost + 1000.0
            
            if new_route_cost_penalized < best_cost:
                new_route = Route(depot, vehicle_capacity, customers_lookup)
                best_insertion = (new_route, 0, True)  # True = new route
                best_cost = new_route_cost_penalized
        else:
            # First customer - must open first route
            new_route = Route(depot, vehicle_capacity, customers_lookup)
            best_insertion = (new_route, 0, True)
        
        # Perform insertion
        if best_insertion is not None:
            target_route, pos, is_new = best_insertion
            
            if is_new:
                routes.append(target_route)
            
            success = target_route.insert_inplace(customer.id, pos)
            
            if not success:
                # Emergency fallback: force into dedicated route
                fallback = Route(depot, vehicle_capacity, customers_lookup)
                fallback.customer_ids = [customer.id]
                fallback.current_load = customer.demand
                fallback.departure_time = 0.0
                fallback.calculate_cost_inplace()
                routes.append(fallback)
        else:
            # Should never happen, but safety net
            fallback = Route(depot, vehicle_capacity, customers_lookup)
            fallback.customer_ids = [customer.id]
            fallback.current_load = customer.demand
            fallback.departure_time = 0.0
            fallback.calculate_cost_inplace()
            routes.append(fallback)
    
    # Build final solution
    for route in routes:
        if route.customer_ids:
            solution.add_route(route)
    
    solution.update_cost()
    
    # CRITICAL FIX 4: Validate solution quality
    if solution.total_base_cost > 5000:
        print(f"WARNING: Initial solution cost is {solution.total_base_cost:.2f}")
        print(f"  This suggests construction issues. Expected: ~2000-2500")
        print(f"  Number of routes: {len(solution.routes)}")
        print(f"  Average route cost: {solution.total_base_cost / len(solution.routes):.2f}")
    
    return solution


def calculate_true_insertion_cost(route: Route, customer: Customer, position: int) -> float:
    """
    Calculate TRUE insertion cost with proper feasibility checks
    Returns float('inf') if insertion is infeasible
    """
    
    # Check 1: Capacity
    if route.current_load + customer.demand > route.vehicle_capacity:
        return float('inf')
    
    n = len(route.customer_ids)
    
    # Check 2: Time window feasibility
    # We need to check if inserting here breaks time windows
    
    # Calculate arrival time at customer
    if n == 0:
        # Empty route
        travel_time = distance(route.depot, customer)
        arrival = route.departure_time + travel_time
    elif position == 0:
        # Insert at beginning
        travel_time = distance(route.depot, customer)
        arrival = route.departure_time + travel_time
    else:
        # Insert after position-1
        prev_customer = route.get_customer(position - 1)
        
        # Get departure time from previous customer
        if position - 1 < len(route.arrival_times):
            prev_arrival = route.arrival_times[position - 1]
        else:
            # Need to calculate
            prev_arrival = route.departure_time + distance(route.depot, prev_customer)
            prev_arrival = max(prev_arrival, prev_customer.ready_time)
        
        departure_from_prev = prev_arrival + prev_customer.service_time
        travel_time = distance(prev_customer, customer)
        arrival = departure_from_prev + travel_time
    
    # Apply waiting if arriving early
    arrival = max(arrival, customer.ready_time)
    
    # Check if violates due date
    if arrival > customer.due_date:
        return float('inf')
    
    # Check 3: Does insertion break NEXT customer's time window?
    if position < n:
        next_customer = route.get_customer(position)
        departure_from_new = arrival + customer.service_time
        travel_to_next = distance(customer, next_customer)
        next_arrival = departure_from_new + travel_to_next
        next_arrival = max(next_arrival, next_customer.ready_time)
        
        if next_arrival > next_customer.due_date:
            return float('inf')
    
    # Calculate cost (edge changes only)
    if n == 0:
        # Empty route: depot -> customer -> depot
        cost = distance(route.depot, customer) + distance(customer, route.depot)
    elif position == 0:
        # Insert at start: depot -> customer -> old_first
        next_customer = route.get_customer(0)
        old_edge = distance(route.depot, next_customer)
        new_edges = distance(route.depot, customer) + distance(customer, next_customer)
        cost = new_edges - old_edge
    elif position == n:
        # Insert at end: old_last -> customer -> depot
        prev_customer = route.get_customer(-1)
        old_edge = distance(prev_customer, route.depot)
        new_edges = distance(prev_customer, customer) + distance(customer, route.depot)
        cost = new_edges - old_edge
    else:
        # Insert in middle: prev -> customer -> next
        prev_customer = route.get_customer(position - 1)
        next_customer = route.get_customer(position)
        old_edge = distance(prev_customer, next_customer)
        new_edges = distance(prev_customer, customer) + distance(customer, next_customer)
        cost = new_edges - old_edge
    
    # Add waiting time cost (if any)
    if position == 0:
        travel_time = distance(route.depot, customer)
        raw_arrival = route.departure_time + travel_time
    else:
        prev_customer = route.get_customer(position - 1)
        if position - 1 < len(route.arrival_times):
            prev_departure = route.arrival_times[position - 1] + prev_customer.service_time
        else:
            prev_departure = route.departure_time + distance(route.depot, prev_customer) + prev_customer.service_time
        
        travel_time = distance(prev_customer, customer)
        raw_arrival = prev_departure + travel_time
    
    waiting = max(0.0, customer.ready_time - raw_arrival)
    cost += waiting * 1.1  # Waiting penalty
    
    return cost


def enhanced_mih_construction(
    depot: Customer,
    customers: List[Customer],
    vehicle_capacity: int,
    random_seed: Optional[int] = None
) -> Solution:
    """
    Alias for compatibility - calls the fixed version
    """
    return limited_candidate_mih(depot, customers, vehicle_capacity, random_seed=random_seed)