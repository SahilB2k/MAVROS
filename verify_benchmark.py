
from core.solomon_loader import load_solomon_instance
from algorithms.hybrid_solver import solve_vrptw
import time

def verify():
    print("Loading data/c102.txt (100 customers)...")
    depot, customers, vehicle_capacity, fleet_size = load_solomon_instance("data/c102.txt")
    
    print("Solving...")
    start = time.time()
    solution = solve_vrptw(depot, customers, vehicle_capacity)
    duration = time.time() - start
    
    with open("verification_result.txt", "w") as f:
        f.write(f"Total Cost: {solution.total_base_cost:.2f}\n")
        f.write(f"Vehicles: {solution.num_vehicles}\n")
        f.write(f"Time: {duration:.2f}s\n")
        f.write(f"Feasible: {solution.is_feasible()}\n")
        
    print("Verification done. Check verification_result.txt")

if __name__ == "__main__":
    verify()
