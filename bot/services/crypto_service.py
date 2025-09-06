"""Cryptocurrency tracking and betting service."""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from enum import Enum

from ..core.database import Base, db_manager
from ..core.logging import LoggerMixin
from ..core.exceptions import APIError


class BetStatus(str, Enum):
    """Bet status enumeration."""
    PENDING = "pending"
    WON = "won" 
    LOST = "lost"
    CANCELLED = "cancelled"


class CryptoBet(Base):
    """Cryptocurrency betting model."""
    
    __tablename__ = "crypto_bets"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    chat_id = Column(Integer, nullable=False)
    symbol = Column(String(20), nullable=False)  # BTC, ETH, etc.
    bet_type = Column(String(20), nullable=False)  # up, down, exact
    target_price = Column(Float, nullable=True)  # For exact predictions
    current_price = Column(Float, nullable=False)
    amount = Column(Float, default=10.0)  # Virtual amount
    multiplier = Column(Float, default=2.0)
    duration_minutes = Column(Integer, default=60)
    expires_at = Column(DateTime, nullable=False)
    final_price = Column(Float, nullable=True)
    status = Column(String(20), default=BetStatus.PENDING)
    payout = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)


class UserBalance(Base):
    """User virtual balance model."""
    
    __tablename__ = "user_balances"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)
    balance = Column(Float, default=1000.0)  # Starting virtual balance
    total_wagered = Column(Float, default=0.0)
    total_won = Column(Float, default=0.0)
    total_lost = Column(Float, default=0.0)
    win_streak = Column(Integer, default=0)
    best_streak = Column(Integer, default=0)
    total_bets = Column(Integer, default=0)
    last_daily_bonus = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CryptoPrice(Base):
    """Cryptocurrency price tracking model."""
    
    __tablename__ = "crypto_prices"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    change_24h = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)
    volume_24h = Column(Float, nullable=True)
    market_cap = Column(Float, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)


