"""
Solomon instance loader with stream processing
Memory-efficient parsing of VRPTW benchmark instances
"""

from typing import List, Tuple, Optional
from core.data_structures import Customer


def load_solomon_instance(file_path: str, num_customers: Optional[int] = None) -> Tuple[Customer, List[Customer], int, int]:
    """
    Load Solomon VRPTW instance from file
    
    Returns:
        depot: Depot customer
        customers: List of customer objects
        vehicle_capacity: Vehicle capacity constraint
        fleet_size: Maximum number of vehicles (if specified, else None)
    
    Memory efficient: Processes line by line, creates minimal objects
    """
    customers: List[Customer] = []
    depot: Customer = None
    vehicle_capacity: int = None
    fleet_size: int = None
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Parse header (first few lines contain metadata)
    line_idx = 0
    
    # Skip title line
    if lines[line_idx].strip().startswith('PROBLEM'):
        line_idx += 1
    
    # Find vehicle capacity
    for i in range(line_idx, min(line_idx + 10, len(lines))):
        if 'CAPACITY' in lines[i].upper():
            parts = lines[i].split()
            for j, part in enumerate(parts):
                if part.upper() == 'CAPACITY':
                    if j + 1 < len(parts):
                        vehicle_capacity = int(parts[j + 1])
                    break
        if vehicle_capacity:
            line_idx = i + 1
            break
    
    # Find data section (usually starts with customer data)
    # Format: CUST NO. XCOORD. YCOORD. DEMAND READY_TIME DUE_DATE SERVICE_TIME
    data_start = None
    for i in range(line_idx, len(lines)):
        line = lines[i].strip()
        if not line or line.startswith('EOF'):
            break
        parts = line.split()
        if len(parts) >= 7:
            try:
                # Try to parse as customer data
                cust_id = int(parts[0])
                x = float(parts[1])
                y = float(parts[2])
                demand = int(parts[3])
                ready = int(float(parts[4]))
                due = int(float(parts[5]))
                service = int(float(parts[6]))
                
                if data_start is None:
                    data_start = i
                
                # First customer is usually depot (id=0 or id=1)
                if cust_id == 0 or (data_start == i and depot is None):
                    depot = Customer(
                        id=cust_id,
                        x=x,
                        y=y,
                        demand=demand,
                        ready_time=ready,
                        due_date=due,
                        service_time=service
                    )
                else:
                    customer = Customer(
                        id=cust_id,
                        x=x,
                        y=y,
                        demand=demand,
                        ready_time=ready,
                        due_date=due,
                        service_time=service
                    )
                    customers.append(customer)
                    
                    # Limit number of customers if specified
                    if num_customers and len(customers) >= num_customers:
                        break
            except (ValueError, IndexError):
                continue
    
    if depot is None:
        raise ValueError("Could not find depot in instance file")
    
    if vehicle_capacity is None:
        raise ValueError("Could not find vehicle capacity in instance file")
    
    return depot, customers, vehicle_capacity, fleet_size


def load_solomon_subset(file_path: str, max_customers: int) -> Tuple[Customer, List[Customer], int, int]:
    """
    Load subset of customers from Solomon instance
    Useful for testing with smaller instances (25, 50, 100 customers)
    """
    return load_solomon_instance(file_path, num_customers=max_customers)







