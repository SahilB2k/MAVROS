"""
On-the-fly distance calculation utilities
NO CACHING - all calculations are O(1) space
"""

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.data_structures import Customer


def euclidean_distance(c1: 'Customer', c2: 'Customer') -> float:
    """
    Calculate Euclidean distance between two customers
    O(1) space complexity - no caching
    """
    return math.sqrt((c1.x - c2.x)**2 + (c1.y - c2.y)**2)


def travel_time(c1: 'Customer', c2: 'Customer', speed: float = 1.0) -> float:
    """
    Calculate travel time between two customers
    Assumes unit speed by default (distance = time)
    """
    return euclidean_distance(c1, c2) / speed







