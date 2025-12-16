"""
Selective Multi-Directional Search (MDS)
Now includes INTER-ROUTE vehicle reduction
"""

from typing import List
from core.data_structures import Solution, Route
from evaluation.route_analyzer import identify_critical_route_indices
from operators.inter_route_relocate import inter_route_relocate_inplace
from operators.intra_route_2opt import intra_route_2opt_inplace
from operators.or_opt import or_opt_inplace
from operators.temporal_shift import temporal_shift_operator_inplace
from operators.swap import swap_operator_inplace
from operators.relocate import relocate_operator_inplace
from operators.lns_destroy_repair import lns_destroy_repair


MAX_MDS_ITERATIONS = 50
TOP_N_CRITICAL_ROUTES = 5
MAX_ROUTE_SIZE = 50
EARLY_TERMINATION_THRESHOLD = 10


def selective_mds(solution: Solution,
                  max_iterations: int = MAX_MDS_ITERATIONS,
                  top_n_critical: int = TOP_N_CRITICAL_ROUTES,
                  early_termination: int = EARLY_TERMINATION_THRESHOLD) -> Solution:
    """
    Two-phase MDS:
      Phase 1 (feasibility / vehicle reduction):
        - aggressively applies inter-route relocations to shrink the fleet,
          guided by the penalised objective in Solution.update_cost().
      Phase 2 (cost refinement):
        - focuses on temporal shift, swap and relocate on critical routes.
    """

    max_route_size = max((len(r.customer_ids) for r in solution.routes), default=0)
    buffer_size = max(MAX_ROUTE_SIZE, max_route_size + 10)
    temp_arrival_buffer = [0.0] * buffer_size

    iteration = 0
    no_improvement = 0

    # --- Phase 1: feasibility / vehicle-count focused ---
    while iteration < max_iterations and no_improvement < early_termination:
        iteration += 1
        improved = False

        if inter_route_relocate_inplace(solution, temp_arrival_buffer):
            improved = True

        if improved:
            no_improvement = 0
        else:
            no_improvement += 1

        # stop early if we cannot reduce vehicles any further
        if not improved:
            break

    solution.update_cost()

    # --- Global escape: one lightweight LNS destroy-repair before refinement ---
    if lns_destroy_repair(solution, removal_fraction=0.15, fixed_remove_count=12, random_seed=42):
        solution.update_cost()

    # --- Phase 2: route-level cost refinement ---
    no_improvement = 0
    while iteration < max_iterations and no_improvement < early_termination:
        iteration += 1
        improved = False

        critical_indices = identify_critical_route_indices(
            solution, top_n=min(top_n_critical, len(solution.routes))
        )

        for route_idx in critical_indices:
            route = solution.routes[route_idx]

            # 0. Intra-route 2-opt (polish ordering under time windows)
            if intra_route_2opt_inplace(route):
                solution.update_cost()
                improved = True
                continue

            # 0.5. Or-Opt (1-3 segment relocate) for finer path cleanup
            if or_opt_inplace(route, max_segment_len=3):
                solution.update_cost()
                improved = True
                continue

            # 1. Temporal shift
            if temporal_shift_operator_inplace(route, temp_arrival_buffer):
                solution.update_cost()
                improved = True
                continue

            # 2. Swap
            if swap_operator_inplace(route, temp_arrival_buffer, max_swaps=20):
                solution.update_cost()
                improved = True
                continue

            # 3. Intra-route relocate
            if relocate_operator_inplace(route, temp_arrival_buffer, max_relocations=20):
                solution.update_cost()
                improved = True

        if improved:
            no_improvement = 0
        else:
            no_improvement += 1

    solution.update_cost()
    return solution
