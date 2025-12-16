"""
Memory-efficient data structures for VRPTW
CRITICAL: Minimize space complexity, use __slots__, in-place operations
"""

from dataclasses import dataclass
import math
from typing import Dict, List, Optional


@dataclass
class Customer:
    """Minimal customer representation - ~56 bytes per instance"""
    id: int
    x: float
    y: float
    demand: int
    ready_time: int
    due_date: int
    service_time: int
    
    def __post_init__(self):
        """Ensure __slots__ behavior by using dataclass"""
        pass


def distance(c1: Customer, c2: Customer) -> float:
    """
    Calculate Euclidean distance on-the-fly
    NO CACHING - O(1) space complexity
    """
    return math.sqrt((c1.x - c2.x)**2 + (c1.y - c2.y)**2)


class Route:
    """
    Mutable route with in-place operations
    Memory: O(route_size) - minimal overhead
    """
    __slots__ = ['customer_ids', 'arrival_times', 'departure_time', 
                 'current_load', 'total_cost', 'depot', 'customers_lookup', 
                 'vehicle_capacity']
    
    def __init__(self, depot: Customer, vehicle_capacity: int, customers_lookup: Dict[int, Customer]):
        self.customer_ids: List[int] = []        # List of IDs (not Customer objects)
        self.arrival_times: List[float] = []     # Parallel array
        self.departure_time: float = 0.0
        self.current_load: int = 0
        self.total_cost: float = 0.0
        self.depot: Customer = depot
        self.customers_lookup: Dict[int, Customer] = customers_lookup  # Reference to global dict
        self.vehicle_capacity: int = vehicle_capacity

    def recompute_schedule(self):
        """
        Recompute arrival times after route modification.
        Compatible with current Route structure.
        """

        self.arrival_times.clear()

        time = self.departure_time
        prev = self.depot

        for cust_id in self.customer_ids:
            customer = self.customers_lookup[cust_id]

            travel = distance(prev, customer)
            arrival = max(time + travel, customer.ready_time)

            self.arrival_times.append(arrival)

            # departure = arrival + service_time
            time = arrival + customer.service_time
            prev = customer

    
    def get_customer(self, idx: int) -> Customer:
        """Get customer object by index without storing duplicates"""
        return self.customers_lookup[self.customer_ids[idx]]

    def get_customer_by_id(self, customer_id):
        """
        Return Customer object for given customer_id
        Route already holds reference to customers dict
        """
        return self.customers_lookup[customer_id]

    
    def insert_inplace(self, customer_id: int, position: int) -> bool:
        """
        Insert customer and update only affected portion
        Returns True if insertion was successful and feasible
        """
        customer = self.customers_lookup[customer_id]
        
        # Check capacity constraint
        if self.current_load + customer.demand > self.vehicle_capacity:
            return False
        
        self.customer_ids.insert(position, customer_id)
        self.arrival_times.insert(position, 0.0)
        self.current_load += customer.demand
        
        # Recalculate from position onwards
        self._recalculate_from(position)
        
        # Check feasibility after insertion
        if not self.is_feasible():
            # Rollback
            self.customer_ids.pop(position)
            self.arrival_times.pop(position)
            self.current_load -= customer.demand
            self._recalculate_from(position)
            return False
        
        self.calculate_cost_inplace()
        return True
    
    def _recalculate_from(self, start_idx: int):
        """
        Recalculate arrival times from start_idx onwards (in-place)
        Modifies self.arrival_times directly - no temporary arrays
        """
        if len(self.customer_ids) == 0:
            return
        
        # Start from depot or from previous customer
        if start_idx == 0:
            current_time = self.departure_time
            prev_location = self.depot
        else:
            prev_customer = self.get_customer(start_idx - 1)
            current_time = self.arrival_times[start_idx - 1] + prev_customer.service_time
            prev_location = prev_customer
        
        # Recalculate for all customers from start_idx
        for i in range(start_idx, len(self.customer_ids)):
            customer = self.get_customer(i)
            
            # Travel time from previous location
            travel_time = distance(prev_location, customer)
            arrival_time = current_time + travel_time
            
            # Apply time window constraint (wait if early)
            arrival_time = max(arrival_time, customer.ready_time)
            
            self.arrival_times[i] = arrival_time
            
            # Update for next iteration
            current_time = arrival_time + customer.service_time
            prev_location = customer
    
    def is_feasible(self) -> bool:
        """Check feasibility without creating temporary data"""
        if len(self.customer_ids) == 0:
            return True
        
        # Check capacity
        if self.current_load > self.vehicle_capacity:
            return False
        
        # Check time windows
        for i, customer_id in enumerate(self.customer_ids):
            customer = self.customers_lookup[customer_id]
            arrival = self.arrival_times[i]
            
            if arrival > customer.due_date:
                return False
        
        return True
    
    def calculate_cost_inplace(self) -> float:
        """
        Update self.total_cost and arrival_times and return cost.
        
        Cost = travel distance + waiting time.
        Waiting is computed against the *raw* arrival
        (before applying max(raw_arrival, ready_time)).
        """
        if not self.customer_ids:
            self.total_cost = 0.0
            self.arrival_times = []
            return 0.0

        total_cost = 0.0
        n = len(self.customer_ids)
        if len(self.arrival_times) != n:
            self.arrival_times = [0.0] * n

        time = self.departure_time
        prev = self.depot

        for i, cust_id in enumerate(self.customer_ids):
            customer = self.customers_lookup[cust_id]

            travel = distance(prev, customer)
            raw_arrival = time + travel
            wait = max(0.0, customer.ready_time - raw_arrival)
            arrival = raw_arrival + wait

            # store final arrival (after waiting) for feasibility / slack logic
            self.arrival_times[i] = arrival

            # distance + waiting contribute to cost
            total_cost += travel + wait

            # next leg starts after service
            time = arrival + customer.service_time
            prev = customer

        # Return to depot
        last_customer = self.customers_lookup[self.customer_ids[-1]]
        total_cost += distance(last_customer, self.depot)

        self.total_cost = total_cost
        return total_cost
    
    def get_total_distance(self) -> float:
        """
        Return total travel distance for current route (including depot->first
        and last->depot), ignoring waiting time.
        Does not modify route state.
        """
        if not self.customer_ids:
            return 0.0

        total_dist = 0.0

        # depot -> first
        first = self.customers_lookup[self.customer_ids[0]]
        total_dist += distance(self.depot, first)

        # between customers
        for i in range(len(self.customer_ids) - 1):
            c1 = self.customers_lookup[self.customer_ids[i]]
            c2 = self.customers_lookup[self.customer_ids[i + 1]]
            total_dist += distance(c1, c2)

        # last -> depot
        last = self.customers_lookup[self.customer_ids[-1]]
        total_dist += distance(last, self.depot)

        return total_dist
    
    def swap_inplace(self, i: int, j: int) -> bool:
        """
        Swap customers at positions i and j WITHOUT creating new route
        Returns True if swap was successful and feasible
        """
        if i == j or i < 0 or j < 0 or i >= len(self.customer_ids) or j >= len(self.customer_ids):
            return False
        
        # Swap customer IDs
        self.customer_ids[i], self.customer_ids[j] = self.customer_ids[j], self.customer_ids[i]
        
        # Recalculate from the earlier position
        start_idx = min(i, j)
        self._recalculate_from(start_idx)
        
        # Check feasibility
        if not self.is_feasible():
            # Rollback
            self.customer_ids[i], self.customer_ids[j] = self.customer_ids[j], self.customer_ids[i]
            self._recalculate_from(start_idx)
            return False
        
        self.calculate_cost_inplace()
        return True
    
    def relocate_inplace(self, from_pos: int, to_pos: int) -> bool:
        """
        Move customer from from_pos to to_pos in same route
        Returns True if relocation was successful and feasible
        """
        if from_pos == to_pos or from_pos < 0 or to_pos < 0:
            return False
        if from_pos >= len(self.customer_ids) or to_pos >= len(self.customer_ids):
            return False
        
        # Remove customer from original position
        customer_id = self.customer_ids.pop(from_pos)
        self.arrival_times.pop(from_pos)
        
        # Adjust to_pos if needed (since we removed an element)
        if to_pos > from_pos:
            to_pos -= 1
        
        # Insert at new position
        self.customer_ids.insert(to_pos, customer_id)
        self.arrival_times.insert(to_pos, 0.0)
        
        # Recalculate from the earlier affected position
        start_idx = min(from_pos, to_pos)
        self._recalculate_from(start_idx)
        
        # Check feasibility
        if not self.is_feasible():
            # Rollback - remove from to_pos and reinsert at from_pos
            self.customer_ids.pop(to_pos)
            self.arrival_times.pop(to_pos)
            if to_pos < from_pos:
                self.customer_ids.insert(from_pos, customer_id)
                self.arrival_times.insert(from_pos, 0.0)
            else:
                self.customer_ids.insert(from_pos, customer_id)
                self.arrival_times.insert(from_pos, 0.0)
            self._recalculate_from(min(from_pos, to_pos))
            return False
        
        self.calculate_cost_inplace()
        return True
    
    def adjust_departure_time_inplace(self, new_departure: float) -> bool:
        """
        Adjust route departure time from depot (temporal shift)
        Returns True if adjustment was successful and feasible
        """
        if new_departure < 0:
            return False
        
        old_departure = self.departure_time
        self.departure_time = new_departure
        
        # Recalculate all arrival times
        self._recalculate_from(0)
        
        # Check feasibility
        if not self.is_feasible():
            # Rollback
            self.departure_time = old_departure
            self._recalculate_from(0)
            return False
        
        self.calculate_cost_inplace()
        return True
    
    def get_waiting_time(self) -> float:
        """
        Robust waiting time calculation.
        Uses the same raw-arrival-based definition as in calculate_cost_inplace.
        Automatically repairs schedule/cost if needed.
        """
        if not self.customer_ids:
            return 0.0

        # Ensure schedule and cost are consistent
        if len(self.arrival_times) != len(self.customer_ids):
            self.calculate_cost_inplace()

        waiting = 0.0

        time = self.departure_time
        prev = self.depot
        for cust_id in self.customer_ids:
            customer = self.customers_lookup[cust_id]
            travel = distance(prev, customer)
            raw_arrival = time + travel
            wait = max(0.0, customer.ready_time - raw_arrival)
            waiting += wait

            arrival = raw_arrival + wait
            time = arrival + customer.service_time
            prev = customer

        return waiting
    
    def get_waiting_contributions(self) -> List[tuple[int, float]]:
        """
        Return per-customer waiting contributions (raw-arrival based).
        """
        contributions: List[tuple[int, float]] = []
        if not self.customer_ids:
            return contributions

        # Ensure schedule/cost are consistent
        if len(self.arrival_times) != len(self.customer_ids):
            self.calculate_cost_inplace()

        time = self.departure_time
        prev = self.depot
        for cust_id in self.customer_ids:
            customer = self.customers_lookup[cust_id]
            travel = distance(prev, customer)
            raw_arrival = time + travel
            wait = max(0.0, customer.ready_time - raw_arrival)
            contributions.append((cust_id, wait))
            arrival = raw_arrival + wait
            time = arrival + customer.service_time
            prev = customer

        return contributions

    
    def get_tight_window_count(self, slack_threshold: float = 10.0) -> int:
        """Count customers with slack < threshold"""
        count = 0
        for i, arrival in enumerate(self.arrival_times):
            customer = self.get_customer(i)
            slack = customer.due_date - arrival
            if slack < slack_threshold:
                count += 1
        return count
    
    def get_average_slack(self) -> float:
        """Calculate average time window slack"""
        if len(self.customer_ids) == 0:
            return 0.0
        
        total_slack = 0.0
        for i, arrival in enumerate(self.arrival_times):
            customer = self.get_customer(i)
            slack = customer.due_date - arrival
            total_slack += slack
        
        return total_slack / len(self.customer_ids)


