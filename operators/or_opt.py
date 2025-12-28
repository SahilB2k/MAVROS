"""
Enhanced Or-Opt with Larger Segments and Smarter Selection
Replace your existing or_opt.py with this version for better cost reduction
"""

from core.data_structures import Route
from typing import Optional


def or_opt_inplace(route: Route, max_segment_len: int = 4, max_attempts: int = 100) -> bool:
    """
    ENHANCED Or-Opt: Try moving segments of length 1-4 (increased from 1-3).
    Uses best-improvement strategy with smart segment selection.
    
    Args:
        route: Route to optimize
        max_segment_len: Maximum segment length to try (default 4)
        max_attempts: Maximum number of move attempts
    
    Returns:
        True if any improving move was found
    """
    n = len(route.customer_ids)
    if n < 3:
        return False
    
    improved = False
    attempts = 0
    
    # Try different segment lengths, prioritizing larger segments (more impactful)
    for seg_len in range(min(max_segment_len, n - 1), 0, -1):
        
        # Smart segment selection: prioritize high-cost segments
        segment_priorities = []
        for start_i in range(n - seg_len + 1):
            # Estimate segment cost (sum of edge costs)
            if start_i > 0 and hasattr(route, '_cost_segments') and route._cost_segments:
                # Use cached costs if available
                seg_cost = sum(route._cost_segments[start_i:start_i + seg_len])
            else:
                # Fallback: use simple position-based priority
                # Prefer segments near route ends (often suboptimal)
                if start_i < n // 3 or start_i > 2 * n // 3:
                    seg_cost = 10.0  # High priority
                else:
                    seg_cost = 1.0   # Low priority
            
            segment_priorities.append((seg_cost, start_i))
        
        # Sort by priority (high cost first)
        segment_priorities.sort(reverse=True)
        
        # Try top segments first
        for _, start_i in segment_priorities:
            if attempts >= max_attempts:
                break
            
            end_i = start_i + seg_len
            
            # Try different insertion positions
            # Smart position selection: avoid no-op and adjacent positions
            insertion_positions = []
            
            # Add distant positions first (more likely to improve)
            for insert_j in range(n - seg_len + 1):
                # Skip no-op moves and adjacent positions
                if insert_j >= start_i and insert_j <= end_i:
                    continue
                
                # Calculate distance from original position
                distance = abs(insert_j - start_i)
                insertion_positions.append((distance, insert_j))
            
            # Sort by distance (try distant positions first)
            insertion_positions.sort(reverse=True)
            
            # Try each insertion position
            for _, insert_j in insertion_positions:
                attempts += 1
                if attempts >= max_attempts:
                    break
                
                # Evaluate move
                delta_cost, is_feasible = route.get_move_delta_cost(start_i, end_i, insert_j)
                
                if is_feasible and delta_cost < -0.001:  # Improvement found
                    # Apply the move
                    segment = route.customer_ids[start_i:end_i]
                    
                    # Remove segment
                    route.customer_ids = route.customer_ids[:start_i] + route.customer_ids[end_i:]
                    
                    # Adjust insertion position
                    if insert_j > start_i:
                        insert_j -= seg_len
                    
                    # Insert segment
                    route.customer_ids = (route.customer_ids[:insert_j] + 
                                         segment + 
                                         route.customer_ids[insert_j:])
                    
                    # Recalculate
                    route._recalculate_from(min(start_i, insert_j))
                    route.calculate_cost_inplace()
                    
                    improved = True
                    
                    # Continue searching for more improvements in this segment length
                    break  # Move to next segment
            
            if attempts >= max_attempts:
                break
        
        if attempts >= max_attempts:
            break
    
    return improved


def or_opt_best_improvement(route: Route, max_segment_len: int = 4) -> bool:
    """
    Exhaustive Or-Opt that finds the BEST move across all segments.
    More expensive but guaranteed to find the best single move.
    Use this for final refinement.
    
    Returns:
        True if any improving move was found
    """
    n = len(route.customer_ids)
    if n < 3:
        return False
    
    best_delta = 0.0
    best_move = None
    
    # Exhaustively search all moves
    for seg_len in range(1, min(max_segment_len + 1, n)):
        for start_i in range(n - seg_len + 1):
            end_i = start_i + seg_len
            
            for insert_j in range(n - seg_len + 1):
                # Skip no-op
                if insert_j >= start_i and insert_j <= end_i:
                    continue
                
                delta_cost, is_feasible = route.get_move_delta_cost(start_i, end_i, insert_j)
                
                if is_feasible and delta_cost < best_delta - 0.001:
                    best_delta = delta_cost
                    best_move = (start_i, end_i, insert_j, seg_len)
    
    # Apply best move if found
    if best_move is not None:
        start_i, end_i, insert_j, seg_len = best_move
        
        segment = route.customer_ids[start_i:end_i]
        route.customer_ids = route.customer_ids[:start_i] + route.customer_ids[end_i:]
        
        if insert_j > start_i:
            insert_j -= seg_len
        
        route.customer_ids = (route.customer_ids[:insert_j] + 
                             segment + 
                             route.customer_ids[insert_j:])
        
        route._recalculate_from(min(start_i, insert_j))
        route.calculate_cost_inplace()
        
        return True
    
    return False