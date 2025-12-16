"""
Lightweight destroy-and-repair (LNS-style) to escape local minima.

Strategy:
- Destroy: remove a subset of customers from the most critical routes.
- Repair: reinsert customers greedily where the penalised objective improves.

All operations are IN PLACE; uses Route.insert_inplace for feasibility.
"""

import random
from typing import List
from core.data_structures import Solution, Route, Customer
from evaluation.route_analyzer import identify_critical_route_indices


def _try_insert_customer(route: Route, customer_id: int) -> bool:
    """
    Greedy best-position insertion using existing in-place feasibility.
    Returns True if inserted.
    """
    best_pos = None
    best_cost = float('inf')

    for pos in range(len(route.customer_ids) + 1):
        # Tentative: insert, evaluate, rollback
        if route.insert_inplace(customer_id, pos):
            cost = route.total_cost
            if cost < best_cost:
                best_cost = cost
                best_pos = pos
            # rollback
            route.customer_ids.pop(pos)
            route.arrival_times.pop(pos)
            # recalc from pos to keep state clean
            route._recalculate_from(pos)
            route.calculate_cost_inplace()

    if best_pos is None:
        return False

    return route.insert_inplace(customer_id, best_pos)


def lns_destroy_repair(solution: Solution,
                      removal_fraction: float = 0.2,
                      fixed_remove_count: int = None,
                      random_seed: int = 42) -> bool:
    """
    Apply a single destroy-repair iteration.
    Returns True if the solution improved (penalised objective decreased).
    """
    if not solution.routes:
        return False

    random.seed(random_seed)
    solution.update_cost()
    current_obj = solution.total_cost

    # Select routes to destroy from (critical routes)
    crit_indices = identify_critical_route_indices(
        solution, top_n=min(5, len(solution.routes))
    )
    routes = solution.routes

    # Collect customers to remove
    to_remove: List[int] = []
    for idx in crit_indices:
        r = routes[idx]
        to_remove.extend(r.customer_ids)

    total_customers = len(to_remove)
    if total_customers == 0:
        return False

    if fixed_remove_count is not None:
        remove_count = min(fixed_remove_count, total_customers)
    else:
        remove_count = max(5, int(total_customers * removal_fraction))
    to_remove = random.sample(to_remove, min(remove_count, total_customers))

    # Destroy: remove selected customers from their routes
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

    # Remove empty routes
    solution.routes = [r for r in routes if len(r.customer_ids) > 0]

    touched_routes = set()

    # Repair: reinsert each removed customer
    # Use existing depot/capacity from first route
    if not solution.routes:
        return False
    depot = solution.routes[0].depot
    capacity = solution.routes[0].vehicle_capacity
    customers_lookup = solution.routes[0].customers_lookup

    for cid in to_remove:
        customer = customers_lookup[cid]
        inserted = False
        # try existing routes first
        for r in solution.routes:
            if _try_insert_customer(r, cid):
                touched_routes.add(id(r))
                inserted = True
                break
        if not inserted:
            # create new route if needed
            new_route = Route(depot, capacity, customers_lookup)
            if new_route.insert_inplace(cid, 0):
                solution.routes.append(new_route)
                touched_routes.add(id(new_route))
            else:
                # could not insert anywhere; abandon and rollback
                return False

    # Post-repair polish: 2-opt on touched routes
    for r in solution.routes:
        if id(r) in touched_routes:
            from operators.intra_route_2opt import intra_route_2opt_inplace
            intra_route_2opt_inplace(r)

    solution.update_cost()
    return solution.total_cost < current_obj - 1e-6


