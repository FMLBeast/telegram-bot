"""Synonym management handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..decorators.auth import auth_check
from ..services.synonym_service import synonym_service

logger = get_logger(__name__)


@auth_check
async def add_synonym_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add_synonym command to add new synonyms."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    logger.info("Add synonym request", user_id=user_id, args=context.args)
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "📝 **Add Synonym**\n\n"
            "Usage: `/add_synonym <word> <synonym>`\n\n"
            "Examples:\n"
            "• `/add_synonym happy joyful`\n"
            "• `/add_synonym big enormous`\n"
            "• `/add_synonym cool awesome`",
            parse_mode="Markdown"
        )
        return
    
    word = context.args[0]
    synonym = ' '.join(context.args[1:])  # Allow multi-word synonyms
    
    try:
        # Add synonym
        result = await synonym_service.add_synonym(
            word=word,
            synonym=synonym,
            user_id=user_id,
            chat_id=chat_id
        )
        
        if result['success']:
            message = (
                f"✅ **Synonym Added Successfully!**\n\n"
                f"📝 **Word:** {result['word']}\n"
                f"🔗 **Synonym:** {result['synonym']}\n"
                f"📊 **Total synonyms for '{result['word']}':** {result['total_synonyms']}"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("📚 View Synonyms", callback_data=f"view_synonyms_{word}"),
                    InlineKeyboardButton("🎲 Synonym of Day", callback_data="synonym_of_day"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            message = f"❌ **Error:** {result['message']}"
            reply_markup = None
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error("Error in add synonym handler", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error adding synonym. Please try again.")


@auth_check
async def synonym_of_day_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle synonym of the day display."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    logger.info("Synonym of day request", user_id=user_id)
    
    try:
        # Get synonym of the day
        synonym_data = await synonym_service.get_synonym_of_the_day()
        
        word = synonym_data['word']
        synonyms = synonym_data['synonyms']
        count = len(synonyms)
        message_text = synonym_data.get('message', '')
        
        # Format synonyms list
        if count > 8:
            displayed_synonyms = synonyms[:8]
            synonym_list = ', '.join(displayed_synonyms)
            synonym_list += f", ... (+{count - 8} more)"
        else:
            synonym_list = ', '.join(synonyms)
        
        message = (
            f"🌟 **Synonym of the Day**\n\n"
            f"📝 **Word:** {word.upper()}\n"
            f"🔗 **Synonyms ({count}):**\n{synonym_list}\n\n"
            f"💡 {message_text}"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🔍 Search Synonyms", callback_data="search_synonyms"),
                InlineKeyboardButton("📊 Synonym Stats", callback_data="synonym_stats"),
            ],
            [
                InlineKeyboardButton("📚 All Synonyms", callback_data=f"view_all_synonyms_{word}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error("Error in synonym of day handler", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error getting synonym of the day. Please try again.")


@auth_check
async def search_synonyms_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle synonym search."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "🔍 **Search Synonyms**\n\n"
            "Usage: `/search_synonyms <word or partial word>`\n\n"
            "Examples:\n"
            "• `/search_synonyms happy`\n"
            "• `/search_synonyms big`\n"
            "• `/search_synonyms joy`",
            parse_mode="Markdown"
        )
        return
    
    query = ' '.join(context.args)
    
    logger.info("Search synonyms request", user_id=user_id, query=query)
    
    try:
        # Search synonyms
        search_results = await synonym_service.search_synonyms(query)
        
        results = search_results['results']
        count = search_results['count']
        
        if count == 0:
            message = (
                f"🔍 **Search Results for '{query}'**\n\n"
                f"❌ No synonyms found matching your search.\n\n"
                f"💡 Try adding some synonyms first with `/add_synonym`!"
            )
            keyboard = [
                [InlineKeyboardButton("📝 Add Synonym", callback_data="add_synonym_help")]
            ]
        else:
            message_lines = [
                f"🔍 **Search Results for '{query}'**\n",
                f"📊 Found **{count}** words:\n"
            ]
            
            for word, synonyms in list(results.items())[:10]:  # Limit to 10 results
                synonym_preview = ', '.join(synonyms[:5])  # Show first 5 synonyms
                if len(synonyms) > 5:
                    synonym_preview += f" (+{len(synonyms)-5} more)"
                message_lines.append(f"📝 **{word}:** {synonym_preview}")
            
            if count > 10:
                message_lines.append(f"\n... and {count - 10} more results")
            
            message = "\n".join(message_lines)
            
            keyboard = [
                [
                    InlineKeyboardButton("📊 Stats", callback_data="synonym_stats"),
                    InlineKeyboardButton("🎲 Random", callback_data="synonym_of_day"),
                ]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error("Error in search synonyms handler", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error searching synonyms. Please try again.")


@auth_check
async def synonym_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle synonym statistics display."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    logger.info("Synonym stats request", user_id=user_id)
    
    try:
        # Get synonym statistics
        stats = await synonym_service.get_synonym_stats()
        
        total_words = stats['total_words']
        total_synonyms = stats['total_synonyms']
        avg_synonyms = stats.get('average_synonyms_per_word', 0)
        most_synonyms = stats.get('most_synonyms')
        least_synonyms = stats.get('least_synonyms')
        
        message_lines = [
            f"📊 **Synonym Database Statistics**\n",
            f"📚 **Total words:** {total_words}",
            f"🔗 **Total synonyms:** {total_synonyms}",
            f"📈 **Average synonyms per word:** {avg_synonyms}\n"
        ]
        
        if most_synonyms:
            message_lines.extend([
                f"🏆 **Most synonyms:**",
                f"   📝 '{most_synonyms['word']}' ({most_synonyms['count']} synonyms)\n"
            ])
        
        if least_synonyms:
            message_lines.extend([
                f"🥉 **Fewest synonyms:**",
                f"   📝 '{least_synonyms['word']}' ({least_synonyms['count']} synonyms)"
            ])
        
        if total_words == 0:
            message_lines = [
                f"📊 **Synonym Database Statistics**\n",
                f"❌ No synonyms in database yet.\n",
                f"💡 Start adding some with `/add_synonym`!"
            ]
        
        keyboard = [
            [
                InlineKeyboardButton("📝 Add Synonym", callback_data="add_synonym_help"),
                InlineKeyboardButton("🎲 Word of Day", callback_data="synonym_of_day"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "\n".join(message_lines),
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error("Error in synonym stats handler", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error getting synonym statistics. Please try again.")


async def handle_synonym_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle synonym-related callback queries."""
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = update.effective_user.id
    
    logger.info("Synonym callback", user_id=user_id, callback_data=callback_data)
    
    try:
        if callback_data == "synonym_of_day":
            # Show synonym of the day
            synonym_data = await synonym_service.get_synonym_of_the_day()
            
            word = synonym_data['word']
            synonyms = synonym_data['synonyms']
            synonym_list = ', '.join(synonyms[:8])
            if len(synonyms) > 8:
                synonym_list += f" (+{len(synonyms)-8} more)"
            
            message = (
                f"🌟 **Synonym of the Day**\n\n"
                f"📝 **{word.upper()}**\n"
                f"🔗 {synonym_list}"
            )
            
            await query.edit_message_text(message, parse_mode="Markdown")
            
        elif callback_data == "synonym_stats":
            # Show synonym statistics
            stats = await synonym_service.get_synonym_stats()
            
            message = (
                f"📊 **Synonym Statistics**\n\n"
                f"📚 Total words: {stats['total_words']}\n"
                f"🔗 Total synonyms: {stats['total_synonyms']}\n"
                f"📈 Avg per word: {stats.get('average_synonyms_per_word', 0):.1f}"
            )
            
            if stats.get('most_synonyms'):
                message += f"\n🏆 Most: '{stats['most_synonyms']['word']}' ({stats['most_synonyms']['count']})"
            
            await query.edit_message_text(message, parse_mode="Markdown")
            
        elif callback_data == "search_synonyms":
            message = (
                "🔍 **Search Synonyms**\n\n"
                "Use `/search_synonyms <word>` to find synonyms.\n\n"
                "Examples:\n"
                "• `/search_synonyms happy`\n" 
                "• `/search_synonyms big`"
            )
            
            await query.edit_message_text(message, parse_mode="Markdown")
            
        elif callback_data == "add_synonym_help":
            message = (
                "📝 **Add New Synonym**\n\n"
                "Use `/add_synonym <word> <synonym>` to add.\n\n"
                "Examples:\n"
                "• `/add_synonym happy joyful`\n"
                "• `/add_synonym cool awesome`\n"
                "• `/add_synonym big enormous`"
            )
            
            await query.edit_message_text(message, parse_mode="Markdown")
            
        elif callback_data.startswith("view_synonyms_"):
            word = callback_data.split("_", 2)[2]
            synonyms = await synonym_service.get_synonyms(word)
            
            if synonyms:
                synonym_list = ', '.join(synonyms)
                message = f"📚 **Synonyms for '{word}':**\n\n{synonym_list}"
            else:
                message = f"❌ No synonyms found for '{word}'"
            
            await query.edit_message_text(message, parse_mode="Markdown")
            
        else:
            await query.edit_message_text("❓ Unknown synonym action.")
            
    except Exception as e:
        logger.error("Error handling synonym callback", callback_data=callback_data, error=str(e), exc_info=True)
        await query.edit_message_text("❌ Error processing synonym request.")