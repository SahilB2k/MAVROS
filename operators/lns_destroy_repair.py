"""
Fast LNS Destroy-Repair with Smart Insertion
Optimized for speed and quality
"""

import random
from typing import List
from core.data_structures import Solution, Route, Customer, distance


def _calculate_insertion_cost(route: Route, customer_id: int, position: int) -> float:
    """
    Fast insertion cost calculation
    Returns float('inf') if insertion is infeasible.
    """
    customer = route.customers_lookup[customer_id]
    
    if route.current_load + customer.demand > route.vehicle_capacity:
        return float('inf')
    
    old_cost = route.total_cost
    
    if not route.insert_inplace(customer_id, position):
        return float('inf')
    
    new_cost = route.total_cost
    
    # Rollback
    route.customer_ids.pop(position)
    route.arrival_times.pop(position)
    route.current_load -= customer.demand
    route._recalculate_from(position)
    route.calculate_cost_inplace()
    
    return new_cost - old_cost


def _related_removal(solution: Solution, 
                    removal_fraction: float = 0.25,
                    fixed_remove_count: int = None,
                    random_seed: int = 42) -> List[int]:
    """
    Fast related removal using distance clustering
    """
    random.seed(random_seed)
    routes = solution.routes
    
    all_customers = []
    for route in routes:
        for cid in route.customer_ids:
            all_customers.append(cid)
    
    if len(all_customers) == 0:
        return []
    
    if fixed_remove_count is not None:
        remove_count = min(fixed_remove_count, len(all_customers))
    else:
        remove_count = max(5, int(len(all_customers) * removal_fraction))
        remove_count = min(remove_count, len(all_customers))
    
    if remove_count == 0:
        return []
    
    # Random seed customer
    seed_customer_id = random.choice(all_customers)
    seed_customer = routes[0].customers_lookup[seed_customer_id]
    
    to_remove = [seed_customer_id]
    remaining = [cid for cid in all_customers if cid != seed_customer_id]
    
    # Expand cluster greedily
    while len(to_remove) < remove_count and remaining:
        min_dist = float('inf')
        nearest_id = None
        
        for removed_id in to_remove:
            removed_customer = routes[0].customers_lookup[removed_id]
            for candidate_id in remaining:
                candidate = routes[0].customers_lookup[candidate_id]
                dist = distance(removed_customer, candidate)
                if dist < min_dist:
                    min_dist = dist
                    nearest_id = candidate_id
        
        if nearest_id is None:
            break
        
        to_remove.append(nearest_id)
        remaining.remove(nearest_id)
    
    return to_remove


def lns_destroy_repair(solution: Solution,
                      removal_fraction: float = 0.15,
                      fixed_remove_count: int = None,
                      random_seed: int = 42) -> bool:
    """
    Fast LNS with regret-2 repair
    """
    if not solution.routes:
        return False

    solution.update_cost()
    current_obj = solution.total_cost

    to_remove = _related_removal(solution, removal_fraction, fixed_remove_count, random_seed)
    
    if len(to_remove) == 0:
        return False

    routes = solution.routes
    
    # Destroy phase
    for cid in to_remove:
        for r in routes:
            if cid in r.customer_ids:
                pos = r.customer_ids.index(cid)
                r.customer_ids.pop(pos)
                r.arrival_times.pop(pos)
                r.current_load -= r.customers_lookup[cid].demand
                r._recalculate_from(max(0, pos - 1))
                r.calculate_cost_inplace()
                break

    solution.routes = [r for r in routes if len(r.customer_ids) > 0]

    if not solution.routes:
        return False
    
    depot = solution.routes[0].depot
    capacity = solution.routes[0].vehicle_capacity
    customers_lookup = solution.routes[0].customers_lookup

    # Repair with regret-2 (faster than regret-3)
    sorted_to_remove = sorted(to_remove, 
                             key=lambda cid: customers_lookup[cid].due_date - customers_lookup[cid].ready_time)

    for cid in sorted_to_remove:
        best_route_idx = None
        best_pos = None
        best_cost = float('inf')
        second_best_cost = float('inf')
        
        # Find best and second-best insertions
        for r_idx, r in enumerate(solution.routes):
            for pos in range(len(r.customer_ids) + 1):
                cost = _calculate_insertion_cost(r, cid, pos)
                if cost < best_cost:
                    second_best_cost = best_cost
                    best_cost = cost
                    best_route_idx = r_idx
                    best_pos = pos
                elif cost < second_best_cost:
                    second_best_cost = cost
        
        # Use regret-2 metric if we have options
        regret = second_best_cost - best_cost if second_best_cost != float('inf') else 0
        
        if best_route_idx is not None and best_cost != float('inf'):
            route = solution.routes[best_route_idx]
            if not route.insert_inplace(cid, best_pos):
                # Create new route if insertion fails
                new_route = Route(depot, capacity, customers_lookup)
                if not new_route.insert_inplace(cid, 0):
                    new_route.customer_ids = [cid]
                    new_route.arrival_times = [0.0]
                    new_route.current_load = customers_lookup[cid].demand
                    new_route.departure_time = 0.0
                    new_route.calculate_cost_inplace()
                solution.routes.append(new_route)
        else:
            # Create new route
            new_route = Route(depot, capacity, customers_lookup)
            if not new_route.insert_inplace(cid, 0):
                new_route.customer_ids = [cid]
                new_route.arrival_times = [0.0]
                new_route.current_load = customers_lookup[cid].demand
                new_route.departure_time = 0.0
                new_route.calculate_cost_inplace()
            solution.routes.append(new_route)

    # Fast 2-opt on modified routes
    from operators.intra_route_2opt import intra_route_2opt_inplace
    for r in solution.routes:
        intra_route_2opt_inplace(r)

    # Validation
    all_ids_after = [cid for route in solution.routes for cid in route.customer_ids]
    missing = [cid for cid in to_remove if cid not in all_ids_after]
    if missing:
        raise ValueError(f"LNS repair lost customers: {missing}")

    solution.update_cost()
    return solution.total_cost < current_obj - 1e-6