class Solution:
    """Single solution instance maintained throughout algorithm"""
    __slots__ = ['routes', 'total_cost', 'num_vehicles']
    
    def __init__(self):
        self.routes: List[Route] = []
        self.total_cost: float = 0.0
        self.num_vehicles: int = 0
    
    def add_route(self, route: Route):
        """Add route and update totals"""
        self.routes.append(route)
        self.num_vehicles += 1
        self.total_cost += route.total_cost
    
    def update_cost(self):
        """
        Recalculate penalised total cost from routes.

        Base distance+waiting is taken from each route.total_cost.
        A vehicle-count penalty λ * num_vehicles is added, where
        λ is approximated as the average route length.
        """
        if not self.routes:
            self.total_cost = 0.0
            self.num_vehicles = 0
            return

        # ensure per-route costs are up to date
        base_distance = 0.0
        for r in self.routes:
            base_distance += r.calculate_cost_inplace()

        self.num_vehicles = len(self.routes)

        # λ: dynamic penalty using distance and waiting signals
        avg_route_cost = base_distance / max(self.num_vehicles, 1)
        avg_waiting = 0.0
        for r in self.routes:
            avg_waiting += r.get_waiting_time()
        avg_waiting = avg_waiting / max(self.num_vehicles, 1)

        # Encourage fewer vehicles but react to waiting (tight time windows)
        lambda_penalty = 0.6 * avg_route_cost + 0.2 * avg_waiting + 30.0
        lambda_penalty = max(40.0, min(lambda_penalty, 250.0))

        self.total_cost = base_distance + lambda_penalty * self.num_vehicles
    
    def is_feasible(self) -> bool:
        """Check if all routes are feasible"""
        return all(route.is_feasible() for route in self.routes)







