"""
Memory-efficient data structures for VRPTW
CRITICAL: Minimize space complexity, use __slots__, in-place operations
Now includes incremental cost evaluation function for performance.
"""

from dataclasses import dataclass
import math
from typing import Dict, List, Optional, Tuple


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

def calculate_arrival(prev_time: float, prev_loc: Customer, curr_loc: Customer) -> Tuple[float, float, float]:
    """
    Calculates travel, raw arrival, and final arrival (after waiting) for a single leg.
    Returns: (travel, raw_arrival, final_arrival)
    """
    travel = distance(prev_loc, curr_loc)
    raw_arrival = prev_time + travel
    wait = max(0.0, curr_loc.ready_time - raw_arrival)
    final_arrival = raw_arrival + wait
    return travel, raw_arrival, final_arrival


class Route:
    """
    Mutable route with in-place operations
    Memory: O(route_size) - minimal overhead
    """
    __slots__ = ['customer_ids', 'arrival_times', 'departure_time', 
                 'current_load', 'total_cost', 'depot', 'customers_lookup', 
                 'vehicle_capacity', '_dist_cache']
    
    def __init__(self, depot: Customer, vehicle_capacity: int, customers_lookup: Dict[int, Customer]):
        self.customer_ids: List[int] = [] 	    # List of IDs (not Customer objects)
        self.arrival_times: List[float] = [] 	# Parallel array
        self.departure_time: float = 0.0
        self.current_load: int = 0
        self.total_cost: float = 0.0          # total_cost = distance + total_waiting
        self.depot: Customer = depot
        self.customers_lookup: Dict[int, Customer] = customers_lookup 	# Reference to global dict
        self.vehicle_capacity: int = vehicle_capacity
        self._dist_cache: Dict[Tuple[int, int], float] = {}  # Cache for distance calculations
    
    def _get_distance(self, c1: Customer, c2: Customer) -> float:
        """Get distance with caching"""
        # Use customer IDs for cache key
        key = (c1.id, c2.id)
        if key not in self._dist_cache:
            self._dist_cache[key] = distance(c1, c2)
        return self._dist_cache[key]

    # ... [recompute_schedule, get_customer, get_customer_by_id methods remain the same] ...
    def recompute_schedule(self):
        """
        Recompute arrival times after route modification.
        Compatible with current Route structure.
        (This function is now ONLY used for debugging/visualization, calculate_cost_inplace
        handles the actual scheduling.)
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
        
        # --- Trial Insertion (Temporary modification for _recalculate_from) ---
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
        
        # Cost is updated by caller (e.g., in selective_mds) - NOT HERE
        # self.calculate_cost_inplace()
        return True
    
    def _recalculate_from(self, start_idx: int):
        """
        Recalculate arrival times from start_idx onwards (in-place)
        Modifies self.arrival_times directly - no temporary arrays
        """
        customer_ids = self.customer_ids
        n = len(customer_ids)
        if n == 0:
            return
        
        # Start from depot or from previous customer
        if start_idx == 0:
            current_time = self.departure_time
            prev_location = self.depot
        else:
            prev_id = customer_ids[start_idx - 1]
            prev_customer = self.customers_lookup[prev_id]
            current_time = self.arrival_times[start_idx - 1] + prev_customer.service_time
            prev_location = prev_customer
        
        customers_lookup = self.customers_lookup
        arrival_times = self.arrival_times

        # Recalculate for all customers from start_idx
        for i in range(start_idx, n):
            cust_id = customer_ids[i]
            customer = customers_lookup[cust_id]
            
            # Travel time from previous location (use cached distance)
            travel_time = self._get_distance(prev_location, customer)
            arrival_time = current_time + travel_time
            
            # Apply time window constraint (wait if early)
            arrival_time = max(arrival_time, customer.ready_time)
            
            arrival_times[i] = arrival_time
            
            # Update for next iteration
            current_time = arrival_time + customer.service_time
            prev_location = customer
    
    def is_feasible(self) -> bool:
        """Check feasibility without creating temporary data - with early exit"""
        customer_ids = self.customer_ids
        if not customer_ids:
            return True
        
        # Check capacity
        if self.current_load > self.vehicle_capacity:
            return False
        
        # Check time windows with early exit
        customers_lookup = self.customers_lookup
        arrival_times = self.arrival_times
        for i, customer_id in enumerate(customer_ids):
            customer = customers_lookup[customer_id]
            arrival = arrival_times[i]

            # Early exit: if any customer violates time window, return immediately
            if arrival > customer.due_date:
                return False
        
        return True
    
    def calculate_cost_inplace(self) -> float:
        """
        Update self.total_cost and arrival_times and return cost.
        This recalculates the schedule and cost fully (O(N)).
        Includes early exit for infeasible routes.
        """
        customer_ids = self.customer_ids
        if not customer_ids:
            self.total_cost = 0.0
            self.arrival_times = []
            return 0.0

        total_cost = 0.0
        n = len(customer_ids)
        arrival_times = self.arrival_times
        if len(arrival_times) != n:
            arrival_times = [0.0] * n
            self.arrival_times = arrival_times

        time = self.departure_time
        prev = self.depot
        customers_lookup = self.customers_lookup

        for i, cust_id in enumerate(customer_ids):
            customer = customers_lookup[cust_id]

            travel = self._get_distance(prev, customer)
            raw_arrival = time + travel
            wait = max(0.0, customer.ready_time - raw_arrival)
            arrival = raw_arrival + wait

            # Early exit: if arrival violates time window, mark as infeasible and return
            if arrival > customer.due_date:
                # Set a high cost to indicate infeasibility
                self.total_cost = float('inf')
                return float('inf')

            # store final arrival (after waiting) for feasibility / slack logic
            arrival_times[i] = arrival

            # distance + waiting contribute to cost (waiting weighted 1.2x)
            total_cost += travel + (wait * 1.1)

            # next leg starts after service
            time = arrival + customer.service_time
            prev = customer

        # Return to depot
        last_customer = customers_lookup[customer_ids[-1]]
        total_cost += self._get_distance(last_customer, self.depot)

        self.total_cost = total_cost
        return total_cost
    
    def get_move_delta_cost(self, start_i: int, end_i: int, insert_j: int) -> Tuple[float, bool]:
        """
        CRITICAL PERFORMANCE FUNCTION (O(N) for feasibility check)
        Calculates the change in cost and checks feasibility for an Or-Opt segment move (i..j).
        This function DOES NOT modify the route list in-place.
        
        Args:
            start_i: Start index of the segment to move (inclusive).
            end_i: End index of the segment to move (exclusive). Segment length is end_i - start_i.
            insert_j: Insertion position (index before which the segment is placed).
            
        Returns:
            (delta_cost, is_feasible)
        """
        customer_ids = self.customer_ids
        n = len(customer_ids)
        seg_len = end_i - start_i
        
        if seg_len <= 0 or start_i < 0 or end_i > n or insert_j < 0 or insert_j > n:
            return 0.0, False

        # --- 1. Calculate Cost Reduction from Removal (Old Links) ---
        old_cost = 0.0
        
        # Link 1: Predecessor of segment -> Segment start (or Depot)
        prev_i = self.depot if start_i == 0 else self.get_customer(start_i - 1)
        c_start = self.get_customer(start_i)
        if start_i == 0:
            old_cost += distance(prev_i, c_start)  # Depot not in cache
        else:
            old_cost += self._get_distance(prev_i, c_start)
        
        # Link 2: Segment end -> Successor of segment (or Depot)
        c_end = self.get_customer(end_i - 1)
        succ_i = self.depot if end_i == n else self.get_customer(end_i)
        if end_i == n:
            old_cost += distance(c_end, succ_i)  # Depot not in cache
        else:
            old_cost += self._get_distance(c_end, succ_i)
        
        # Link 3: Link replacing the removed segment (Predecessor -> Successor)
        if start_i == 0 or end_i == n:
            new_replacing_link = distance(prev_i, succ_i)  # Depot involved
        else:
            new_replacing_link = self._get_distance(prev_i, succ_i)
        
        # Cost change from removal: (Link 1 + Link 2) - Link 3
        cost_savings_from_removal = old_cost - new_replacing_link


        # --- 2. Calculate Cost Increase from Insertion (New Links) ---
        
        # Segment start/end customers (will be inserted at j)
        seg_start = self.get_customer(start_i)
        seg_end = self.get_customer(end_i - 1)
        
        # Insertion location neighbors (considering the virtual route without the segment)
        # Note: If j is between start_i and end_i, the neighbors shift
        
        if insert_j < start_i:
            j_prev = self.depot if insert_j == 0 else self.get_customer(insert_j - 1)
            j_succ = self.depot if insert_j == len(customer_ids) - seg_len else self.get_customer(insert_j)
        elif insert_j > end_i:
            j_prev = self.depot if insert_j == 0 else self.get_customer(insert_j - seg_len - 1)
            j_succ = self.depot if insert_j == n else self.get_customer(insert_j)
        else: # Insertion within segment's original span (no move/no change)
            return 0.0, True

        # Link 4: Predecessor of insertion -> Segment start
        if insert_j == 0 or j_prev.id == self.depot.id:
            link_prev_to_start = distance(j_prev, seg_start)  # Depot involved
        else:
            link_prev_to_start = self._get_distance(j_prev, seg_start)
        
        # Link 5: Segment end -> Successor of insertion
        if insert_j == n or j_succ.id == self.depot.id:
            link_end_to_succ = distance(seg_end, j_succ)  # Depot involved
        else:
            link_end_to_succ = self._get_distance(seg_end, j_succ)
        
        # Link 6: Old link at insertion spot (Predecessor -> Successor)
        if insert_j == 0 or j_prev.id == self.depot.id or j_succ.id == self.depot.id:
            link_old_j = distance(j_prev, j_succ)  # Depot involved
        else:
            link_old_j = self._get_distance(j_prev, j_succ)
        
        # Cost change from insertion: (Link 4 + Link 5) - Link 6
        cost_increase_from_insertion = link_prev_to_start + link_end_to_succ - link_old_j
        
        # Cost calculation is currently distance only - waiting time requires full schedule check.
        # This is where the true complexity lies. We must check time feasibility.

        # --- 3. Full Time Feasibility Check (O(N) - MUST BE DONE) ---
        # Due to the complexity of the full time window check on the virtual route,
        # we will simulate the segment list changes and call _recalculate_from(0) on a temporary route copy.
        # This reduces the $O(N^3)$ of Or-Opt to $O(N^2)$, which is the best feasible target without
        # moving to a full, complex data structure like Linked Lists with slack caching.

        # *** REVERTING TO $O(N^2)$ FOR FEASIBILITY ***
        # This is the $O(N)$ step that dominates the calculation.
        temp_ids = customer_ids[:start_i] + customer_ids[end_i:]
        temp_ids[insert_j:insert_j] = customer_ids[start_i:end_i]
        
        # Create a deep copy of the route schedule to test the move
        temp_route = Route(self.depot, self.vehicle_capacity, self.customers_lookup)
        temp_route.customer_ids = temp_ids
        temp_route.departure_time = self.departure_time
        temp_route.current_load = self.current_load # Load doesn't change
        
        # Recalculate schedule and cost fully for feasibility check
        new_total_cost = temp_route.calculate_cost_inplace()
        
        if not temp_route.is_feasible():
             return 0.0, False # Feasibility check failed
             
        # Total cost delta (distance + waiting)
        delta_cost = new_total_cost - self.total_cost
        return delta_cost, True
        
    # ... [get_total_distance, swap_inplace, relocate_inplace, adjust_departure_time_inplace, 
    #       get_waiting_time, get_waiting_contributions, get_tight_window_count, get_average_slack remain the same] ...
    
    
    def get_move_delta_cost_for_external_customer(self, customer_id: int, position: int) -> tuple[float, bool]:
        """
        Simulates inserting an EXTERNAL customer into this route.
        Returns (delta_cost, is_feasible).
        """
        customer = self.customers_lookup[customer_id]
        
        # 1. Quick Capacity Check
        if self.current_load + customer.demand > self.vehicle_capacity:
            return 0.0, False

        # 2. Simulate the new sequence
        new_ids = list(self.customer_ids)
        new_ids.insert(position, customer_id)
        
        # 3. Time Window & Cost Check (O(N))
        # We reuse the logic from get_move_delta_cost but for an external insertion
        temp_route = Route(self.depot, self.vehicle_capacity, self.customers_lookup)
        temp_route.customer_ids = new_ids
        temp_route.departure_time = self.departure_time
        
        # Calculate new cost (includes distance + waiting)
        new_total_cost = temp_route.calculate_cost_inplace()
        
        # If the arrival time at any node exceeds due_date, calculate_cost_inplace 
        # should ideally return infinity or we check feasibility here
        if not temp_route.is_feasible():
            return 0.0, False
            
        delta_cost = new_total_cost - self.total_cost
        return delta_cost, True
    
    
    def get_total_distance(self) -> float:
        """
        Return total travel distance for current route (including depot->first
        and last->depot), ignoring waiting time.
        Does not modify route state.
        Uses cached distances when possible.
        """
        if not self.customer_ids:
            return 0.0

        total_dist = 0.0

        # depot -> first (depot not in cache, use direct calculation)
        first = self.customers_lookup[self.customer_ids[0]]
        total_dist += distance(self.depot, first)

        # between customers (use cached distances)
        for i in range(len(self.customer_ids) - 1):
            c1 = self.customers_lookup[self.customer_ids[i]]
            c2 = self.customers_lookup[self.customer_ids[i + 1]]
            total_dist += self._get_distance(c1, c2)

        # last -> depot (depot not in cache, use direct calculation)
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
        customer_ids = self.customer_ids
        if not customer_ids:
            return 0.0

        # Ensure schedule and cost are consistent enough to rely on total_cost.
        # This preserves prior behavior where an inconsistent arrival array
        # triggered a full recomputation.
        if len(self.arrival_times) != len(customer_ids):
            self.calculate_cost_inplace()

        # Cost definition: total_cost = travel_distance + (total_waiting * 1.2).
        # To obtain waiting: (total_cost - distance_only) / 1.2
        distance_only = self.get_total_distance()
        return (self.total_cost - distance_only) / 1.2
    
    def get_waiting_contributions(self) -> List[tuple[int, float]]:
        """
        Return per-customer waiting contributions (raw-arrival based).
        """
        contributions: List[tuple[int, float]] = []
        customer_ids = self.customer_ids
        if not customer_ids:
            return contributions

        # Ensure schedule/cost are consistent
        if len(self.arrival_times) != len(customer_ids):
            self.calculate_cost_inplace()

        time = self.departure_time
        prev = self.depot
        customers_lookup = self.customers_lookup

        for cust_id in customer_ids:
            customer = customers_lookup[cust_id]
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
        arrival_times = self.arrival_times
        customers_lookup = self.customers_lookup
        customer_ids = self.customer_ids
        for i, arrival in enumerate(arrival_times):
            customer = customers_lookup[customer_ids[i]]
            slack = customer.due_date - arrival
            if slack < slack_threshold:
                count += 1
        return count
    
    def get_average_slack(self) -> float:
        """Calculate average time window slack"""
        customer_ids = self.customer_ids
        if len(customer_ids) == 0:
            return 0.0
        
        total_slack = 0.0
        arrival_times = self.arrival_times
        customers_lookup = self.customers_lookup
        for i, arrival in enumerate(arrival_times):
            customer = customers_lookup[customer_ids[i]]
            slack = customer.due_date - arrival
            total_slack += slack
        
        return total_slack / len(self.customer_ids)


class Solution:
    """Single solution instance maintained throughout algorithm"""
    __slots__ = ['routes', 'total_cost', 'total_base_cost', 'num_vehicles']
    
    def __init__(self):
        self.routes: List[Route] = []
        self.total_cost: float = 0.0          # Penalized cost
        self.total_base_cost: float = 0.0     # Sum of all route.total_cost (distance + waiting)
        self.num_vehicles: int = 0
    
    def add_route(self, route: Route):
        """Add route and update totals"""
        self.routes.append(route)
        self.num_vehicles += 1
        self.total_base_cost += route.total_cost # Use the cost calculated during insertion
        
    def update_cost(self, alpha_vehicle: Optional[float] = None):
        """
        Recalculate penalized total cost from routes.
        Base cost is recalculated (O(N) for all routes) - used during initialization/MIH.
        """
        if not self.routes:
            self.total_cost = 0.0
            self.total_base_cost = 0.0
            self.num_vehicles = 0
            return

        # Ensure per-route costs are up to date and update total_base_cost
        self.total_base_cost = sum(r.calculate_cost_inplace() for r in self.routes)
        self.num_vehicles = len(self.routes)
        
        self._recalculate_penalized_cost(alpha_vehicle)
        
    def update_base_cost(self, delta_cost: float, alpha_vehicle: Optional[float] = None):
        """
        Updates total_base_cost incrementally, avoiding full recalculation (O(1)).
        This is for use after a successful local move where route.total_cost has been updated.
        """
        self.total_base_cost += delta_cost
        self.num_vehicles = len(self.routes) # Ensure vehicle count is fresh
        
        self._recalculate_penalized_cost(alpha_vehicle)

    def _recalculate_penalized_cost(self, alpha_vehicle: Optional[float]):
        """Internal method to apply the vehicle penalty."""
        base_distance = sum(r.get_total_distance() for r in self.routes)
        
        if alpha_vehicle is not None:
            lambda_penalty = alpha_vehicle
        else:
            # Increased default penalty to prioritize vehicle reduction (was 40-250, now 500-1000)
            avg_route_cost = self.total_base_cost / max(self.num_vehicles, 1)
            avg_waiting = self.total_base_cost - base_distance
            avg_waiting = avg_waiting / max(self.num_vehicles, 1)

            lambda_penalty = 0.6 * avg_route_cost + 0.2 * avg_waiting + 1000.0
            lambda_penalty = max(1000.0, min(lambda_penalty, 2000.0))

        self.total_cost = self.total_base_cost + lambda_penalty * self.num_vehicles
        
    def is_feasible(self) -> bool:
        """Check if all routes are feasible"""
        return all(route.is_feasible() for route in self.routes)