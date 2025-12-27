from core.data_structures import Solution
from core.data_structures import distance
from operators.intra_route_2opt import intra_route_2opt_inplace
from operators.candidate_pruning import build_candidate_list_for_customer, get_candidate_insertion_positions


def inter_route_relocate_inplace(solution: Solution, arrival_buffer=None, neighbors: dict = None) -> bool:
    """
    Inter-route relocate using a classic first-improvement local search.
    Optimized with precomputed neighbor lists if provided.
    """

    routes = solution.routes
    if not routes:
        return False

    # Ensure objective is up to date
    solution.update_cost()
    current_obj = solution.total_cost

    # Build candidate lists logic (only if neighbors not provided)
    all_customers_list = []
    if neighbors is None:
        for route in routes:
            for cid in route.customer_ids:
                all_customers_list.append(route.customers_lookup[cid])
    
    # Prefer smaller routes as sources, but consider waiting contribution
    routes_sorted = sorted(routes, key=lambda r: len(r.customer_ids))

    for src in routes_sorted:
        if len(src.customer_ids) == 0:
            continue

        # Sort customers by waiting contribution (high to low)
        src.calculate_cost_inplace()
        contribs = src.get_waiting_contributions()
        contribs.sort(key=lambda x: x[1], reverse=True)
        src_ids_ordered = [cid for cid, _ in contribs]

        for cust_id in src_ids_ordered:
            if cust_id not in src.customer_ids:
                continue

            customer = src.get_customer_by_id(cust_id)
            
            # Use precomputed neighbors if available
            if neighbors and cust_id in neighbors:
                candidate_neighbors = neighbors[cust_id]
            else:
                candidate_neighbors = build_candidate_list_for_customer(customer, all_customers_list, k=25)

            for dst in routes:
                if dst is src:
                    continue
                
                # Geometric Pruning
                if not src.overlaps_with(dst, buffer=20.0):
                    continue

                # Capacity pre-check
                if dst.current_load + customer.demand > dst.vehicle_capacity:
                    continue

                # Candidate pruning: only try positions where predecessor is a nearest neighbor
                candidate_positions = get_candidate_insertion_positions(dst, customer, candidate_neighbors, k=25)
                
                for pos in candidate_positions:
                    # --- ATOMIC CHECK: Verify feasibility BEFORE any modifications ---
                    delta_cost, is_feasible = dst.get_move_delta_cost_for_external_customer(cust_id, pos)
                    if not is_feasible:
                        continue  # Skip this position, try next

                    # --- backup state ---
                    src_ids_before = list(src.customer_ids)
                    dst_ids_before = list(dst.customer_ids)
                    src_arr_before = list(src.arrival_times)
                    dst_arr_before = list(dst.arrival_times)
                    src_load_before = src.current_load
                    dst_load_before = dst.current_load
                    routes_before = list(solution.routes)

                    # --- ATOMIC PATTERN: Insert FIRST, then remove ---
                    # Step 1: Insert into dst route (this is safe - if it fails, nothing is modified)
                    if not dst.insert_inplace(cust_id, pos):
                        # Insertion failed despite feasibility check - skip this position
                        continue
                    
                    # Step 2: Only if insertion succeeded, remove from src
                    src_idx = src.customer_ids.index(cust_id)
                    src.customer_ids.pop(src_idx)
                    src.arrival_times.pop(src_idx)
                    src.current_load -= customer.demand
                    src._recalculate_from(max(0, src_idx - 1))
                    src.calculate_cost_inplace()

                    # Step 3: If src becomes empty, remove route
                    remove_src = len(src.customer_ids) == 0
                    if remove_src:
                        solution.routes = [r for r in solution.routes if r is not src]

                    # Step 4: Recompute objective and verify improvement
                    solution.update_cost()
                    feasible_move = solution.is_feasible()
                    improved = solution.total_cost < current_obj - 1e-6

                    if feasible_move and improved:
                        # Post-move optimization
                        intra_route_2opt_inplace(dst)
                        if src in solution.routes:
                            intra_route_2opt_inplace(src)
                        solution.update_cost()
                        return True

                    # Not improved or infeasible -> rollback
                    solution.routes = routes_before
                    src.customer_ids = src_ids_before
                    dst.customer_ids = dst_ids_before
                    src.arrival_times = src_arr_before
                    dst.arrival_times = dst_arr_before
                    src.current_load = src_load_before
                    dst.current_load = dst_load_before
                    src._recalculate_from(0)
                    dst._recalculate_from(0)
                    src.calculate_cost_inplace()
                    dst.calculate_cost_inplace()
                    solution.update_cost()

    return False
