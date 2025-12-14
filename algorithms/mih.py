"""
Limited Candidate Multiple Insertion Heuristic (MIH)
Memory-efficient implementation with candidate sampling
"""

import random
from typing import List, Dict, Optional
from core.data_structures import Customer, Route, Solution, distance


def limited_candidate_mih(
    depot: Customer,
    customers: List[Customer],
    vehicle_capacity: int,
    candidate_ratio: float = 0.3,
    min_candidates: int = 3,
    random_seed: Optional[int] = None
) -> Solution:
    """
    Limited Candidate MIH - intentionally sub-optimal to leave improvement opportunities
    
    Key innovation: Sample only 30-50% of candidates at each insertion step
    instead of evaluating all possibilities
    
    Memory efficient:
    - Works with customer indices, not object copies
    - Calculates distances on-the-fly
    - No distance matrix caching
    - Reuses route evaluation buffers
    
    Args:
        depot: Depot customer
        customers: List of customer objects
        vehicle_capacity: Vehicle capacity constraint
        candidate_ratio: Fraction of candidates to sample (0.3 = 30%)
        min_candidates: Minimum number of candidates to always check
        random_seed: Random seed for reproducibility
    
    Returns:
        Solution object with routes
    """
    if random_seed is not None:
        random.seed(random_seed)
    
    # Create customers lookup dictionary (reference, not copies)
    customers_lookup: Dict[int, Customer] = {c.id: c for c in customers}
    
    # Track unrouted customers by ID only (not objects)
    unrouted_ids: List[int] = [c.id for c in customers]
    
    solution = Solution()
    
    while unrouted_ids:
        # Create new route (single route object, reused)
        route = Route(depot, vehicle_capacity, customers_lookup)
        
        # Try to insert customers into this route
        improved = True
        while improved and unrouted_ids:
            improved = False
            
            # KEY: Only check subset of candidates
            num_candidates = max(min_candidates, int(len(unrouted_ids) * candidate_ratio))
            candidate_indices = random.sample(range(len(unrouted_ids)), min(num_candidates, len(unrouted_ids)))
            
            best_customer_idx = None
            best_position = None
            best_cost = float('inf')
            
            # Calculate on-the-fly, don't store
            for idx in candidate_indices:
                customer_id = unrouted_ids[idx]
                customer = customers_lookup[customer_id]
                
                # Try all valid positions in current route
                for position in range(len(route.customer_ids) + 1):
                    # Calculate insertion cost immediately, don't store
                    cost = calculate_insertion_cost_inline(route, customer, position)
                    
                    if cost < best_cost:
                        best_cost = cost
                        best_customer_idx = idx
                        best_position = position
            
            # Insert best candidate if found
            if best_customer_idx is not None:
                customer_id = unrouted_ids[best_customer_idx]
                
                # Try insertion (checks feasibility)
                if route.insert_inplace(customer_id, best_position):
                    unrouted_ids.pop(best_customer_idx)
                    improved = True
                else:
                    # If insertion failed, remove from candidates for this route
                    # (will be tried in next route)
                    break
        
        # Add route to solution
        if len(route.customer_ids) > 0:
            solution.add_route(route)
    
    solution.update_cost()
    return solution


def calculate_insertion_cost_inline(route: Route, customer: Customer, position: int) -> float:
    """
    Calculate cost of inserting customer at position in route
    Calculated on-the-fly, no caching
    
    Cost = additional travel distance + waiting time penalty
    
    Returns float('inf') if insertion would violate constraints
    """
    # Check capacity constraint first (cheap check)
    if route.current_load + customer.demand > route.vehicle_capacity:
        return float('inf')
    
    # Calculate additional travel distance
    additional_distance = 0.0
    
    if len(route.customer_ids) == 0:
        # Empty route: depot -> customer -> depot
        additional_distance = distance(route.depot, customer) + distance(customer, route.depot)
    elif position == 0:
        # Insert at beginning: depot -> customer -> first_customer
        first_customer = route.get_customer(0)
        old_distance = distance(route.depot, first_customer)
        new_distance = distance(route.depot, customer) + distance(customer, first_customer)
        additional_distance = new_distance - old_distance
    elif position == len(route.customer_ids):
        # Insert at end: last_customer -> customer -> depot
        last_customer = route.get_customer(len(route.customer_ids) - 1)
        old_distance = distance(last_customer, route.depot)
        new_distance = distance(last_customer, customer) + distance(customer, route.depot)
        additional_distance = new_distance - old_distance
    else:
        # Insert in middle: prev -> customer -> next
        prev_customer = route.get_customer(position - 1)
        next_customer = route.get_customer(position)
        old_distance = distance(prev_customer, next_customer)
        new_distance = distance(prev_customer, customer) + distance(customer, next_customer)
        additional_distance = new_distance - old_distance
    
    # Estimate waiting time penalty (simplified - actual waiting calculated during insertion)
    # Use time window tightness as proxy
    window_width = customer.due_date - customer.ready_time
    if window_width < 10:  # Tight window
        additional_distance += 5.0  # Penalty
    
    return additional_distance


def calculate_insertion_cost_with_feasibility(route: Route, customer: Customer, position: int) -> float:
    """
    More accurate insertion cost calculation that checks time window feasibility
    Still calculated on-the-fly, but more expensive
    """
    # Quick capacity check
    if route.current_load + customer.demand > route.vehicle_capacity:
        return float('inf')
    
    # Simulate insertion to check time windows
    # We'll calculate arrival time at position
    if len(route.customer_ids) == 0:
        # Empty route
        travel_time = distance(route.depot, customer)
        arrival_time = route.departure_time + travel_time
    elif position == 0:
        # Beginning of route
        travel_time = distance(route.depot, customer)
        arrival_time = route.departure_time + travel_time
    else:
        # After previous customer
        prev_customer = route.get_customer(position - 1)
        prev_arrival = route.arrival_times[position - 1]
        prev_departure = prev_arrival + prev_customer.service_time
        travel_time = distance(prev_customer, customer)
        arrival_time = prev_departure + travel_time
    
    # Check time window
    arrival_time = max(arrival_time, customer.ready_time)
    if arrival_time > customer.due_date:
        return float('inf')  # Infeasible
    
    # Calculate additional distance (same as above)
    additional_distance = 0.0
    if len(route.customer_ids) == 0:
        additional_distance = distance(route.depot, customer) + distance(customer, route.depot)
    elif position == 0:
        first_customer = route.get_customer(0)
        old_distance = distance(route.depot, first_customer)
        new_distance = distance(route.depot, customer) + distance(customer, first_customer)
        additional_distance = new_distance - old_distance
    elif position == len(route.customer_ids):
        last_customer = route.get_customer(len(route.customer_ids) - 1)
        old_distance = distance(last_customer, route.depot)
        new_distance = distance(last_customer, customer) + distance(customer, route.depot)
        additional_distance = new_distance - old_distance
    else:
        prev_customer = route.get_customer(position - 1)
        next_customer = route.get_customer(position)
        old_distance = distance(prev_customer, next_customer)
        new_distance = distance(prev_customer, customer) + distance(customer, next_customer)
        additional_distance = new_distance - old_distance
    
    # Add waiting time
    waiting_time = max(0.0, customer.ready_time - (arrival_time - travel_time))
    
    return additional_distance + waiting_time * 0.5  # Weight waiting time







