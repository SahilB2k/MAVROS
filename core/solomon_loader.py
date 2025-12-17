"""
Solomon Instance Loader for VRPTW.
Parses the standard Solomon format (.txt) and creates Customer objects.
"""

from typing import List, Tuple, Optional
from core.data_structures import Customer

def load_solomon_instance(
    file_path: str,
    num_customers: Optional[int] = None
) -> Tuple[Customer, List[Customer], int, int]:
    """
    Loads a Solomon VRPTW instance from a text file.
    
    Returns:
        depot: The central depot customer
        customers: List of delivery customers
        vehicle_capacity: Capacity constraint for all vehicles
        fleet_size: Number of vehicles available (if specified)
    """

    customers: List[Customer] = []
    depot: Optional[Customer] = None
    vehicle_capacity: Optional[int] = None
    fleet_size: Optional[int] = None

    with open(file_path, "r") as f:
        lines = f.readlines()

    i = 0

    # --------------------------------------------------
    # VEHICLE section
    # --------------------------------------------------
    while i < len(lines):
        if lines[i].strip() == "VEHICLE":
            i += 2  # skip header
            parts = lines[i].split()
            if len(parts) >= 2:
                fleet_size = int(parts[0])
                vehicle_capacity = int(parts[1])
            break
        i += 1

    if vehicle_capacity is None:
        raise ValueError("Could not find vehicle capacity section in Solomon file")

    # --------------------------------------------------
    # CUSTOMER DATA HEADER (find "CUST NO.")
    # --------------------------------------------------
    while i < len(lines) and "CUST" not in lines[i]:
        i += 1

    if i >= len(lines):
        raise ValueError("Could not find customer section header")

    i += 1  # Move past the header line to the first data row (usually row 0: Depot)

    first_customer = True

    # --------------------------------------------------
    # READ CUSTOMER ROWS
    # --------------------------------------------------
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        parts = line.split()
        if len(parts) < 7:
            i += 1
            continue

        try:
            cid = int(parts[0])
            x = float(parts[1])
            y = float(parts[2])
            demand = int(parts[3])
            ready = int(parts[4])
            due = int(parts[5])
            service = int(parts[6])
        except ValueError:
            i += 1
            continue

        cust = Customer(
            id=cid,
            x=x,
            y=y,
            demand=demand,
            ready_time=ready,
            due_date=due,
            service_time=service
        )

        # ✅ Solomon rule: The first entry in the data section is the DEPOT
        if first_customer:
            depot = cust
            first_customer = False
        else:
            customers.append(cust)
            # If a subset is requested, stop here
            if num_customers and len(customers) >= num_customers:
                break

        i += 1

    if depot is None:
        raise ValueError("Could not find depot in instance file")

    # Final Debug check to confirm total count
    print(f"DEBUG: Data Loader complete. Found 1 depot and {len(customers)} customers.")

    # Indented return: correctly inside the load_solomon_instance function
    return depot, customers, vehicle_capacity, fleet_size


def load_solomon_subset(file_path: str, max_customers: int):
    """Convenience wrapper for loading partial instances."""
    return load_solomon_instance(file_path, num_customers=max_customers)