"""
MIH-MDS Hybrid Solver with Multi-Pass Improvement and Coverage Validation.
"""

from typing import Optional, List, Tuple, Dict
import copy
from core.data_structures import Customer, Solution
from algorithms.mih import limited_candidate_mih
from algorithms.mds import selective_mds
from operators.route_merge import merge_underfilled_routes

def solve_vrptw(
    depot: Customer,
    customers: List[Customer],
    vehicle_capacity: int,
    candidate_ratio: float = 0.5,
    min_candidates: int = 5,
    max_mds_iterations: int = 150,
    top_n_critical: int = 10,
    random_seed: Optional[int] = None
) -> Solution:
    """
    Standard wrapper for the hybrid solver to satisfy main.py imports.
    """
    # 1. Construction
    solution = limited_candidate_mih(
        depot=depot,
        customers=customers,
        vehicle_capacity=vehicle_capacity,
        candidate_ratio=candidate_ratio,
        min_candidates=min_candidates,
        random_seed=random_seed
    )

    # 2. Improvement
    solution = selective_mds(
        solution=solution,
        max_iterations=max_mds_iterations,
        top_n_critical=top_n_critical
    )

    return solution

def solve_vrptw_with_stats(instance, max_iterations=None, candidate_k=None, alpha_vehicle=1000.0):
    """
    Enhanced Hybrid Solver with debug checkpoints to track customer loss.
    """
    depot = instance.get('depot')
    customers = instance.get('customers')
    vehicle_capacity = instance.get('vehicle_capacity')
    customers_lookup = {c.id: c for c in customers}
    n = len(customers)
    
    # ------------------------------------------------------------
    # PHASE 1: Initial Construction
    # ------------------------------------------------------------
    solution = limited_candidate_mih(
        depot=depot, 
        customers=customers, 
        vehicle_capacity=vehicle_capacity,
        candidate_ratio=0.5, 
        min_candidates=candidate_k if candidate_k else 5, 
        random_seed=42
    )
    
    
    # CHECKPOINT 1: Construction Integrity
    mih_count = sum(len(r.customer_ids) for r in solution.routes)
    print(f"DEBUG [Checkpoint 1]: MIH constructed solution with {mih_count}/{n} customers.")

    # Capture Initial Stats (Raw costs)
    initial_cost_raw = sum(route.total_cost for route in solution.routes)
    initial_vehicles = len(solution.routes)
    
    # ------------------------------------------------------------
    # PHASE 1.5: ADAPTIVE REPAIR (NEW!)
    # Dissolve routes with <5 customers and re-insert
    # ------------------------------------------------------------
    from algorithms.adaptive_repair import adaptive_repair_phase
    
    print(f"\nDEBUG [Phase 1.5]: Running Adaptive Repair...")
    print(f"  Before repair: {len(solution.routes)} routes, cost={solution.total_base_cost:.2f}")
    
    solution = adaptive_repair_phase(
        solution,
        min_customers_per_route=5,
        tolerance=0.05  # 5% time window tolerance
    )
    
    # Verify integrity after repair
    repair_count = sum(len(r.customer_ids) for r in solution.routes)
    if repair_count < mih_count:
        print(f"DEBUG [Warning]: Repair phase dropped {mih_count - repair_count} customers!")
    
    print(f"  After repair: {len(solution.routes)} routes, cost={solution.total_base_cost:.2f}")


    # ------------------------------------------------------------
    # PHASE 2: Multi-Pass Improvement with Aggressive Fleet Reduction
    # ------------------------------------------------------------
    num_passes = 3 if n <= 50 else 5
    # CRITICAL FIX: Increased iteration budget from 120 to 500
    # OR-Tools likely runs 1000s of iterations
    total_iters = max_iterations if max_iterations else (200 if n <= 50 else 500)
    iters_per_pass = total_iters // num_passes

    for pass_num in range(num_passes):
        solution = selective_mds(
            solution=solution,
            max_iterations=iters_per_pass,
            top_n_critical=min(5, len(solution.routes))
        )
        
        # CHECKPOINT 2: MDS Integrity
        mds_count = sum(len(r.customer_ids) for r in solution.routes)
        if mds_count < mih_count:
            print(f"DEBUG [Warning]: MDS pass {pass_num+1} dropped {mih_count - mds_count} customers!")
            mih_count = mds_count # Update tracker

        # ENHANCED: Aggressive route merging after EVERY pass (not just first)
        # This is critical for fleet reduction
        pre_merge_solution = copy.deepcopy(solution)
        pre_merge_vehicles = len(solution.routes)
        try:
            # More aggressive merging: lower threshold as we progress
            threshold = 0.7 - (pass_num * 0.1)  # 0.7, 0.6, 0.5, 0.4, 0.3
            threshold = max(0.3, threshold)  # Don't go below 0.3
            
            solution = merge_underfilled_routes(
                solution=solution, 
                vehicle_capacity=vehicle_capacity,
                customers_lookup=customers_lookup, 
                utilization_threshold=threshold
            )
            merge_count = sum(len(r.customer_ids) for r in solution.routes)
            post_merge_vehicles = len(solution.routes)
            
            print(f"DEBUG [Checkpoint 3.{pass_num}]: Merge pass (threshold={threshold:.1f}) finished with {merge_count}/{n} customers, {post_merge_vehicles} vehicles (was {pre_merge_vehicles}).")
            
            if merge_count < n:
                print("WARNING: Merge reduced customer count; rolling back.")
                solution = pre_merge_solution
            elif not solution.is_feasible():
                print("WARNING: Merge created infeasible solution; rolling back.")
                solution = pre_merge_solution
        except Exception as e:
            print(f"WARNING: Merge failed with exception {e}; rolling back.")
            solution = pre_merge_solution
    
    # ------------------------------------------------------------
    # PHASE 2.5: FORCE-DISSOLVE TO 3 VEHICLES (R-SERIES ONLY)
    # DISABLED: Causes inf cost due to infeasible time windows
    # ------------------------------------------------------------
    # Detect R-series instances
    is_r_series = False
    if hasattr(instance, '__getitem__'):
        instance_file = instance.get('file', '')
        if 'r1' in instance_file.lower() or 'r2' in instance_file.lower():
            is_r_series = True
    
    # DISABLED: Force-dissolve creates infeasible solutions
    # Re-enable when better constraint handling is implemented
    if False and is_r_series and len(solution.routes) > 3:
        print(f"\nDEBUG [Phase 2.5]: Force-Dissolve to 3 vehicles (R-series detected)...")
        print(f"  Current: {len(solution.routes)} vehicles")
        
        from algorithms.force_dissolve import force_dissolve_to_target
        from operators.cross_exchange import cross_exchange
        
        # Force-dissolve to 3 vehicles
        solution = force_dissolve_to_target(
            solution,
            target_vehicles=3,
            time_tolerance=0.10,  # 10% time window relaxation
            capacity_tolerance=0.05  # 5% capacity relaxation
        )
        
        # Apply cross-exchange to balance time window pressure
        print(f"  Applying cross-exchange to balance routes...")
        for _ in range(5):
            cross_exchange(solution, max_attempts=100)
        
        solution.update_cost()
        print(f"  Force-Dissolve complete: {len(solution.routes)} vehicles, cost={solution.total_base_cost:.2f}")


    
    # ------------------------------------------------------------
    # PHASE 3: Controlled Fleet Reduction
    # ------------------------------------------------------------
    print(f"\nDEBUG [Phase 3]: Controlled fleet reduction (limit 5% cost increase/step)...")
    print(f"  Starting: {len(solution.routes)} vehicles, cost={solution.total_base_cost:.2f}")
    
    # Target: Reduce to 12 vehicles (OR-Tools level)
    target_vehicles = 12
    
    while len(solution.routes) > target_vehicles:
        # Find the smallest route
        smallest_route = min(solution.routes, key=lambda r: len(r.customer_ids))
        customers_to_move = list(smallest_route.customer_ids)
        
        if len(customers_to_move) == 0:
            solution.routes.remove(smallest_route)
            continue
        
        print(f"  Attempting to eliminate route with {len(customers_to_move)} customers...")
        
        # Try to redistribute customers
        backup_solution = copy.deepcopy(solution)
        # Ensure backup cost is up to date
        backup_cost = sum(r.total_cost for r in backup_solution.routes) 
        
        success = True
        
        # Remove the route
        solution.routes = [r for r in solution.routes if r is not smallest_route]
        
        # Sort customers to move by due date (hardest first)
        customers_to_move_objs = [customers_lookup[cid] for cid in customers_to_move]
        customers_to_move_objs.sort(key=lambda c: c.due_date)
        
        # For each customer, find BEST feasible insertion
        for customer in customers_to_move_objs:
            cust_id = customer.id
            inserted = False
            best_move = None # (route_idx, pos, cost_increase)
            best_increase = float('inf')
            
            # Use Best-Fit strategy instead of First-Fit
            for r_idx, route in enumerate(solution.routes):
                # Optimization: Skip if capacity definitely violated
                if route.current_load + customer.demand > route.vehicle_capacity:
                    continue
                    
                for pos in range(len(route.customer_ids) + 1):
                    # Use delta cost check which is efficient and includes feasibility
                    delta, feasible = route.get_move_delta_cost_for_external_customer(cust_id, pos)
                    if feasible and delta < best_increase:
                        best_increase = delta
                        best_move = (r_idx, pos)
            
            if best_move:
                r_idx, pos = best_move
                # Execute the best move
                if solution.routes[r_idx].insert_inplace(cust_id, pos):
                    inserted = True
                else:
                    # Should not happen if get_move_delta... said feasible, but safety check
                    inserted = False
            
            if not inserted:
                # Couldn't insert this customer anywhere
                success = False
                break
        
        if success and solution.is_feasible():
            solution.update_cost()
            new_cost = solution.total_base_cost
            cost_increase_pct = ((new_cost - backup_cost) / backup_cost) * 100 if backup_cost > 0 else 0
            
            if cost_increase_pct <= 5.0:
                print(f"  ✓ Eliminated route! Now {len(solution.routes)} vehicles, cost={new_cost:.2f} (+{cost_increase_pct:.2f}%)")
            else:
                # Rollback - too expensive
                solution = backup_solution
                print(f"  ✗ Failed: Cost increase too high (+{cost_increase_pct:.2f}% > 5.0%). Stopping fleet reduction.")
                break
        else:
            # Rollback
            solution = backup_solution
            print(f"  ✗ Failed to eliminate route (infeasible). Stopping fleet reduction.")
            break
            
    print(f"  Final: {len(solution.routes)} vehicles, cost={solution.total_base_cost:.2f}")

    # ------------------------------------------------------------
    # FINAL VALIDATION & STATS
    # ------------------------------------------------------------
    try:
        solution.validate_coverage(n)
    except Exception as e:
        print(f"WARNING: Coverage validation failed: {e}")
    
    total_served = sum(len(r.customer_ids) for r in solution.routes)
    if total_served < n:
        print(f"\n! WARNING: Integrity Check Failed !")
        print(f"! Served: {total_served}/{n} customers. !")
    else:
        print(f"\n* SUCCESS: All {n}/{n} customers served. *")

    
    raw_final_cost = sum(route.total_cost for route in solution.routes)
    
    # CRITICAL FIX: Add vehicle count penalty (like OR-Tools)
    # Prioritize minimizing vehicles, then cost
    vehicle_penalty = len(solution.routes) * 300  # 300 per vehicle
    penalized_cost = raw_final_cost + vehicle_penalty
    
    # Safety check: replace inf with large number for metrics
    if raw_final_cost == float('inf'):
        print(f"WARNING: Final cost is inf, setting to 1,000,000 for metrics")
        raw_final_cost = 1000000.0
        penalized_cost = 1000000.0
    
    if initial_cost_raw == float('inf'):
        initial_cost_raw = 1000000.0
    
    improvement_pct = ((initial_cost_raw - raw_final_cost) / initial_cost_raw * 100) if initial_cost_raw > 0 else 0
    
    print(f"\nFinal Solution:")
    print(f"  Distance Cost: {raw_final_cost:.2f}")
    print(f"  Vehicle Penalty: {vehicle_penalty:.2f} ({len(solution.routes)} vehicles × 300)")
    print(f"  Total Penalized Cost: {penalized_cost:.2f}")
    
    stats = {
        'initial_cost': float(initial_cost_raw),
        'initial_vehicles': int(initial_vehicles),
        'final_cost': float(raw_final_cost),
        'final_vehicles': int(len(solution.routes)),
        'improvement_pct': float(improvement_pct),
        'penalized_cost': float(penalized_cost)
    }
    
    return solution, stats