class CryptoService(LoggerMixin):
    """Service for cryptocurrency betting and price tracking."""
    
    def __init__(self) -> None:
        """Initialize the crypto service."""
        self.supported_coins = {
            "BTC": "Bitcoin",
            "ETH": "Ethereum", 
            "BNB": "Binance Coin",
            "ADA": "Cardano",
            "DOT": "Polkadot",
            "LINK": "Chainlink",
            "LTC": "Litecoin",
            "BCH": "Bitcoin Cash",
            "XRP": "Ripple",
            "DOGE": "Dogecoin"
        }
        self.price_cache = {}
        self.cache_expiry = {}
        self.logger.info("Crypto service initialized", supported_coins=len(self.supported_coins))
    
    async def get_user_balance(self, user_id: int) -> Dict[str, Any]:
        """Get user's virtual balance and stats."""
        async with db_manager.get_session() as session:
            stmt = select(UserBalance).where(UserBalance.user_id == user_id)
            result = await session.execute(stmt)
            balance = result.scalar_one_or_none()
            
            if not balance:
                # Create new user balance
                balance = UserBalance(user_id=user_id)
                session.add(balance)
                await session.flush()
                self.logger.info("Created new user balance", user_id=user_id)
            
            return {
                "balance": balance.balance,
                "total_wagered": balance.total_wagered,
                "total_won": balance.total_won,
                "total_lost": balance.total_lost,
                "win_streak": balance.win_streak,
                "best_streak": balance.best_streak,
                "total_bets": balance.total_bets,
                "win_rate": (balance.total_won / max(balance.total_wagered, 1)) * 100,
                "profit_loss": balance.total_won - balance.total_lost
            }
    
    async def get_crypto_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current cryptocurrency price from CoinGecko API."""
        symbol = symbol.upper()
        
        if symbol not in self.supported_coins:
            return None
        
        # Check cache
        now = datetime.utcnow()
        if symbol in self.cache_expiry and now < self.cache_expiry[symbol]:
            return self.price_cache.get(symbol)
        
        try:
            # Map symbols to CoinGecko IDs
            symbol_map = {
                "BTC": "bitcoin",
                "ETH": "ethereum", 
                "BNB": "binancecoin",
                "ADA": "cardano",
                "DOT": "polkadot",
                "LINK": "chainlink",
                "LTC": "litecoin",
                "BCH": "bitcoin-cash",
                "XRP": "ripple",
                "DOGE": "dogecoin"
            }
            
            coin_id = symbol_map.get(symbol)
            if not coin_id:
                # Fallback to mock for unsupported coins
                return await self._get_mock_price(symbol, now)
            
            import aiohttp
            
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_market_cap": "true",
                "include_24hr_vol": "true"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        coin_data = data.get(coin_id, {})
                        
                        if coin_data:
                            current_price = coin_data.get("usd", 0.0)
                            change_percent = coin_data.get("usd_24h_change", 0.0)
                            volume_24h = coin_data.get("usd_24h_vol", 0)
                            market_cap = coin_data.get("usd_market_cap", 0)
                            
                            # Calculate change_24h from percentage
                            change_24h = (change_percent / 100) * current_price if current_price else 0
                            
                            price_data = {
                                "symbol": symbol,
                                "name": self.supported_coins[symbol],
                                "price": round(current_price, 8),
                                "change_24h": round(change_24h, 8),
                                "change_percent": round(change_percent, 2),
                                "volume_24h": volume_24h,
                                "market_cap": market_cap,
                                "last_updated": now,
                                "source": "coingecko"
                            }
                            
                            # Cache the result for 2 minutes
                            self.price_cache[symbol] = price_data
                            self.cache_expiry[symbol] = now + timedelta(minutes=2)
                            
                            # Store in database
                            async with db_manager.get_session() as session:
                                crypto_price = CryptoPrice(
                                    symbol=symbol,
                                    price=current_price,
                                    change_24h=change_24h,
                                    change_percent=change_percent,
                                    volume_24h=volume_24h,
                                    market_cap=market_cap
                                )
                                session.add(crypto_price)
                            
                            self.logger.info("Fetched real crypto price", symbol=symbol, price=current_price, source="coingecko")
                            return price_data
                    
                    # If API fails, fall back to mock data
                    self.logger.warning("CoinGecko API failed, using mock data", symbol=symbol, status=response.status)
                    return await self._get_mock_price(symbol, now)
                    
        except Exception as e:
            self.logger.error("Error fetching crypto price", symbol=symbol, error=str(e))
            # Fall back to mock data on any error
            return await self._get_mock_price(symbol, now)
    
    async def _get_mock_price(self, symbol: str, now: datetime) -> Dict[str, Any]:
        """Fallback mock price data when API is unavailable."""
        base_prices = {
            "BTC": 65000.0,
            "ETH": 3200.0,
            "BNB": 580.0,
            "ADA": 0.65,
            "DOT": 28.5,
            "LINK": 25.8,
            "LTC": 180.0,
            "BCH": 420.0,
            "XRP": 0.88,
            "DOGE": 0.15
        }
        
        # Add some realistic volatility
        import random
        base_price = base_prices[symbol]
        volatility = random.uniform(-0.05, 0.05)  # ±5% random change
        current_price = base_price * (1 + volatility)
        
        change_24h = random.uniform(-0.10, 0.10) * base_price
        change_percent = (change_24h / base_price) * 100
        
        price_data = {
            "symbol": symbol,
            "name": self.supported_coins[symbol],
            "price": round(current_price, 8),
            "change_24h": round(change_24h, 8),
            "change_percent": round(change_percent, 2),
            "volume_24h": random.uniform(1000000, 50000000000),
            "market_cap": current_price * random.uniform(10000000, 1000000000),
            "last_updated": now,
            "source": "mock"
        }
        
        # Cache for 60 seconds
        self.price_cache[symbol] = price_data
        self.cache_expiry[symbol] = now + timedelta(seconds=60)
        
        # Store in database
        async with db_manager.get_session() as session:
            crypto_price = CryptoPrice(
                symbol=symbol,
                price=current_price,
                change_24h=change_24h,
                change_percent=change_percent,
                volume_24h=price_data["volume_24h"],
                market_cap=price_data["market_cap"]
            )
            session.add(crypto_price)
        
        return price_data
    
    async def place_bet(
        self,
        user_id: int,
        chat_id: int,
        symbol: str,
        bet_type: str,
        amount: float,
        duration_minutes: int = 60,
        target_price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Place a cryptocurrency bet."""
        symbol = symbol.upper()
        
        if symbol not in self.supported_coins:
            raise APIError(f"Unsupported cryptocurrency: {symbol}")
        
        if bet_type not in ["up", "down", "exact"]:
            raise APIError("Bet type must be 'up', 'down', or 'exact'")
        
        if amount <= 0:
            raise APIError("Bet amount must be positive")
        
        if bet_type == "exact" and target_price is None:
            raise APIError("Target price required for exact predictions")
        
        # Check user balance
        user_balance = await self.get_user_balance(user_id)
        if user_balance["balance"] < amount:
            raise APIError(f"Insufficient balance. You have ${user_balance['balance']:.2f}")
        
        # Get current price
        price_data = await self.get_crypto_price(symbol)
        if not price_data:
            raise APIError(f"Unable to get price for {symbol}")
        
        current_price = price_data["price"]
        expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
        
        # Calculate multiplier based on bet type and duration
        base_multiplier = 2.0
        if bet_type == "exact":
            base_multiplier = 10.0  # Higher risk, higher reward
        elif duration_minutes <= 15:
            base_multiplier = 1.5  # Short-term bets have lower multiplier
        elif duration_minutes >= 240:
            base_multiplier = 3.0  # Long-term bets have higher multiplier
        
        async with db_manager.get_session() as session:
            # Deduct balance
            stmt = update(UserBalance).where(
                UserBalance.user_id == user_id
            ).values(
                balance=UserBalance.balance - amount,
                total_wagered=UserBalance.total_wagered + amount,
                total_bets=UserBalance.total_bets + 1
            )
            await session.execute(stmt)
            
            # Create bet
            bet = CryptoBet(
                user_id=user_id,
                chat_id=chat_id,
                symbol=symbol,
                bet_type=bet_type,
                target_price=target_price,
                current_price=current_price,
                amount=amount,
                multiplier=base_multiplier,
                duration_minutes=duration_minutes,
                expires_at=expires_at
            )
            session.add(bet)
            await session.flush()
            
            self.logger.info(
                "Bet placed",
                user_id=user_id,
                bet_id=bet.id,
                symbol=symbol,
                bet_type=bet_type,
                amount=amount,
                current_price=current_price
            )
            
            return {
                "bet_id": bet.id,
                "symbol": symbol,
                "bet_type": bet_type,
                "amount": amount,
                "current_price": current_price,
                "target_price": target_price,
                "multiplier": base_multiplier,
                "expires_at": expires_at,
                "potential_payout": amount * base_multiplier
            }
    
    async def get_user_bets(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get user's bets."""
        async with db_manager.get_session() as session:
            stmt = select(CryptoBet).where(CryptoBet.user_id == user_id)
            
            if status:
                stmt = stmt.where(CryptoBet.status == status)
            
            stmt = stmt.order_by(CryptoBet.created_at.desc()).limit(limit)
            
            result = await session.execute(stmt)
            bets = result.scalars().all()
            
            return [
                {
                    "id": bet.id,
                    "symbol": bet.symbol,
                    "bet_type": bet.bet_type,
                    "amount": bet.amount,
                    "current_price": bet.current_price,
                    "target_price": bet.target_price,
                    "final_price": bet.final_price,
                    "multiplier": bet.multiplier,
                    "status": bet.status,
                    "payout": bet.payout,
                    "expires_at": bet.expires_at,
                    "created_at": bet.created_at,
                    "resolved_at": bet.resolved_at
                }
                for bet in bets
            ]
    
    async def resolve_bet(self, bet_id: int) -> Optional[Dict[str, Any]]:
        """Resolve a bet by checking final price."""
        async with db_manager.get_session() as session:
            stmt = select(CryptoBet).where(
                CryptoBet.id == bet_id,
                CryptoBet.status == BetStatus.PENDING
            )
            result = await session.execute(stmt)
            bet = result.scalar_one_or_none()
            
            if not bet:
                return None
            
            # Check if bet has expired
            if datetime.utcnow() < bet.expires_at:
                return None  # Not expired yet
            
            # Get current price
            price_data = await self.get_crypto_price(bet.symbol)
            if not price_data:
                return None
            
            final_price = price_data["price"]
            won = False
            
            # Determine if bet won
            if bet.bet_type == "up":
                won = final_price > bet.current_price
            elif bet.bet_type == "down":
                won = final_price < bet.current_price
            elif bet.bet_type == "exact":
                # Allow 1% margin for exact predictions
                margin = bet.target_price * 0.01
                won = abs(final_price - bet.target_price) <= margin
            
            status = BetStatus.WON if won else BetStatus.LOST
            payout = (bet.amount * bet.multiplier) if won else 0.0
            
            # Update bet
            stmt = update(CryptoBet).where(
                CryptoBet.id == bet_id
            ).values(
                final_price=final_price,
                status=status,
                payout=payout,
                resolved_at=datetime.utcnow()
            )
            await session.execute(stmt)
            
            # Update user balance
            if won:
                stmt = update(UserBalance).where(
                    UserBalance.user_id == bet.user_id
                ).values(
                    balance=UserBalance.balance + payout,
                    total_won=UserBalance.total_won + payout,
                    win_streak=UserBalance.win_streak + 1,
                    best_streak=func.greatest(UserBalance.best_streak, UserBalance.win_streak + 1)
                )
            else:
                stmt = update(UserBalance).where(
                    UserBalance.user_id == bet.user_id
                ).values(
                    total_lost=UserBalance.total_lost + bet.amount,
                    win_streak=0
                )
            
            await session.execute(stmt)
            
            self.logger.info(
                "Bet resolved",
                bet_id=bet_id,
                user_id=bet.user_id,
                symbol=bet.symbol,
                won=won,
                payout=payout
            )
            
            return {
                "bet_id": bet_id,
                "symbol": bet.symbol,
                "bet_type": bet.bet_type,
                "amount": bet.amount,
                "current_price": bet.current_price,
                "final_price": final_price,
                "won": won,
                "payout": payout,
                "status": status
            }
    
    async def get_pending_bets(self) -> List[Dict[str, Any]]:
        """Get all pending bets for resolution."""
        async with db_manager.get_session() as session:
            stmt = select(CryptoBet).where(
                CryptoBet.status == BetStatus.PENDING,
                CryptoBet.expires_at <= datetime.utcnow()
            )
            result = await session.execute(stmt)
            bets = result.scalars().all()
            
            return [
                {
                    "id": bet.id,
                    "user_id": bet.user_id,
                    "chat_id": bet.chat_id,
                    "symbol": bet.symbol,
                    "bet_type": bet.bet_type,
                    "current_price": bet.current_price,
                    "target_price": bet.target_price,
                    "amount": bet.amount,
                    "multiplier": bet.multiplier,
                    "expires_at": bet.expires_at
                }
                for bet in bets
            ]
    
    async def give_daily_bonus(self, user_id: int) -> Optional[float]:
        """Give daily bonus to user if eligible."""
        async with db_manager.get_session() as session:
            stmt = select(UserBalance).where(UserBalance.user_id == user_id)
            result = await session.execute(stmt)
            balance = result.scalar_one_or_none()
            
            if not balance:
                # Create new balance with bonus
                balance = UserBalance(user_id=user_id, last_daily_bonus=datetime.utcnow())
                session.add(balance)
                return 1000.0  # Starting bonus
            
            # Check if already claimed today
            if balance.last_daily_bonus:
                last_bonus = balance.last_daily_bonus.date()
                today = datetime.utcnow().date()
                
                if last_bonus >= today:
                    return None  # Already claimed today
            
            # Give bonus based on current balance
            bonus_amount = 100.0
            if balance.balance < 50:
                bonus_amount = 200.0  # Bigger bonus if low balance
            elif balance.balance > 5000:
                bonus_amount = 50.0   # Smaller bonus if high balance
            
            stmt = update(UserBalance).where(
                UserBalance.user_id == user_id
            ).values(
                balance=UserBalance.balance + bonus_amount,
                last_daily_bonus=datetime.utcnow()
            )
            await session.execute(stmt)
            
            self.logger.info("Daily bonus given", user_id=user_id, amount=bonus_amount)
            return bonus_amount
    
    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by balance."""
        async with db_manager.get_session() as session:
            stmt = select(UserBalance).order_by(
                UserBalance.balance.desc()
            ).limit(limit)
            
            result = await session.execute(stmt)
            balances = result.scalars().all()
            
            return [
                {
                    "user_id": balance.user_id,
                    "balance": balance.balance,
                    "total_won": balance.total_won,
                    "win_streak": balance.win_streak,
                    "best_streak": balance.best_streak,
                    "total_bets": balance.total_bets
                }
                for balance in balances
            ]
    
    async def convert_crypto(self, from_symbol: str, to_symbol: str, amount: float) -> Optional[Dict]:
        """Convert between cryptocurrencies or to fiat currencies."""
        try:
            from_symbol = from_symbol.upper()
            to_symbol = to_symbol.upper()
            
            # Get prices for both symbols
            from_price_data = await self.get_crypto_price(from_symbol)
            
            if not from_price_data:
                return None
            
            # Handle fiat conversions
            fiat_currencies = {
                "USD": 1.0,
                "EUR": 0.92,
                "GBP": 0.79,
                "JPY": 149.50,
                "AUD": 1.53,
                "CAD": 1.36,
                "CHF": 0.88,
                "CNY": 7.24,
                "INR": 83.12,
                "PHP": 56.85  # Philippine Peso
            }
            
            if to_symbol in fiat_currencies:
                # Convert crypto to fiat
                usd_value = from_price_data["price"] * amount
                converted_amount = usd_value * fiat_currencies[to_symbol]
                
                return {
                    "from_symbol": from_symbol,
                    "to_symbol": to_symbol,
                    "from_amount": amount,
                    "converted_amount": converted_amount,
                    "from_price": from_price_data["price"],
                    "to_price": fiat_currencies[to_symbol],
                    "conversion_rate": converted_amount / amount,
                    "is_fiat": True
                }
            
            elif from_symbol in fiat_currencies:
                # Convert fiat to crypto
                to_price_data = await self.get_crypto_price(to_symbol)
                if not to_price_data:
                    return None
                
                usd_value = amount / fiat_currencies[from_symbol]
                converted_amount = usd_value / to_price_data["price"]
                
                return {
                    "from_symbol": from_symbol,
                    "to_symbol": to_symbol,
                    "from_amount": amount,
                    "converted_amount": converted_amount,
                    "from_price": fiat_currencies[from_symbol],
                    "to_price": to_price_data["price"],
                    "conversion_rate": converted_amount / amount,
                    "is_fiat": True
                }
            
            else:
                # Convert crypto to crypto
                to_price_data = await self.get_crypto_price(to_symbol)
                if not to_price_data:
                    return None
                
                # Convert via USD
                usd_value = from_price_data["price"] * amount
                converted_amount = usd_value / to_price_data["price"]
                
                return {
                    "from_symbol": from_symbol,
                    "to_symbol": to_symbol,
                    "from_amount": amount,
                    "converted_amount": converted_amount,
                    "from_price": from_price_data["price"],
                    "to_price": to_price_data["price"],
                    "conversion_rate": converted_amount / amount,
                    "is_fiat": False
                }
                
        except Exception as e:
            self.logger.error("Error converting crypto", from_symbol=from_symbol, to_symbol=to_symbol, 
                            amount=amount, error=str(e), exc_info=True)
            return None

    async def format_conversion_response(
        self, 
        conversion_data: Dict[str, Any], 
        chat_id: Optional[int] = None
    ) -> str:
        """Format conversion response with optional PHP auto-conversion."""
        if not conversion_data:
            return "❌ Conversion failed"
        
        from_symbol = conversion_data["from_symbol"]
        to_symbol = conversion_data["to_symbol"]
        from_amount = conversion_data["from_amount"]
        converted_amount = conversion_data["converted_amount"]
        
        def format_number(number: float) -> str:
            """Format number with appropriate decimal places."""
            if abs(number) < 0.01:
                return f"{number:.8f}"
            elif abs(number) < 1:
                return f"{number:.4f}"
            else:
                return f"{number:,.2f}"
        
        response = (
            f"💱 **Currency Conversion**\n\n"
            f"**From:** `{format_number(from_amount)} {from_symbol}`\n"
            f"**To:** `{format_number(converted_amount)} {to_symbol}`"
        )
        
        # Add USD value if converting between non-USD currencies
        if from_symbol != "USD" and to_symbol != "USD":
            # Calculate USD value
            from_price_data = await self.get_crypto_price(from_symbol) if from_symbol in self.supported_coins else None
            if from_price_data:
                usd_value = from_price_data["price"] * from_amount
            else:
                # Fiat to fiat conversion via USD
                fiat_rates = {
                    "EUR": 0.92, "GBP": 0.79, "JPY": 149.50, "AUD": 1.53,
                    "CAD": 1.36, "CHF": 0.88, "CNY": 7.24, "INR": 83.12, "PHP": 56.85
                }
                if from_symbol in fiat_rates:
                    usd_value = from_amount / fiat_rates[from_symbol]
                else:
                    usd_value = from_amount  # Assume USD if unknown
            
            response += f"\n**USD Value:** `${format_number(usd_value)}`"
            
            # PHP auto-conversion for specific chat
            if chat_id == -1002153368935:
                php_value = usd_value * 56.85  # USD to PHP rate
                response += f"\n**PHP Value:** `₱{format_number(php_value)}`"
        
        return response

    async def enhanced_convert(
        self, 
        amount: float, 
        from_symbol: str, 
        to_symbol: str = "USD", 
        chat_id: Optional[int] = None
    ) -> Optional[str]:
        """Enhanced crypto conversion with formatted response and PHP auto-conversion."""
        conversion_data = await self.convert_crypto(from_symbol, to_symbol, amount)
        return await self.format_conversion_response(conversion_data, chat_id)


# Global crypto service instance
crypto_service = CryptoService()