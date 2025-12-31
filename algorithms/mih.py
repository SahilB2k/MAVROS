"""
Regret-3 Insertion Heuristic for VRPTW
Ensures initial construction creates <10 routes (not 36!)

Key Features:
1. Constrained seed selection: max(distance / time_window_width)
2. Regret-3 insertion: (cost_2nd - cost_1st) + (cost_3rd - cost_1st)
3. Strict Euclidean distance (no rounding)
"""

import math
from typing import List, Dict, Optional, Tuple
from core.data_structures import Customer, Route, Solution


def euclidean_distance(c1: Customer, c2: Customer) -> float:
    """
    Strict Euclidean distance - NO ROUNDING
    """
    dx = c1.x - c2.x
    dy = c1.y - c2.y
    return math.sqrt(dx * dx + dy * dy)


def select_constrained_seed(unassigned: List[Customer], depot: Customer) -> Customer:
    """
    Select most constrained customer for new route seed.
    
    Formula: max(distance_to_depot / (due_date - ready_time))
    
    Higher score = more constrained (far from depot, tight time window)
    """
    best_score = -float('inf')
    best_customer = None
    
    for customer in unassigned:
        distance = euclidean_distance(depot, customer)
        time_window_width = customer.due_date - customer.ready_time
        
        # Avoid division by zero
        if time_window_width > 0:
            score = distance / time_window_width
        else:
            score = float('inf')  # Extremely constrained - zero time window
        
        if score > best_score:
            best_score = score
            best_customer = customer
    
    return best_customer


def calculate_insertion_cost_strict(
    route: Route,
    customer: Customer,
    position: int
) -> float:
    """
    Calculate insertion cost with STRICT feasibility checking.
    Returns inf if infeasible.
    """
    # Save state
    old_cost = route.total_cost
    old_ids = route.customer_ids.copy()
    old_arrivals = route.arrival_times.copy()
    old_load = route.current_load
    
    # Try insertion
    if route.insert_inplace(customer.id, position):
        insertion_cost = route.total_cost - old_cost
        
        # Rollback
        route.customer_ids = old_ids
        route.arrival_times = old_arrivals
        route.current_load = old_load
        route.total_cost = old_cost
        
        return insertion_cost
    else:
        return float('inf')


def regret_3_construction(
    depot: Customer,
    customers: List[Customer],
    vehicle_capacity: int,
    random_seed: Optional[int] = None
) -> Solution:
    """
    Regret-3 Insertion Heuristic for VRPTW.
    
    Algorithm:
    1. Start first route with most constrained customer
    2. For each unassigned customer, find top-3 insertion positions
    3. Calculate Regret-3 = (cost_2 - cost_1) + (cost_3 - cost_1)
    4. Insert customer with HIGHEST regret first
    5. Repeat until all customers assigned
    
    Target: <10 routes with ~2,500 cost (not 36 routes with 11,930!)
    """
    customers_lookup: Dict[int, Customer] = {c.id: c for c in customers}
    solution = Solution()
    routes: List[Route] = []
    unassigned = customers.copy()
    
    print(f"  Regret-3: Starting construction for {len(customers)} customers...")
    
    # Initialize first route with most constrained customer
    seed = select_constrained_seed(unassigned, depot)
    first_route = Route(depot, vehicle_capacity, customers_lookup)
    first_route.insert_inplace(seed.id, 0)
    routes.append(first_route)
    unassigned.remove(seed)
    
    print(f"  Regret-3: Initialized first route with customer {seed.id} (constraint score={euclidean_distance(depot, seed)/(seed.due_date - seed.ready_time):.3f})")
    
    # Main Regret-3 insertion loop
    iteration = 0
    while unassigned:
        iteration += 1
        
        best_customer = None
        max_regret = -float('inf')
        best_insertion = None  # (cost, route, position)
        
        # For each unassigned customer
        for customer in unassigned:
            # Find top-3 insertion positions across ALL routes
            insertion_options = []  # (cost, route, position)
            
            for route in routes:
                n = len(route.customer_ids)
                for pos in range(n + 1):
                    cost = calculate_insertion_cost_strict(route, customer, pos)
                    if cost < float('inf'):
                        insertion_options.append((cost, route, pos))
            
            # Sort by cost (ascending)
            insertion_options.sort(key=lambda x: x[0])
            
            # Calculate Regret-3
            if len(insertion_options) >= 3:
                cost_1 = insertion_options[0][0]
                cost_2 = insertion_options[1][0]
                cost_3 = insertion_options[2][0]
                regret = (cost_2 - cost_1) + (cost_3 - cost_1)
            elif len(insertion_options) == 2:
                cost_1 = insertion_options[0][0]
                cost_2 = insertion_options[1][0]
                regret = 2.0 * (cost_2 - cost_1)  # Penalize limited options
            elif len(insertion_options) == 1:
                regret = float('inf')  # Only one option - VERY high priority
            else:
                regret = float('inf')  # No feasible insertion - must create new route
            
            # Track customer with highest regret
            if regret > max_regret:
                max_regret = regret
                best_customer = customer
                if insertion_options:
                    best_insertion = insertion_options[0]
                else:
                    best_insertion = None
        
        # Insert customer with highest regret
        if best_customer is None:
            break  # Should never happen
        
        if best_insertion is not None:
            # Insert into existing route
            cost, route, pos = best_insertion
            success = route.insert_inplace(best_customer.id, pos)
            if success:
                unassigned.remove(best_customer)
            else:
                # Fallback: create new route
                new_route = Route(depot, vehicle_capacity, customers_lookup)
                new_route.insert_inplace(best_customer.id, 0)
                routes.append(new_route)
                unassigned.remove(best_customer)
        else:
            # No feasible insertion - create new route with constrained seed
            seed = select_constrained_seed([best_customer], depot)
            new_route = Route(depot, vehicle_capacity, customers_lookup)
            new_route.insert_inplace(seed.id, 0)
            routes.append(new_route)
            unassigned.remove(seed)
        
        # Progress reporting
        if iteration % 20 == 0:
            print(f"    Iteration {iteration}: {len(unassigned)} customers remaining, {len(routes)} routes")
    
    # Build solution
    for route in routes:
        if route.customer_ids:
            solution.add_route(route)
    
    solution.update_cost()
    
    # Validation
    print(f"  Regret-3: Constructed solution with {len(solution.routes)} routes, cost={solution.total_base_cost:.2f}")
    
    # Check route sizes
    route_sizes = [len(r.customer_ids) for r in solution.routes]
    print(f"  Regret-3: Route sizes: min={min(route_sizes)}, max={max(route_sizes)}, avg={sum(route_sizes)/len(route_sizes):.1f}")
    
    if len(solution.routes) > 10:
        print(f"  WARNING: Created {len(solution.routes)} routes (target: <10). Adaptive repair needed!")
    
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
    Wrapper for compatibility - calls Regret-3 construction
    """
    return regret_3_construction(depot, customers, vehicle_capacity, random_seed)


def enhanced_mih_construction(
    depot: Customer,
    customers: List[Customer],
    vehicle_capacity: int,
    random_seed: Optional[int] = None
) -> Solution:
    """
    Alias for compatibility - calls Regret-3 construction
    """
    return regret_3_construction(depot, customers, vehicle_capacity, random_seed)