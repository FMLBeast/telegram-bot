"""Mines casino game multiplier calculator service."""

import math
from typing import Dict, List, Tuple, Optional
from ..core.logging import LoggerMixin


class MinesService(LoggerMixin):
    """Mines casino game multiplier calculator service."""
    
    def __init__(self) -> None:
        """Initialize Mines service."""
        pass
    
    def combination(self, n: int, k: int) -> int:
        """Calculate combination (n choose k)."""
        return math.comb(n, k)
    
    async def calculate_multiplier_from_mines_diamonds(
        self, 
        mines: int, 
        diamonds: int
    ) -> Optional[Dict]:
        """Calculate multiplier and winning chance from mines and diamonds count."""
        try:
            if mines + diamonds > 25 or mines <= 0 or diamonds <= 0:
                return None
            
            n = 25  # Total tiles
            x = 25 - mines  # Safe tiles
            
            first = self.combination(n, diamonds)
            second = self.combination(x, diamonds)
            multiplier = 0.99 * (first / second)
            multiplier = round(multiplier, 2)
            
            winning_chance = round(99 / multiplier, 5)
            
            # Calculate close multipliers
            close_multipliers = []
            for i in range(max(1, mines - 1), min(25, mines + 2)):
                for j in range(max(1, diamonds - 1), min(25 - i + 1, diamonds + 2)):
                    if i == mines and j == diamonds:
                        continue
                    close_result = self.combination(25, j) / self.combination(25 - i, j)
                    close_result = round(0.99 * close_result, 2)
                    close_multipliers.append((i, j, close_result))
            
            close_multipliers.sort(key=lambda x: abs(x[2] - multiplier))
            
            return {
                "mines": mines,
                "diamonds": diamonds,
                "multiplier": multiplier,
                "winning_chance": winning_chance,
                "close_multipliers": close_multipliers[:4]
            }
            
        except Exception as e:
            self.logger.error("Error calculating multiplier from mines/diamonds", 
                            mines=mines, diamonds=diamonds, error=str(e), exc_info=True)
            return None
    
    async def find_combinations_for_multiplier(
        self, 
        target_multiplier: float
    ) -> Optional[List[Tuple[int, int, float]]]:
        """Find mines/diamonds combinations that achieve target multiplier."""
        try:
            multipliers = []
            
            for mines in range(1, 25):
                for diamonds in range(1, 25 - mines + 1):
                    n = 25
                    x = 25 - mines
                    first = self.combination(n, diamonds)
                    second = self.combination(x, diamonds)
                    result = 0.99 * (first / second)
                    result = round(result, 2)
                    multipliers.append((mines, diamonds, result))
            
            # Sort by closeness to target
            multipliers.sort(key=lambda x: abs(x[2] - target_multiplier))
            
            return multipliers[:5]
            
        except Exception as e:
            self.logger.error("Error finding combinations for multiplier", 
                            target_multiplier=target_multiplier, error=str(e), exc_info=True)
            return None


# Global mines service instance
mines_service = MinesService()