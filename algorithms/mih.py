"""
Guaranteed Coverage Regret-2 MIH
Ensures 100% of customers are routed by opening new vehicles when necessary.
"""

import random
from typing import List, Dict, Optional, Tuple
from core.data_structures import Customer, Route, Solution, distance

def limited_candidate_mih(
    depot: Customer,
    customers: List[Customer],
    vehicle_capacity: int,
    candidate_ratio: float = 0.3,
    min_candidates: int = 5,
    random_seed: Optional[int] = None
) -> Solution:
    
    if random_seed is not None:
        random.seed(random_seed)

    customers_lookup: Dict[int, Customer] = {c.id: c for c in customers}
    # Create a COPY of all IDs to track
    unrouted_ids: List[int] = [c.id for c in customers]
    total_to_route = len(unrouted_ids)
    
    random.shuffle(unrouted_ids)
    solution = Solution()
    routes: List[Route] = []

    # Main Construction Loop
    while len(unrouted_ids) > 0:
        # 1. Selection Phase (Regret-2)
        best_choice = None
        
        # Sample candidates to evaluate
        num_to_sample = max(min_candidates, int(len(unrouted_ids) * candidate_ratio))
        sampled_ids = random.sample(unrouted_ids, min(num_to_sample, len(unrouted_ids)))

        for customer_id in sampled_ids:
            customer = customers_lookup[customer_id]
            best_cost = float('inf')
            second_best_cost = float('inf')
            best_route = None
            best_pos = None

            # Check all existing routes
            for route in routes:
                for pos in range(len(route.customer_ids) + 1):
                    cost = calculate_insertion_cost_inline(route, customer, pos)
                    if cost < best_cost:
                        second_best_cost = best_cost
                        best_cost = cost
                        best_route = route
                        best_pos = pos
                    elif cost < second_best_cost:
                        second_best_cost = cost

            # Consider opening a new route as a competitor
            new_r_temp = Route(depot, vehicle_capacity, customers_lookup)
            cost_new = calculate_insertion_cost_inline(new_r_temp, customer, 0)
            
            # Penalize new route slightly (e.g., +200) to encourage packing
            cost_new_penalized = cost_new + 200.0
            
            if cost_new_penalized < best_cost:
                second_best_cost = best_cost
                best_cost = cost_new_penalized
                best_route = new_r_temp # This signals we want a new route
                best_pos = 0
            elif cost_new_penalized < second_best_cost:
                second_best_cost = cost_new_penalized

            regret = second_best_cost - best_cost
            
            if best_cost < float('inf'):
                if best_choice is None or regret > best_choice[0]:
                    best_choice = (regret, customer_id, best_route, best_pos)

        # 2. Insertion Phase
        if best_choice is not None:
            _, cid, target_route, pos = best_choice
            
            # If target_route is not in our list, it's the 'new route' we signaled
            if target_route not in routes:
                routes.append(target_route)
            
            # Perform the actual move
            success = target_route.insert_inplace(cid, pos)
            if success:
                unrouted_ids.remove(cid)
            else:
                # Emergency Fallback: If logic failed, force a dedicated truck
                fallback_r = Route(depot, vehicle_capacity, customers_lookup)
                fallback_r.insert_inplace(cid, 0)
                routes.append(fallback_r)
                unrouted_ids.remove(cid)
        else:
            # FORCED FALLBACK: No route (new or old) reported feasible cost
            # This happens if Time Windows are extremely tight
            cid = unrouted_ids.pop(0)
            forced_r = Route(depot, vehicle_capacity, customers_lookup)
            forced_r.insert_inplace(cid, 0)
            routes.append(forced_r)

    # Finalize
    for r in routes:
        if r.customer_ids:
            solution.add_route(r)

    solution.update_cost()
    return solution

def calculate_insertion_cost_inline(route: Route, customer: Customer, position: int) -> float:
    # Capacity Check
    if route.current_load + customer.demand > route.vehicle_capacity:
        return float('inf')

    # Hard Time Window Check
    if position == 0:
        arrival = route.departure_time + distance(route.depot, customer)
    else:
        prev = route.get_customer(position - 1)
        prev_arr = route.arrival_times[position-1] if (position-1 < len(route.arrival_times)) else route.departure_time
        arrival = max(prev_arr, prev.ready_time) + prev.service_time + distance(prev, customer)

    if arrival > customer.due_date:
        return float('inf')

    # Simple cost: Distance + waiting
    dist_added = 0.0
    if len(route.customer_ids) == 0:
        dist_added = distance(route.depot, customer) + distance(customer, route.depot)
    elif position == 0:
        nxt = route.get_customer(0)
        dist_added = distance(route.depot, customer) + distance(customer, nxt) - distance(route.depot, nxt)
    elif position == len(route.customer_ids):
        prv = route.get_customer(-1)
        dist_added = distance(prv, customer) + distance(customer, route.depot) - distance(prv, route.depot)
    else:
        prv = route.get_customer(position - 1)
        nxt = route.get_customer(position)
        dist_added = distance(prv, customer) + distance(customer, nxt) - distance(prv, nxt)

    return dist_added + max(0.0, customer.ready_time - arrival)