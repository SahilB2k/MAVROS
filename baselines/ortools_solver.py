"""
OR-Tools baseline solver for comparison
Runs in separate process to avoid memory conflicts
"""

import time
from typing import Optional, Dict
from pathlib import Path


def solve_with_ortools(instance_file: str, max_customers: Optional[int] = None) -> Dict:
    """
    Solve VRPTW using OR-Tools
    
    Returns statistics dictionary
    """
    try:
        from ortools.constraint_solver import routing_enums_pb2
        from ortools.constraint_solver import pywrapcp
        from core.solomon_loader import load_solomon_instance, load_solomon_subset
    except ImportError:
        raise ImportError("OR-Tools not installed. Install with: pip install ortools")
    
    # Load instance
    if max_customers:
        depot, customers, vehicle_capacity, fleet_size = load_solomon_subset(
            instance_file, max_customers
        )
    else:
        depot, customers, vehicle_capacity, fleet_size = load_solomon_instance(instance_file)
    
    # Create data model for OR-Tools
    num_customers = len(customers)
    num_vehicles = fleet_size if fleet_size else num_customers  # Use all customers as upper bound
    
    # Create distance callback (on-the-fly calculation)
    def distance_callback(from_index, to_index):
        """Returns the distance between the two nodes"""
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        
        if from_node == 0:
            from_customer = depot
        else:
            from_customer = customers[from_node - 1]
        
        if to_node == 0:
            to_customer = depot
        else:
            to_customer = customers[to_node - 1]
        
        # Calculate distance on-the-fly
        import math
        return int(math.sqrt((from_customer.x - to_customer.x)**2 + 
                           (from_customer.y - to_customer.y)**2))
    
    # Create time callback
    def time_callback(from_index, to_index):
        """Returns the travel time between the two nodes"""
        return distance_callback(from_index, to_index)
    
    # Create demand callback
    def demand_callback(from_index):
        """Returns the demand of the node"""
        from_node = manager.IndexToNode(from_index)
        if from_node == 0:
            return 0
        return customers[from_node - 1].demand
    
    # Create routing index manager
    manager = pywrapcp.RoutingIndexManager(num_customers + 1, num_vehicles, 0)
    
    # Create routing model
    routing = pywrapcp.RoutingModel(manager)
    
    # Register callbacks
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    time_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(
        time_callback_index,
        30,  # allow waiting time
        30000,  # maximum time per vehicle
        False,  # Don't force start cumul to zero
        "Time"
    )
    time_dimension = routing.GetDimensionOrDie("Time")
    
    # Add time window constraints
    for customer_idx, customer in enumerate(customers):
        index = manager.NodeToIndex(customer_idx + 1)
        time_dimension.CumulVar(index).SetRange(
            customer.ready_time,
            customer.due_date
        )
    
    # Add capacity constraint
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        [vehicle_capacity] * num_vehicles,  # vehicle maximum capacities
        True,  # start cumul to zero
        "Capacity"
    )
    
    # Set search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 30  # Limit time for comparison
    
    # Solve
    start_time = time.time()
    solution = routing.SolveWithParameters(search_parameters)
    solve_time = time.time() - start_time
    
    if solution:
        # Extract solution
        total_distance = 0
        total_time = 0
        num_vehicles_used = 0
        
        for vehicle_id in range(num_vehicles):
            index = routing.Start(vehicle_id)
            route_distance = 0
            route_customers = []
            
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node != 0:
                    route_customers.append(node)
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(
                    previous_index, index, vehicle_id
                )
            
            if len(route_customers) > 0:
                num_vehicles_used += 1
                total_distance += route_distance
        
        return {
            'cost': total_distance,
            'time': solve_time,
            'num_vehicles': num_vehicles_used,
            'feasible': True
        }
    else:
        return {
            'cost': float('inf'),
            'time': solve_time,
            'num_vehicles': 0,
            'feasible': False
        }







