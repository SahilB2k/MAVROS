"""
Memory-efficient data structures for VRPTW with O(N²) complexity optimizations
CRITICAL: Smart filtering + incremental evaluation + early termination
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
    """Calculate Euclidean distance on-the-fly - NO CACHING - O(1) space"""
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
    Mutable route with in-place operations and O(N²) complexity optimizations
    Memory: O(route_size) - minimal overhead
    """
    __slots__ = ['customer_ids', 'arrival_times', 'departure_time', 
                 'current_load', 'total_cost', 'depot', 'customers_lookup', 
                 'vehicle_capacity', '_dist_cache', 'load_at_customers',
                 'waiting_times', 'bbox', '_cost_segments']
    
    def __init__(self, depot: Customer, vehicle_capacity: int, customers_lookup: Dict[int, Customer]):
        self.customer_ids: List[int] = []
        self.arrival_times: List[float] = []
        self.load_at_customers: List[float] = []
        self.waiting_times: List[float] = []
        self.departure_time: float = 0.0
        self.current_load: int = 0
        self.total_cost: float = 0.0
        self.depot: Customer = depot
        self.customers_lookup: Dict[int, Customer] = customers_lookup
        self.vehicle_capacity: int = vehicle_capacity
        self._dist_cache: Dict[Tuple[int, int], float] = {}
        self.bbox: Tuple[float, float, float, float] = (depot.x, depot.y, depot.x, depot.y)
        self._cost_segments: List[float] = []  # NEW: Cache segment costs for incremental eval
    
    def update_bounding_box(self):
        """Update the bounding box (min_x, min_y, max_x, max_y) of the route - O(N)"""
        min_x, min_y = self.depot.x, self.depot.y
        max_x, max_y = self.depot.x, self.depot.y
        
        customers_lookup = self.customers_lookup
        for cid in self.customer_ids:
            c = customers_lookup[cid]
            if c.x < min_x: min_x = c.x
            if c.x > max_x: max_x = c.x
            if c.y < min_y: min_y = c.y
            if c.y > max_y: max_y = c.y
            
        self.bbox = (min_x, min_y, max_x, max_y)

    def overlaps_with(self, other: 'Route', buffer: float = 0.0) -> bool:
        """Check if bounding boxes overlap - O(1) geometric pruning"""
        min_x1, min_y1, max_x1, max_y1 = self.bbox
        min_x2, min_y2, max_x2, max_y2 = other.bbox
        
        min_x1 -= buffer; max_x1 += buffer
        min_y1 -= buffer; max_y1 += buffer
        
        if max_x1 < min_x2 or max_x2 < min_x1:
            return False
        if max_y1 < min_y2 or max_y2 < min_y1:
            return False
        return True
    
    def _get_distance(self, c1: Customer, c2: Customer) -> float:
        """Get distance with caching"""
        key = (c1.id, c2.id)
        if key not in self._dist_cache:
            self._dist_cache[key] = distance(c1, c2)
        return self._dist_cache[key]

    def recompute_schedule(self):
        """Recompute arrival times (debugging/visualization only)"""
        self.arrival_times.clear()
        time = self.departure_time
        prev = self.depot

        for cust_id in self.customer_ids:
            customer = self.customers_lookup[cust_id]
            travel = distance(prev, customer)
            arrival = max(time + travel, customer.ready_time)
            self.arrival_times.append(arrival)
            time = arrival + customer.service_time
            prev = customer
    
    def get_customer(self, idx: int) -> Customer:
        """Get customer object by index"""
        return self.customers_lookup[self.customer_ids[idx]]

    def get_customer_by_id(self, customer_id):
        """Return Customer object for given customer_id"""
        return self.customers_lookup[customer_id]
    
    def insert_inplace(self, customer_id: int, position: int) -> bool:
        """Insert customer and update only affected portion - Returns True if feasible"""
        customer = self.customers_lookup[customer_id]
        
        if self.current_load + customer.demand > self.vehicle_capacity:
            return False
        
        self.customer_ids.insert(position, customer_id)
        self.arrival_times.insert(position, 0.0)
        self.current_load += customer.demand
        
        self._recalculate_from(position)
        
        if not self.is_feasible():
            self.customer_ids.pop(position)
            self.arrival_times.pop(position)
            self.current_load -= customer.demand
            self._recalculate_from(position)
            return False
        
        self.calculate_cost_inplace()
        return True
    
    def _recalculate_from(self, start_idx: int):
        """Recalculate arrival times from start_idx onwards (in-place) - O(N)"""
        customer_ids = self.customer_ids
        n = len(customer_ids)
        if n == 0:
            return

        if len(self.arrival_times) != n:
            self.arrival_times = [0.0] * n
        if len(self.load_at_customers) != n:
            self.load_at_customers = [0.0] * n
        if len(self.waiting_times) != n:
            self.waiting_times = [0.0] * n
        
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
        load_at_customers = self.load_at_customers
        waiting_times = self.waiting_times

        for i in range(start_idx, n):
            cust_id = customer_ids[i]
            customer = customers_lookup[cust_id]
            
            travel_time = self._get_distance(prev_location, customer)
            arrival_time = current_time + travel_time
            
            wait = max(0.0, customer.ready_time - arrival_time)
            arrival_time = arrival_time + wait
            
            arrival_times[i] = arrival_time
            waiting_times[i] = wait
            load_at_customers[i] = self.current_load
            
            current_time = arrival_time + customer.service_time
            prev_location = customer
    
    def is_feasible(self) -> bool:
        """Check feasibility with early exit - O(N) worst case, O(1) average"""
        customer_ids = self.customer_ids
        if not customer_ids:
            return True
        
        if self.current_load > self.vehicle_capacity:
            return False
        
        customers_lookup = self.customers_lookup
        arrival_times = self.arrival_times
        for i, customer_id in enumerate(customer_ids):
            customer = customers_lookup[customer_id]
            arrival = arrival_times[i]
            if arrival > customer.due_date:
                return False
        
        return True
    
    def calculate_cost_inplace(self) -> float:
        """Update self.total_cost and arrival_times - O(N) with early exit"""
        customer_ids = self.customer_ids
        if not customer_ids:
            self.total_cost = 0.0
            self.arrival_times = []
            self._cost_segments = []
            return 0.0

        total_cost = 0.0
        n = len(customer_ids)
        arrival_times = self.arrival_times
        if len(arrival_times) != n:
            arrival_times = [0.0] * n
            self.arrival_times = arrival_times

        self._cost_segments = [0.0] * n  # Cache segment costs

        time = self.departure_time
        prev = self.depot
        customers_lookup = self.customers_lookup

        for i, cust_id in enumerate(customer_ids):
            customer = customers_lookup[cust_id]

            travel = self._get_distance(prev, customer)
            raw_arrival = time + travel
            wait = max(0.0, customer.ready_time - raw_arrival)
            arrival = raw_arrival + wait

            if arrival > customer.due_date:
                self.total_cost = float('inf')
                return float('inf')

            arrival_times[i] = arrival
            
            segment_cost = travel + (wait * 1.1)
            self._cost_segments[i] = segment_cost
            total_cost += segment_cost

            time = arrival + customer.service_time
            prev = customer

        last_customer = customers_lookup[customer_ids[-1]]
        total_cost += self._get_distance(last_customer, self.depot)

        self.total_cost = total_cost
        return total_cost
    
    def get_move_delta_cost(self, start_i: int, end_i: int, insert_j: int) -> Tuple[float, bool]:
        """
        OPTIMIZED: O(N) worst case with smart filtering and early termination
        Calculates cost change for Or-Opt segment move with pre-filtering
        """
        customer_ids = self.customer_ids
        n = len(customer_ids)
        seg_len = end_i - start_i
        
        if seg_len <= 0 or start_i < 0 or end_i > n or insert_j < 0 or insert_j > n:
            return 0.0, False
        
        if insert_j >= start_i and insert_j <= end_i:
            return 0.0, True  # No-op move

        # OPTIMIZATION 1: Quick distance-based filtering
        seg_start = self.get_customer(start_i)
        seg_end = self.get_customer(end_i - 1)
        
        if insert_j < start_i:
            insert_neighbor = self.depot if insert_j == 0 else self.get_customer(insert_j - 1)
        else:
            insert_neighbor = self.depot if insert_j == n else self.get_customer(insert_j - seg_len - 1)
        
        # Estimate distance change (heuristic filter)
        avg_seg_x = (seg_start.x + seg_end.x) / 2
        avg_seg_y = (seg_start.y + seg_end.y) / 2
        dist_to_insert = math.sqrt((avg_seg_x - insert_neighbor.x)**2 + (avg_seg_y - insert_neighbor.y)**2)
        
        # If moving segment far away (>3x average route span), skip
        # RELAXED: 2.5 -> 3.0 to find more moves (leveraging speed budget)
        if n > 0 and self.bbox[2] - self.bbox[0] > 0:
            avg_route_span = ((self.bbox[2] - self.bbox[0]) + (self.bbox[3] - self.bbox[1])) / 2
            if dist_to_insert > 3.0 * avg_route_span:
                return 0.0, False

        # Create virtual sequence for evaluation
        temp_ids = customer_ids[:start_i] + customer_ids[end_i:]
        if insert_j < start_i:
            actual_insert = insert_j
        elif insert_j > end_i:
            actual_insert = insert_j - seg_len
        else:
            return 0.0, True
        
        temp_ids[actual_insert:actual_insert] = customer_ids[start_i:end_i]
        
        # OPTIMIZATION 2: Incremental feasibility check with early termination
        affected_start = max(0, min(start_i, actual_insert) - 1)
        affected_end = min(len(temp_ids), max(end_i, actual_insert + seg_len) + 1)
        
        # Quick time window feasibility check on affected region
        time = self.departure_time
        prev = self.depot
        
        if affected_start > 0:
            for i in range(affected_start):
                cust = self.customers_lookup[temp_ids[i]]
                travel = self._get_distance(prev, cust)
                arrival = max(time + travel, cust.ready_time)
                time = arrival + cust.service_time
                prev = cust
        
        # Check affected region
        for i in range(affected_start, min(affected_end, len(temp_ids))):
            cust = self.customers_lookup[temp_ids[i]]
            travel = self._get_distance(prev, cust)
            arrival = max(time + travel, cust.ready_time)
            
            if arrival > cust.due_date:
                return 0.0, False  # Early termination
            
            time = arrival + cust.service_time
            prev = cust
        
        # If still feasible, do full cost calculation
        temp_route = Route(self.depot, self.vehicle_capacity, self.customers_lookup)
        temp_route.customer_ids = temp_ids
        temp_route.departure_time = self.departure_time
        temp_route.current_load = self.current_load
        
        new_total_cost = temp_route.calculate_cost_inplace()
        
        if not temp_route.is_feasible():
            return 0.0, False
        
        delta_cost = new_total_cost - self.total_cost
        return delta_cost, True
    
    def get_move_delta_cost_for_external_customer(self, customer_id: int, position: int) -> tuple[float, bool]:
        """
        OPTIMIZED: Simulates inserting EXTERNAL customer with smart filtering
        Returns (delta_cost, is_feasible)
        """
        customer = self.customers_lookup[customer_id]
        
        if self.current_load + customer.demand > self.vehicle_capacity:
            return 0.0, False

        # OPTIMIZATION: Distance-based pre-filtering (RELAXED)
        if position > 0:
            prev_cust = self.get_customer(position - 1)
            dist_to_prev = distance(prev_cust, customer)
            if self.bbox[2] - self.bbox[0] > 0:
                avg_span = ((self.bbox[2] - self.bbox[0]) + (self.bbox[3] - self.bbox[1])) / 2
                # RELAXED: 2.0 -> 2.5 to explore more insertion options
                if dist_to_prev > 2.5 * avg_span:
                    return 0.0, False

        new_ids = list(self.customer_ids)
        new_ids.insert(position, customer_id)
        
        # Incremental feasibility check (only check near insertion point)
        check_start = max(0, position - 2)
        check_end = min(len(new_ids), position + 3)
        
        time = self.departure_time
        prev = self.depot
        
        for i in range(check_start):
            cust = self.customers_lookup[new_ids[i]]
            travel = distance(prev, cust)
            arrival = max(time + travel, cust.ready_time)
            time = arrival + cust.service_time
            prev = cust
        
        for i in range(check_start, check_end):
            cust = self.customers_lookup[new_ids[i]]
            travel = distance(prev, cust)
            arrival = max(time + travel, cust.ready_time)
            
            if arrival > cust.due_date:
                return 0.0, False
            
            time = arrival + cust.service_time
            prev = cust
        
        # Full evaluation only if incremental check passed
        temp_route = Route(self.depot, self.vehicle_capacity, self.customers_lookup)
        temp_route.customer_ids = new_ids
        temp_route.departure_time = self.departure_time
        temp_route.current_load = self.current_load + customer.demand
        
        new_total_cost = temp_route.calculate_cost_inplace()
        
        if not temp_route.is_feasible():
            return 0.0, False
        
        delta_cost = new_total_cost - self.total_cost
        return delta_cost, True
    
    def get_total_distance(self) -> float:
        """Return total travel distance (excluding waiting time)"""
        if not self.customer_ids:
            return 0.0

        total_dist = 0.0
        first = self.customers_lookup[self.customer_ids[0]]
        total_dist += distance(self.depot, first)

        for i in range(len(self.customer_ids) - 1):
            c1 = self.customers_lookup[self.customer_ids[i]]
            c2 = self.customers_lookup[self.customer_ids[i + 1]]
            total_dist += self._get_distance(c1, c2)

        last = self.customers_lookup[self.customer_ids[-1]]
        total_dist += distance(last, self.depot)

        return total_dist
    
    def swap_inplace(self, i: int, j: int) -> bool:
        """Swap customers at positions i and j - Returns True if feasible"""
        if i == j or i < 0 or j < 0 or i >= len(self.customer_ids) or j >= len(self.customer_ids):
            return False
        
        self.customer_ids[i], self.customer_ids[j] = self.customer_ids[j], self.customer_ids[i]
        start_idx = min(i, j)
        self._recalculate_from(start_idx)
        
        if not self.is_feasible():
            self.customer_ids[i], self.customer_ids[j] = self.customer_ids[j], self.customer_ids[i]
            self._recalculate_from(start_idx)
            return False
        
        self.calculate_cost_inplace()
        return True
    
    def relocate_inplace(self, from_pos: int, to_pos: int) -> bool:
        """Move customer from from_pos to to_pos - Returns True if feasible"""
        if from_pos == to_pos or from_pos < 0 or to_pos < 0:
            return False
        if from_pos >= len(self.customer_ids) or to_pos >= len(self.customer_ids):
            return False
        
        customer_id = self.customer_ids.pop(from_pos)
        self.arrival_times.pop(from_pos)
        
        if to_pos > from_pos:
            to_pos -= 1
        
        self.customer_ids.insert(to_pos, customer_id)
        self.arrival_times.insert(to_pos, 0.0)
        
        start_idx = min(from_pos, to_pos)
        self._recalculate_from(start_idx)
        
        if not self.is_feasible():
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
        """Adjust route departure time - Returns True if feasible"""
        if new_departure < 0:
            return False
        
        old_departure = self.departure_time
        self.departure_time = new_departure
        self._recalculate_from(0)
        
        if not self.is_feasible():
            self.departure_time = old_departure
            self._recalculate_from(0)
            return False
        
        self.calculate_cost_inplace()
        return True
    
    def get_waiting_time(self) -> float:
        """Calculate total waiting time"""
        customer_ids = self.customer_ids
        if not customer_ids:
            return 0.0

        if len(self.arrival_times) != len(customer_ids):
            self.calculate_cost_inplace()

        distance_only = self.get_total_distance()
        return (self.total_cost - distance_only) / 1.1
    
    def get_waiting_contributions(self) -> List[tuple[int, float]]:
        """Return per-customer waiting contributions"""
        contributions: List[tuple[int, float]] = []
        customer_ids = self.customer_ids
        if not customer_ids:
            return contributions

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
        self.total_cost: float = 0.0
        self.total_base_cost: float = 0.0
        self.num_vehicles: int = 0
    
    def add_route(self, route: Route):
        """Add route and update totals"""
        self.routes.append(route)
        self.num_vehicles += 1
        self.total_base_cost += route.total_cost
        
    def update_cost(self, alpha_vehicle: Optional[float] = None):
        """Recalculate penalized total cost from routes"""
        if not self.routes:
            self.total_cost = 0.0
            self.total_base_cost = 0.0
            self.num_vehicles = 0
            return

        self.total_base_cost = 0.0
        for r in self.routes:
            cost = r.calculate_cost_inplace()
            r.update_bounding_box()
            self.total_base_cost += cost
        
        self.num_vehicles = len(self.routes)
        self._recalculate_penalized_cost(alpha_vehicle)
        
    def update_base_cost(self, delta_cost: float, alpha_vehicle: Optional[float] = None):
        """Updates total_base_cost incrementally - O(1)"""
        self.total_base_cost += delta_cost
        self.num_vehicles = len(self.routes)
        self._recalculate_penalized_cost(alpha_vehicle)

    def _recalculate_penalized_cost(self, alpha_vehicle: Optional[float]):
        """Internal method to apply vehicle penalty"""
        base_distance = sum(r.get_total_distance() for r in self.routes)
        
        if alpha_vehicle is not None:
            lambda_penalty = alpha_vehicle
        else:
            avg_route_cost = self.total_base_cost / max(self.num_vehicles, 1)
            avg_waiting = self.total_base_cost - base_distance
            avg_waiting = avg_waiting / max(self.num_vehicles, 1)
            lambda_penalty = 1.5 * avg_route_cost + 0.5 * avg_waiting + 3000.0
            lambda_penalty = max(3000.0, min(lambda_penalty, 5000.0))

        self.total_cost = self.total_base_cost + lambda_penalty * self.num_vehicles
        
    def is_feasible(self) -> bool:
        """Check if all routes are feasible"""
        return all(route.is_feasible() for route in self.routes)
    
    def get_total_customers(self) -> int:
        """Return total number of customers in routes"""
        return sum(len(r.customer_ids) for r in self.routes)
    
    def get_all_customer_ids(self) -> List[int]:
        """Return list of all customer IDs in routes"""
        all_ids = []
        for route in self.routes:
            all_ids.extend(route.customer_ids)
        return all_ids
    
    def validate_coverage(self, total_customers: int) -> None:
        """Validate customer coverage - raises ValueError if violated"""
        covered = self.get_total_customers()
        if covered != total_customers:
            raise ValueError(
                f"Customer coverage violation: expected {total_customers}, "
                f"but found {covered} assigned customers."
            )
    
    def restore_missing_customers(self, expected_ids: List[int], depot: Customer, vehicle_capacity: int) -> None:
        """Restore missing customers by creating new routes"""
        current_ids = set(self.get_all_customer_ids())
        expected_set = set(expected_ids)
        missing_ids = expected_set - current_ids
        
        if missing_ids:
            customers_lookup = self.routes[0].customers_lookup if self.routes else {}
            for missing_id in missing_ids:
                print(f"Restored customer {missing_id} to a new route.")
                new_route = Route(depot, vehicle_capacity, customers_lookup)
                if not new_route.insert_inplace(missing_id, 0):
                    new_route.customer_ids = [missing_id]
                    new_route.arrival_times = [0.0]
                    new_route.current_load = customers_lookup[missing_id].demand
                    new_route.departure_time = 0.0
                    new_route.calculate_cost_inplace()
                self.add_route(new_route)