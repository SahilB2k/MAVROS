"""
Simple test script to verify VRPTW solver works
Creates a small test instance without requiring Solomon file
"""

import math
from core.data_structures import Customer, Solution, Route, distance
from algorithms.mih import limited_candidate_mih
from algorithms.mds import selective_mds
from algorithms.hybrid_solver import solve_vrptw


def create_test_instance():
    """Create a small test VRPTW instance"""
    # Depot at origin
    depot = Customer(
        id=0,
        x=0.0,
        y=0.0,
        demand=0,
        ready_time=0,
        due_date=1000,
        service_time=0
    )
    
    # Create 10 customers in a grid pattern
    customers = []
    for i in range(1, 11):
        x = (i % 5) * 10.0
        y = (i // 5) * 10.0
        customers.append(Customer(
            id=i,
            x=x,
            y=y,
            demand=5,
            ready_time=i * 10,
            due_date=i * 10 + 50,
            service_time=5
        ))
    
    vehicle_capacity = 50
    
    return depot, customers, vehicle_capacity


def test_basic_functionality():
    """Test basic solver functionality"""
    print("Creating test instance...")
    depot, customers, vehicle_capacity = create_test_instance()
    print(f"Created instance with {len(customers)} customers")
    print(f"Vehicle capacity: {vehicle_capacity}\n")
    
    print("Testing MIH-MDS hybrid solver...")
    solution = solve_vrptw(
        depot=depot,
        customers=customers,
        vehicle_capacity=vehicle_capacity,
        random_seed=42
    )
    
    print(f"\nSolution found:")
    print(f"  Total cost: {solution.total_cost:.2f}")
    print(f"  Number of vehicles: {solution.num_vehicles}")
    print(f"  Feasible: {solution.is_feasible()}")
    
    print(f"\nRoutes:")
    for i, route in enumerate(solution.routes):
        print(f"  Route {i+1}: {len(route.customer_ids)} customers")
        print(f"    Customer IDs: {route.customer_ids}")
        print(f"    Cost: {route.total_cost:.2f}")
        print(f"    Load: {route.current_load}/{vehicle_capacity}")
    
    # Verify feasibility
    assert solution.is_feasible(), "Solution should be feasible!"
    print("\n[OK] All tests passed!")


if __name__ == "__main__":
    try:
        test_basic_functionality()
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()







