"""
Parallel Savings Heuristic for VRPTW
Faster and better quality than Regret-3 for R-type instances

Key Features:
1. Clarke-Wright Savings with time window constraints
2. Strict feasibility checking
3. Optimized for R-type data (geographically clustered)
"""

import math
from typing import List, Dict, Optional, Tuple
from core.data_structures import Customer, Route, Solution


def euclidean_distance(c1: Customer, c2: Customer) -> float:
    """Strict Euclidean distance"""
    dx = c1.x - c2.x
    dy = c1.y - c2.y
    return math.sqrt(dx * dx + dy * dy)


def calculate_savings(depot: Customer, c1: Customer, c2: Customer) -> float:
    """
    Clarke-Wright Savings: S(i,j) = d(0,i) + d(0,j) - d(i,j)
    Higher savings = better to merge routes
    """
    d0i = euclidean_distance(depot, c1)
    d0j = euclidean_distance(depot, c2)
    dij = euclidean_distance(c1, c2)
    return d0i + d0j - dij


def can_merge_routes(route1: Route, route2: Route, customers_lookup: Dict[int, Customer]) -> Tuple[bool, Optional[List[int]]]:
    """
    Check if two routes can be merged (route1's end to route2's start)
    Returns (feasible, merged_customer_ids)
    """
    if not route1.customer_ids or not route2.customer_ids:
        return False, None
    
    # Capacity check
    total_load = route1.current_load + route2.current_load
    if total_load > route1.vehicle_capacity:
        return False, None
    
    # Time window feasibility check
    merged_ids = route1.customer_ids + route2.customer_ids
    
    time = route1.departure_time
    prev = route1.depot
    
    for cid in merged_ids:
        customer = customers_lookup[cid]
        travel = euclidean_distance(prev, customer)
        arrival = time + travel
        
        if arrival < customer.ready_time:
            arrival = customer.ready_time
        
        if arrival > customer.due_date:
            return False, None
        
        time = arrival + customer.service_time
        prev = customer
    
    return True, merged_ids


def parallel_savings_construction(
    depot: Customer,
    customers: List[Customer],
    vehicle_capacity: int,
    random_seed: Optional[int] = None
) -> Solution:
    """
    Parallel Clarke-Wright Savings Heuristic
    
    Algorithm:
    1. Create initial routes: one customer per route
    2. Calculate savings for all customer pairs
    3. Sort savings in descending order
    4. Merge routes greedily based on savings
    
    Fast and effective for R-type data
    """
    customers_lookup: Dict[int, Customer] = {c.id: c for c in customers}
    solution = Solution()
    
    print(f"  Parallel Savings: Starting construction for {len(customers)} customers...")
    
    # Step 1: Create initial routes (one customer each)
    routes = []
    for customer in customers:
        route = Route(depot, vehicle_capacity, customers_lookup)
        route.insert_inplace(customer.id, 0)
        routes.append(route)
    
    # Step 2: Calculate all savings
    savings = []
    for i in range(len(customers)):
        for j in range(i + 1, len(customers)):
            c1 = customers[i]
            c2 = customers[j]
            s = calculate_savings(depot, c1, c2)
            savings.append((s, i, j))
    
    # Sort by savings (descending)
    savings.sort(reverse=True)
    
    print(f"  Parallel Savings: Calculated {len(savings)} savings values...")
    
    # Step 3: Merge routes based on savings
    merges = 0
    for saving_value, i, j in savings:
        if saving_value <= 0:
            break
        
        # Find routes containing customers i and j
        route_i = None
        route_j = None
        
        for route in routes:
            if customers[i].id in route.customer_ids:
                route_i = route
            if customers[j].id in route.customer_ids:
                route_j = route
        
        if route_i is None or route_j is None:
            continue
        
        if route_i is route_j:
            continue
        
        # Check if customers are at route ends
        i_at_start = (route_i.customer_ids[0] == customers[i].id)
        i_at_end = (route_i.customer_ids[-1] == customers[i].id)
        j_at_start = (route_j.customer_ids[0] == customers[j].id)
        j_at_end = (route_j.customer_ids[-1] == customers[j].id)
        
        merged = False
        merged_ids = None
        
        # Try all valid merge configurations
        if i_at_end and j_at_start:
            # route_i + route_j
            feasible, merged_ids = can_merge_routes(route_i, route_j, customers_lookup)
            if feasible:
                merged = True
        elif j_at_end and i_at_start:
            # route_j + route_i
            feasible, merged_ids = can_merge_routes(route_j, route_i, customers_lookup)
            if feasible:
                merged = True
                route_i, route_j = route_j, route_i
        
        if merged and merged_ids:
            # Execute merge
            route_i.customer_ids = merged_ids
            route_i.current_load = route_i.current_load + route_j.current_load
            route_i._recalculate_from(0)
            route_i.calculate_cost_inplace()
            
            # Remove route_j
            routes.remove(route_j)
            merges += 1
    
    print(f"  Parallel Savings: Performed {merges} merges, final routes: {len(routes)}")
    
    # Build solution
    for route in routes:
        if route.customer_ids:
            solution.add_route(route)
    
    solution.update_cost()
    
    # Validation
    route_sizes = [len(r.customer_ids) for r in solution.routes]
    print(f"  Parallel Savings: Route sizes: min={min(route_sizes)}, max={max(route_sizes)}, avg={sum(route_sizes)/len(route_sizes):.1f}")
    print(f"  Parallel Savings: Cost={solution.total_base_cost:.2f}, Vehicles={len(solution.routes)}")
    
    return solution


def limited_candidate_mih(
    depot: Customer,
    customers: List[Customer],
    vehicle_capacity: int,
    candidate_ratio: float = 0.7,
    min_candidates: int = 5,
    random_seed: Optional[int] = None
) -> Solution:
    """
    Wrapper for compatibility - calls Parallel Savings construction
    """
    return parallel_savings_construction(depot, customers, vehicle_capacity, random_seed)


def enhanced_mih_construction(
    depot: Customer,
    customers: List[Customer],
    vehicle_capacity: int,
    random_seed: Optional[int] = None
) -> Solution:
    """
    Alias for compatibility - calls Parallel Savings construction
    """
    return parallel_savings_construction(depot, customers, vehicle_capacity, random_seed)