import logging
import openai
import asyncio
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from .casino_db import CasinoDBManager
from typing import Optional, Dict, Any, List
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)
client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

class CasinoHandler:
    def __init__(self, db_conn):
        self.db = CasinoDBManager(db_conn)
        self.active_queries = {}
        self.casino_contexts = {}  # Store casino contexts for active conversations

    async def handle_casino_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle the /casino command"""
        user_query = ' '.join(context.args) if context.args else None
        
        if not user_query:
            # No query provided, show menu
            await self.show_casino_menu(update, context)
            return

        # Process the query directly
        await self.process_casino_query(update, context, user_query)

    async def show_casino_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the main casino menu"""
        keyboard = [
            [InlineKeyboardButton("📊 Casino Information", callback_data="casino_info")],
            [InlineKeyboardButton("💰 Bonus Calculator", callback_data="casino_calc")],
            [InlineKeyboardButton("🎯 Compare Casinos", callback_data="casino_compare")],
            [InlineKeyboardButton("❓ Ask Question", callback_data="casino_ask")],
        ]
        
        await update.message.reply_text(
            "🎰 *Casino Information Center* 🎰\n\n"
            "What would you like to know about?\n\n"
            "• Use buttons below to navigate\n"
            "• Or ask a direct question using /casino <your question>\n"
            "• Example: /casino what's the weekly bonus at BC level 23?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from casino buttons"""
        query = update.callback_query
        await query.answer()
        data = query.data

        if data == "casino_info":
            await self.show_casino_selection(update, context)
        elif data == "casino_calc":
            await self.show_calculator_menu(update, context)
        elif data == "casino_compare":
            await self.show_comparison_menu(update, context)
        elif data == "casino_ask":
            await self.prompt_question(update, context)
        elif data.startswith("casino_select_"):
            casino_name = data.replace("casino_select_", "")
            await self.show_casino_details(update, context, casino_name)
        elif data.startswith("casino_calc_"):
            await self.handle_calculator(update, context, data)
        elif data.startswith("casino_compare_"):
            await self.handle_comparison(update, context, data)

    async def process_casino_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
        """Process a casino-related query using GPT"""
        try:
            # First, try to identify which casino is being asked about
            casino_name = self._detect_casino_from_query(query)
            
            # Get casino context
            casino_context = await self._get_casino_context(casino_name)
            
            if not casino_context:
                # If casino not detected or found, prompt for selection
                self.active_queries[update.effective_user.id] = query
                await self.show_casino_selection(update, context, 
                    "Which casino would you like to know about?")
                return

            # Process with GPT
            await update.message.reply_text("🎲 Processing your query, please wait...")
            response = await self._query_gpt(query, casino_context)
            
            await update.message.reply_text(response, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Error processing casino query: {str(e)}")
            await update.message.reply_text(
                "Sorry, I encountered an error processing your query. Please try again."
            )

    async def _query_gpt(self, query: str, casino_context: Dict) -> str:
        """Query GPT with casino context"""
        system_prompt = """You are a casino information specialist. Provide clear, accurate information about casino features, 
        bonuses, and VIP systems. Use appropriate emojis and markdown formatting. For calculations, show your work step by step. 
        If information isn't available in the provided context, clearly state that."""

        prompt = f"""
        Using the following casino information:
        {casino_context}

        Answer this question: {query}

        Format your response with:
        - Appropriate emojis
        - Clear markdown formatting
        - Step-by-step calculations when needed
        - Clear statements if information isn't available
        """

        max_retries = 3
        for attempt in range(max_retries):
            try:
                completion = await client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                return completion.choices[0].message.content.strip()
            except openai.RateLimitError as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep((2 ** attempt) + random.random())
                else:
                    raise
            except Exception as e:
                logger.error(f"GPT query error: {str(e)}")
                raise

    def _detect_casino_from_query(self, query: str) -> Optional[str]:
        """Detect which casino is being asked about from the query"""
        query_lower = query.lower()
        casino_keywords = {
            "BC.GAME": ["bc", "bc.game", "bcgame"],
            "Stake": ["stake", "stakes"],
            "Shuffle": ["shuffle", "shfl"],
            "LuckyBird": ["luckybird", "lucky bird"],
            "Gamba": ["gamba"]
        }

        for casino, keywords in casino_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return casino
        return None

    async def _get_casino_context(self, casino_name: Optional[str] = None) -> Dict:
        """Get or build casino context for GPT"""
        if not casino_name:
            # Return context for all casinos
            return {
                "casinos": self.db.get_all_casinos(),
                "type": "casino_list",
                "comparison_features": self._get_comparison_features()
            }

        # Get specific casino context
        casino_data = self.db.get_casino_data(casino_name)
        if not casino_data:
            return None

        return {
            "casino_name": casino_name,
            "data": casino_data,
            "type": "casino_specific",
            "features": self._format_casino_features(casino_data)
        }

    def _format_casino_features(self, casino_data: Dict) -> Dict:
        """Format casino features for GPT context"""
        return {
            "vip_system": self._format_vip_system(casino_data.get("tiers", {})),
            "bonuses": self._format_bonuses(casino_data.get("bonuses", {})),
            "features": casino_data.get("features", {}),
            "currencies": casino_data.get("currencies", {})
        }

    def _format_vip_system(self, tiers: Dict) -> Dict:
        """Format VIP system information"""
        return {
            tier_name: {
                "range": tier_data.get("level_range"),
                "requirements": tier_data.get("xp_requirement"),
                "benefits": tier_data.get("bonus_amount")
            }
            for tier_name, tier_data in tiers.items()
        }

    def _format_bonuses(self, bonuses: Dict) -> Dict:
        """Format bonus information"""
        formatted = {}
        for bonus_type, bonus_list in bonuses.items():
            formatted[bonus_type] = {
                "tiers": [bonus["tier"] for bonus in bonus_list],
                "amounts": [bonus["amount"] for bonus in bonus_list if bonus["amount"]],
                "percentages": [bonus["percentage"] for bonus in bonus_list if bonus["percentage"]],
                "requirements": [bonus["requirements"] for bonus in bonus_list if bonus["requirements"]]
            }
        return formatted

    def _get_comparison_features(self) -> List[str]:
        """Get list of features that can be compared across casinos"""
        return [
            "Weekly Bonus",
            "Monthly Bonus",
            "VIP System",
            "Minimum Deposits",
            "Withdrawal Fees",
            "Cryptocurrencies Supported"
        ]

    async def show_casino_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                  message: str = "Select a casino:"):
        """Show casino selection buttons"""
        casinos = self.db.get_all_casinos()
        keyboard = []
        for casino in casinos:
            keyboard.append([InlineKeyboardButton(
                casino['name'], 
                callback_data=f"casino_select_{casino['name']}"
            )])
        keyboard.append([InlineKeyboardButton("🔄 Back to Menu", callback_data="casino_menu")])
        
        await self._edit_or_send_message(
            update, 
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _edit_or_send_message(self, update: Update, text: str, **kwargs):
        """Helper method to either edit or send a new message"""
        if update.callback_query:
            await update.callback_query.edit_message_text(text, **kwargs)
        else:
            await update.message.reply_text(text, **kwargs)

    # Helper method for error handling
    async def _handle_error(self, update: Update, error: Exception):
        """Handle errors in the casino handler"""
        error_message = (
            "Sorry, I encountered an error while processing your request. "
            "Please try again or contact support if the issue persists."
        )
        logger.error(f"Error in casino handler: {str(error)}")
        await self._edit_or_send_message(update, error_message)

casino_handler = None

def init_casino_handler(db_conn):
    """Initialize the casino handler"""
    global casino_handler
    if casino_handler is None:
        casino_handler = CasinoHandler(db_conn)
    return casino_handler