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
    
    def get_customer(self, idx: int) -> Customer:
        """Get customer object by index without storing duplicates"""
        return self.customers_lookup[self.customer_ids[idx]]
    
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
        Update self.total_cost and return it
        Cost = travel time + waiting time
        """
        if len(self.customer_ids) == 0:
            self.total_cost = 0.0
            return 0.0
        
        total_cost = 0.0
        
        # Travel from depot to first customer
        if len(self.customer_ids) > 0:
            first_customer = self.get_customer(0)
            total_cost += distance(self.depot, first_customer)
        
        # Travel between customers
        for i in range(len(self.customer_ids) - 1):
            customer1 = self.get_customer(i)
            customer2 = self.get_customer(i + 1)
            total_cost += distance(customer1, customer2)
        
        # Travel from last customer back to depot
        if len(self.customer_ids) > 0:
            last_customer = self.get_customer(len(self.customer_ids) - 1)
            total_cost += distance(last_customer, self.depot)
        
        # Add waiting time
        for i, arrival in enumerate(self.arrival_times):
            customer = self.get_customer(i)
            waiting_time = max(0.0, customer.ready_time - arrival)
            total_cost += waiting_time
        
        self.total_cost = total_cost
        return total_cost
    
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
        """Calculate total waiting time in route"""
        total_waiting = 0.0
        for i, arrival in enumerate(self.arrival_times):
            customer = self.get_customer(i)
            waiting = max(0.0, customer.ready_time - arrival)
            total_waiting += waiting
        return total_waiting
    
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
        """Recalculate total from routes"""
        self.total_cost = sum(r.total_cost for r in self.routes)
    
    def is_feasible(self) -> bool:
        """Check if all routes are feasible"""
        return all(route.is_feasible() for route in self.routes)







