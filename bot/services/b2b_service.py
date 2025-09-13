"""Betting progression calculator service (Back-to-Back betting strategy)."""

from typing import Dict, List, Tuple
from ..core.logging import LoggerMixin


class B2BService(LoggerMixin):
    """Back-to-back betting progression calculator service."""
    
    def __init__(self) -> None:
        """Initialize B2B service."""
        pass
    
    def format_number(self, n: float) -> str:
        """Format number with appropriate suffixes and decimal precision."""
        if abs(n) >= 1e9:
            return f"{n/1e9:.2f}B"
        if abs(n) >= 1e6:
            return f"{n/1e6:.2f}M"
        if abs(n) >= 1e3:
            return f"{n/1e3:.2f}K"

        # Handle very small numbers with more precision
        if abs(n) < 0.001:
            return f"{n:.8f}"
        elif abs(n) < 0.01:
            return f"{n:.6f}"
        elif abs(n) < 0.1:
            return f"{n:.4f}"
        else:
            return f"{n:.2f}"
    
    async def calculate_bets(
        self,
        base_bet: float,
        multiplier: float,
        increase_percentage: float,
        iterations: int = 15
    ) -> Tuple[List[float], List[float], float]:
        """Calculate betting progression for gambling strategy."""
        try:
            bets = [base_bet]
            net_results = []
            total = 0

            for i in range(1, iterations + 20):
                net_result = bets[-1] * multiplier
                total += net_result
                next_bet = bets[-1] * (1 + increase_percentage / 100)
                
                bets.append(next_bet)
                net_results.append(net_result)

            return bets[:iterations], net_results, total
            
        except Exception as e:
            self.logger.error("Error calculating bet progression", error=str(e), exc_info=True)
            return [], [], 0


# Global B2B service instance
b2b_service = B2BService()