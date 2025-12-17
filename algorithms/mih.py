"""
Limited Candidate Regret-2 Multiple Insertion Heuristic (MIH)
Designed to leave structured improvement potential for MDS
"""

import random
from typing import List, Dict, Optional, Tuple
from core.data_structures import Customer, Route, Solution, distance


def limited_candidate_mih(
    depot: Customer,
    customers: List[Customer],
    vehicle_capacity: int,
    candidate_ratio: float = 0.3,
    min_candidates: int = 3,
    random_seed: Optional[int] = None
) -> Solution:

    if random_seed is not None:
        random.seed(random_seed)

    customers_lookup: Dict[int, Customer] = {c.id: c for c in customers}
    unrouted_ids: List[int] = [c.id for c in customers]
    random.shuffle(unrouted_ids)  # weaken/perturb initial order

    solution = Solution()

    # Pre-create one empty route
    routes: List[Route] = []

    while unrouted_ids:
        # Ensure at least one route exists
        if not routes:
            routes.append(Route(depot, vehicle_capacity, customers_lookup))

        # -------------------------------
        # REGRET-2 SELECTION
        # -------------------------------
        best_choice: Optional[
            Tuple[float, float, int, Route, int]
        ] = None

        num_candidates = max(
            min_candidates,
            int(len(unrouted_ids) * candidate_ratio)
        )

        sampled_ids = random.sample(
            unrouted_ids,
            min(num_candidates, len(unrouted_ids))
        )

        for customer_id in sampled_ids:
            customer = customers_lookup[customer_id]

            best = float('inf')
            second_best = float('inf')
            best_route = None
            best_position = None

            for route in routes:
                for pos in range(len(route.customer_ids) + 1):
                    cost = calculate_insertion_cost_inline(route, customer, pos)

                    if cost < best:
                        second_best = best
                        best = cost
                        best_route = route
                        best_position = pos
                    elif cost < second_best:
                        second_best = cost

            # Also consider opening a NEW route (penalized)
            new_route = Route(depot, vehicle_capacity, customers_lookup)
            cost_new = calculate_insertion_cost_inline(new_route, customer, 0)

            if cost_new < best:
                second_best = best
                best = cost_new
                best_route = new_route
                best_position = 0

            regret = second_best - best

            if best < float('inf'):
                candidate = (regret, best, customer_id, best_route, best_position)
                if best_choice is None or regret > best_choice[0]:
                    best_choice = candidate

        # -------------------------------
        # INSERT SELECTED CUSTOMER
        # -------------------------------
        if best_choice is None:
            # Forced new route fallback
            cid = unrouted_ids.pop(0)
            r = Route(depot, vehicle_capacity, customers_lookup)
            r.insert_inplace(cid, 0)
            routes.append(r)
            continue

        _, _, customer_id, route, position = best_choice

        # If route is new, register it
        if route not in routes:
            routes.append(route)

        inserted = route.insert_inplace(customer_id, position)
        if inserted:
            unrouted_ids.remove(customer_id)
        else:
            # Fallback: open new route
            fallback = Route(depot, vehicle_capacity, customers_lookup)
            fallback.insert_inplace(customer_id, 0)
            routes.append(fallback)
            unrouted_ids.remove(customer_id)

    # Finalize solution
    for r in routes:
        if r.customer_ids:
            solution.add_route(r)

    solution.update_cost()
    return solution


# ==========================================================
# COST FUNCTION (INTENTIONALLY IMPERFECT)
# ==========================================================

def calculate_insertion_cost_inline(route: Route, customer: Customer, position: int) -> float:
    """
    Smart insertion cost that minimizes waiting time + distance.
    Estimates the waiting time that would be added by inserting at this position.
    """

    # Capacity
    if route.current_load + customer.demand > route.vehicle_capacity:
        return float('inf')

    additional_distance = 0.0
    estimated_waiting = 0.0

    if len(route.customer_ids) == 0:
        # New route
        additional_distance = (
            distance(route.depot, customer) +
            distance(customer, route.depot)
        )
        # Estimate waiting: if we arrive before ready_time, we wait
        travel_time = distance(route.depot, customer)
        arrival_time = route.departure_time + travel_time
        estimated_waiting = max(0.0, customer.ready_time - arrival_time)
        # Penalize new vehicle heavily
        additional_distance += 100.0

    elif position == 0:
        # Insert at beginning
        first = route.get_customer(0)
        additional_distance = (
            distance(route.depot, customer) +
            distance(customer, first) -
            distance(route.depot, first)
        )
        # Estimate waiting: travel from depot, check if we arrive before ready_time
        travel_time = distance(route.depot, customer)
        arrival_time = route.departure_time + travel_time
        estimated_waiting = max(0.0, customer.ready_time - arrival_time)

    elif position == len(route.customer_ids):
        # Insert at end
        last = route.get_customer(-1)
        additional_distance = (
            distance(last, customer) +
            distance(customer, route.depot) -
            distance(last, route.depot)
        )
        # Estimate waiting: use last customer's departure time
        if len(route.arrival_times) > 0:
            last_arrival = route.arrival_times[-1]
            last_customer = last
            last_departure = last_arrival + last_customer.service_time
        else:
            last_departure = route.departure_time
        travel_time = distance(last, customer)
        arrival_time = last_departure + travel_time
        estimated_waiting = max(0.0, customer.ready_time - arrival_time)

    else:
        # Insert in middle
        prev = route.get_customer(position - 1)
        nxt = route.get_customer(position)
        additional_distance = (
            distance(prev, customer) +
            distance(customer, nxt) -
            distance(prev, nxt)
        )
        # Estimate waiting: use previous customer's departure time
        if position - 1 < len(route.arrival_times):
            prev_arrival = route.arrival_times[position - 1]
            prev_departure = prev_arrival + prev.service_time
        else:
            prev_departure = route.departure_time
        travel_time = distance(prev, customer)
        arrival_time = prev_departure + travel_time
        estimated_waiting = max(0.0, customer.ready_time - arrival_time)
        
        # Also check if this insertion causes waiting for next customer
        customer_departure = arrival_time + estimated_waiting + customer.service_time
        next_travel = distance(customer, nxt)
        next_arrival = customer_departure + next_travel
        if position < len(route.arrival_times):
            original_next_arrival = route.arrival_times[position]
            if next_arrival > original_next_arrival:
                # This insertion delays the next customer
                estimated_waiting += (next_arrival - original_next_arrival) * 0.5  # Weighted penalty

    # Time-window tightness penalty
    tw_width = customer.due_date - customer.ready_time
    if tw_width < 20:
        additional_distance += 10.0
    elif tw_width < 40:
        additional_distance += 4.0

    # Prefer consolidating routes
    if len(route.customer_ids) > 0:
        additional_distance -= 3.0

    # Total cost = distance + waiting (matching the objective function)
    return additional_distance + estimated_waiting
