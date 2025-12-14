from typing import List, Tuple, Optional
from core.data_structures import Customer


def load_solomon_instance(
    file_path: str,
    num_customers: Optional[int] = None
) -> Tuple[Customer, List[Customer], int, int]:

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
            fleet_size = int(parts[0])
            vehicle_capacity = int(parts[1])
            break
        i += 1

    if vehicle_capacity is None:
        raise ValueError("Could not find vehicle capacity")

    # --------------------------------------------------
    # CUSTOMER DATA HEADER (CUST NO.)
    # --------------------------------------------------
    while i < len(lines) and "CUST" not in lines[i]:
        i += 1

    if i >= len(lines):
        raise ValueError("Could not find customer section")

    i += 1  # move to first data row

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

        # ✅ Solomon rule: FIRST ROW IS DEPOT
        if first_customer:
            depot = cust
            first_customer = False
        else:
            customers.append(cust)
            if num_customers and len(customers) >= num_customers:
                break

        i += 1

    if depot is None:
        raise ValueError("Could not find depot in instance file")

    return depot, customers, vehicle_capacity, fleet_size


def load_solomon_subset(file_path: str, max_customers: int):
    return load_solomon_instance(file_path, num_customers=max_customers)
