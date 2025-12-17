"""
Intra-route Or-Opt (1-3 customer segment relocate) - FIRST IMPROVEMENT.

Moves a short segment within the same route to another position,
keeping feasibility. Objective: distance + waiting.

PERFORMANCE FIX: Uses incremental cost evaluation (O(N^2) instead of O(N^3))
GEODESIC PRUNING: Only checks insertion positions where predecessor is among
10 nearest neighbors of segment's first customer.
"""

from core.data_structures import Route, distance


def _build_nearest_neighbors(route: Route, k: int = 20) -> dict:
    """
    Build nearest neighbor lookup for each customer in the route.
    Returns dict mapping customer_id -> list of k nearest neighbor customer_ids (sorted by distance).
    """
    from core.data_structures import Customer
    
    customer_ids = route.customer_ids
    customers_lookup = route.customers_lookup
    depot = route.depot
    
    # Get all customers in route plus depot
    all_customers = [depot] + [customers_lookup[cid] for cid in customer_ids]
    
    neighbors = {}
    
    # For each customer in the route, find k nearest neighbors
    for cid in customer_ids:
        customer = customers_lookup[cid]
        distances = []
        
        for other in all_customers:
            if other.id == customer.id:
                continue
            dist = distance(customer, other)
            distances.append((other.id, dist))
        
        # Sort by distance and take k nearest
        distances.sort(key=lambda x: x[1])
        neighbors[cid] = [other_id for other_id, _ in distances[:k]]
    
    return neighbors


def or_opt_inplace(route: Route, max_segment_len: int = 3, max_trials: int = 100) -> bool:
    """
    Apply a FIRST-IMPROVEMENT or-opt (segment relocate) within a route.
    Uses geodesic pruning: only evaluates positions where predecessor is among
    20 nearest neighbors of segment's first customer.
    
    Args:
        route: Route to modify in place.
        max_segment_len: maximum segment length to move (1..3 typical).
        max_trials: Maximum number of insertion positions to check per segment (default 100).

    Returns:
        True if an improving move was applied; False otherwise.
    """
    n = len(route.customer_ids)
    if n < 3:
        return False

    # Ensure cost/schedule are in sync and use route.total_cost as objective
    route.calculate_cost_inplace() # O(N)
    base_obj = route.total_cost

    # Build nearest neighbor lookup for geodesic pruning (increased from 10 to 20)
    neighbors = _build_nearest_neighbors(route, k=20)

    # Try segment lengths 1..max_segment_len
    for seg_len in range(1, min(max_segment_len, n) + 1):
        for start in range(0, n - seg_len + 1):
            end = start + seg_len 	# exclusive
            segment = route.customer_ids[start:end]
            
            # Get first customer in segment for nearest neighbor lookup
            seg_first_id = segment[0]
            seg_first_customer = route.customers_lookup[seg_first_id]
            candidate_neighbors = neighbors.get(seg_first_id, [])
            
            # Track trials to enforce max_trials limit
            trials = 0
            
            # Geodesic pruning: only check positions where predecessor is a nearest neighbor
            for insert_pos in range(0, n - seg_len + 1):
                # Check for no-op moves
                if insert_pos == start or insert_pos == end:
                    continue
                
                # Enforce max_trials limit
                if trials >= max_trials:
                    break
                
                # Determine predecessor at insertion position
                # Need to consider the route WITHOUT the segment for accurate predecessor
                is_depot_pred = False
                if insert_pos == 0:
                    is_depot_pred = True
                else:
                    # Adjust for segment removal when calculating predecessor
                    if insert_pos <= start:
                        # Insertion before segment removal point
                        pred_idx = insert_pos - 1
                    else:
                        # Insertion after segment removal point
                        pred_idx = insert_pos - seg_len - 1
                    
                    if pred_idx < 0:
                        is_depot_pred = True
                    else:
                        pred_id = route.customer_ids[pred_idx]
                
                # Geodesic pruning: only check if predecessor is depot or a nearest neighbor
                if not is_depot_pred and pred_id not in candidate_neighbors:
                    continue
                
                trials += 1
                
                # --- CRITICAL PERFORMANCE STEP ---
                # Check cost and feasibility without modifying the route list
                delta_cost, is_feasible = route.get_move_delta_cost(start, end, insert_pos) # O(N)

                if is_feasible and (base_obj + delta_cost < base_obj - 1e-6):
                    # --- Execute the Improving Move (The only time we modify the list) ---
                    
                    # 1. Physical Removal
                    del route.customer_ids[start:end]
                    
                    # 2. Adjust insertion position due to removal
                    if insert_pos > start:
                        insert_pos -= seg_len
                    
                    # 3. Physical Insertion
                    route.customer_ids[insert_pos:insert_pos] = segment
                    
                    # 4. Finalize schedule and cost
                    route.calculate_cost_inplace() # O(N)
                    
                    return True # First improvement found and applied

    return False