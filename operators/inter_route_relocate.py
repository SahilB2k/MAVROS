from core.data_structures import Solution
from core.data_structures import distance
from operators.intra_route_2opt import intra_route_2opt_inplace
from operators.candidate_pruning import build_candidate_list_for_customer, get_candidate_insertion_positions


def inter_route_relocate_inplace(solution: Solution, arrival_buffer=None) -> bool:
    """
    Inter-route relocate using a classic first-improvement local search:
    try moving one customer from one route to another and accept iff the
    global penalised objective (as defined in Solution.update_cost) improves
    and feasibility is preserved.
    """

    routes = solution.routes
    if not routes:
        return False

    # Ensure objective is up to date
    solution.update_cost()
    current_obj = solution.total_cost

    # Build candidate lists for all customers (once, reused)
    all_customers_list = []
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
            
            # Build candidate list for this customer (25 nearest neighbors)
            candidate_neighbors = build_candidate_list_for_customer(customer, all_customers_list, k=25)

            for dst in routes:
                if dst is src:
                    continue

                # Capacity pre-check
                if dst.current_load + customer.demand > dst.vehicle_capacity:
                    continue

                # Candidate pruning: only try positions where predecessor is a nearest neighbor
                candidate_positions = get_candidate_insertion_positions(dst, customer, candidate_neighbors, k=25)
                
                for pos in candidate_positions:
                    # --- backup state ---
                    src_ids_before = list(src.customer_ids)
                    dst_ids_before = list(dst.customer_ids)
                    src_load_before = src.current_load
                    dst_load_before = dst.current_load
                    routes_before = list(solution.routes)

                    # --- apply tentative move ---
                    src.customer_ids.remove(cust_id)
                    dst.customer_ids.insert(pos, cust_id)
                    src.current_load -= customer.demand
                    dst.current_load += customer.demand

                    # If src becomes empty, we will consider removing it
                    remove_src = len(src.customer_ids) == 0
                    if remove_src:
                        solution.routes = [r for r in solution.routes if r is not src]

                    # Recompute objective and feasibility
                    solution.update_cost()
                    feasible = solution.is_feasible()
                    improved = solution.total_cost < current_obj - 1e-6

                    if feasible and improved:
                        # Post-move route re-optimization (2-opt) on affected routes
                        intra_route_2opt_inplace(dst)
                        if src in solution.routes:
                            intra_route_2opt_inplace(src)
                        solution.update_cost()
                        return True

                    # Rollback
                    solution.routes = routes_before
                    src.customer_ids = src_ids_before
                    dst.customer_ids = dst_ids_before
                    src.current_load = src_load_before
                    dst.current_load = dst_load_before
                    solution.update_cost()

    return False
