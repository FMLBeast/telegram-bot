"""Mood analysis handlers."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..decorators.auth import auth_check
from ..services.mood_service import mood_service
from ..services.user_service import UserService

logger = get_logger(__name__)
user_service = UserService()


@auth_check
async def mood_analysis_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /hows command for mood analysis."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    # Check if analyzing another user or self
    target_user_id = user_id
    target_username = None
    
    if context.args:
        # Try to parse username or user ID
        target_input = context.args[0]
        if target_input.startswith('@'):
            target_username = target_input[1:]
            # You could look up user ID by username here
            # For now, we'll analyze the requesting user
        else:
            try:
                target_user_id = int(target_input)
            except ValueError:
                await update.message.reply_text(
                    "❓ Invalid user ID. Usage: `/hows` or `/hows @username` or `/hows user_id`",
                    parse_mode="Markdown"
                )
                return
    
    logger.info("Mood analysis request", user_id=user_id, target_user_id=target_user_id)
    
    try:
        # Show analysis in progress
        progress_msg = await update.message.reply_text(
            "🔍 Analyzing mood patterns...\n"
            "This may take a moment as I review recent messages. 🧠"
        )
        
        # Perform mood analysis
        mood_result = await mood_service.analyze_user_mood(
            user_id=target_user_id,
            chat_id=chat_id,
            days=3,
            max_messages=20
        )
        
        # Format the response
        display_name = (
            mood_result.get('first_name') or 
            mood_result.get('username') or 
            f"User {target_user_id}"
        )
        
        mood = mood_result['mood']
        confidence = mood_result['confidence']
        analysis = mood_result['analysis']
        suggestions = mood_result.get('suggestions', [])
        message_count = mood_result['message_count']
        
        # Mood emoji mapping
        mood_emojis = {
            'happy': '😊',
            'sad': '😢',
            'angry': '😠',
            'anxious': '😰',
            'excited': '🤗',
            'neutral': '😐',
            'frustrated': '😤',
            'content': '😌',
            'joyful': '😄',
            'depressed': '😔',
            'unknown': '🤷',
            'error': '❌'
        }
        
        mood_emoji = mood_emojis.get(mood, '🤔')
        
        # Confidence bar
        confidence_percent = int(confidence * 100)
        confidence_bar = '█' * (confidence_percent // 10) + '░' * (10 - (confidence_percent // 10))
        
        message_lines = [
            f"🧠 **Mood Analysis Report**\n",
            f"👤 **User:** {display_name}",
            f"{mood_emoji} **Mood:** {mood.title()}",
            f"📊 **Confidence:** {confidence_percent}% {confidence_bar}",
            f"💬 **Messages analyzed:** {message_count}",
            f"📅 **Period:** Last 3 days\n",
            f"🔍 **Analysis:**",
            f"{analysis}\n"
        ]
        
        if suggestions:
            message_lines.append("💡 **Suggestions:**")
            for i, suggestion in enumerate(suggestions[:3], 1):
                message_lines.append(f"{i}. {suggestion}")
        
        # Confidence level interpretation
        if confidence >= 0.8:
            confidence_note = "🎯 High confidence - analysis is very reliable"
        elif confidence >= 0.6:
            confidence_note = "✅ Good confidence - analysis is fairly reliable"  
        elif confidence >= 0.4:
            confidence_note = "⚠️ Medium confidence - analysis may be uncertain"
        else:
            confidence_note = "❓ Low confidence - more data needed for accuracy"
        
        message_lines.extend([
            "",
            f"📈 *{confidence_note}*"
        ])
        
        keyboard = []
        if target_user_id == user_id:
            keyboard.append([
                InlineKeyboardButton("📈 Mood Trends", callback_data=f"mood_trends_{user_id}"),
                InlineKeyboardButton("🔄 Re-analyze", callback_data=f"mood_reanalyze_{user_id}"),
            ])
        
        keyboard.append([
            InlineKeyboardButton("ℹ️ About Mood Analysis", callback_data="mood_info"),
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        # Edit the progress message with results
        await progress_msg.edit_text(
            "\n".join(message_lines),
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error("Error in mood analysis handler", user_id=user_id, error=str(e), exc_info=True)
        try:
            await progress_msg.edit_text("❌ Error analyzing mood. Please try again later.")
        except:
            await update.message.reply_text("❌ Error analyzing mood. Please try again later.")


@auth_check  
async def mood_trends_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle mood trends analysis."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    logger.info("Mood trends request", user_id=user_id)
    
    try:
        await update.message.reply_text("📈 Analyzing your mood trends over time...")
        
        # Get mood trends
        trends = await mood_service.get_mood_trends(
            user_id=user_id,
            chat_id=chat_id,
            days=14
        )
        
        mood_points = trends['mood_points']
        overall_trend = trends['overall_trend']
        avg_confidence = trends['average_confidence']
        positive_days = trends['positive_days']
        negative_days = trends['negative_days']
        total_samples = trends['total_samples']
        
        if total_samples == 0:
            await update.message.reply_text(
                "📈 **Mood Trends**\n\n"
                "Not enough data available for trend analysis.\n"
                "Keep chatting and try again later! 💬",
                parse_mode="Markdown"
            )
            return
        
        # Trend emoji
        trend_emojis = {
            'positive': '📈',
            'negative': '📉',
            'neutral': '➡️'
        }
        
        trend_emoji = trend_emojis.get(overall_trend, '➡️')
        
        message_lines = [
            f"📈 **Your Mood Trends (14 days)**\n",
            f"{trend_emoji} **Overall trend:** {overall_trend.title()}",
            f"📊 **Average confidence:** {avg_confidence * 100:.0f}%",
            f"😊 **Positive periods:** {positive_days}/{total_samples}",
            f"😔 **Negative periods:** {negative_days}/{total_samples}",
            f"📅 **Data points:** {total_samples}\n",
            f"📋 **Recent mood timeline:**"
        ]
        
        # Show recent mood points
        for point in mood_points[:7]:  # Last 7 data points
            date = point['date']
            mood = point['mood']
            confidence = point['confidence']
            
            mood_emoji = {
                'happy': '😊', 'sad': '😢', 'angry': '😠', 'anxious': '😰',
                'excited': '🤗', 'neutral': '😐', 'frustrated': '😤',
                'content': '😌', 'joyful': '😄'
            }.get(mood, '🤔')
            
            confidence_stars = '★' * int(confidence * 5)
            message_lines.append(f"{date}: {mood_emoji} {mood} ({confidence_stars})")
        
        keyboard = [
            [
                InlineKeyboardButton("🧠 Current Mood", callback_data=f"mood_current_{user_id}"),
                InlineKeyboardButton("📊 Mood Stats", callback_data=f"mood_stats_{user_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "\n".join(message_lines),
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error("Error in mood trends handler", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error analyzing mood trends. Please try again.")


async def handle_mood_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle mood-related callback queries."""
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = update.effective_user.id
    
    logger.info("Mood callback", user_id=user_id, callback_data=callback_data)
    
    try:
        if callback_data.startswith("mood_trends_"):
            target_user_id = int(callback_data.split("_")[2])
            
            await query.edit_message_text("📈 Loading mood trends...")
            
            trends = await mood_service.get_mood_trends(
                user_id=target_user_id,
                days=14
            )
            
            if trends['total_samples'] > 0:
                message = (
                    f"📈 **Mood Trends Summary**\n\n"
                    f"Overall: {trends['overall_trend'].title()}\n"
                    f"Positive periods: {trends['positive_days']}\n"
                    f"Negative periods: {trends['negative_days']}\n"
                    f"Average confidence: {trends['average_confidence']*100:.0f}%"
                )
            else:
                message = "📈 No trend data available yet."
            
            await query.edit_message_text(message, parse_mode="Markdown")
            
        elif callback_data.startswith("mood_reanalyze_"):
            target_user_id = int(callback_data.split("_")[2])
            
            await query.edit_message_text("🔍 Re-analyzing mood...")
            
            mood_result = await mood_service.analyze_user_mood(
                user_id=target_user_id,
                days=3,
                max_messages=20
            )
            
            mood = mood_result['mood']
            confidence = mood_result['confidence']
            
            message = (
                f"🧠 **Fresh Mood Analysis**\n\n"
                f"Mood: {mood.title()}\n"
                f"Confidence: {confidence*100:.0f}%\n\n"
                f"{mood_result['analysis']}"
            )
            
            await query.edit_message_text(message, parse_mode="Markdown")
            
        elif callback_data == "mood_info":
            info_message = (
                "ℹ️ **About Mood Analysis**\n\n"
                "🧠 **How it works:**\n"
                "• Analyzes your recent messages (last 3 days)\n"
                "• Uses AI to detect emotional patterns\n"
                "• Provides confidence scoring\n\n"
                "📊 **Confidence levels:**\n"
                "• 80%+: Very reliable\n"
                "• 60-80%: Fairly reliable\n"
                "• 40-60%: Somewhat uncertain\n"
                "• <40%: More data needed\n\n"
                "🔒 **Privacy:** Analysis is temporary and not stored permanently."
            )
            
            await query.edit_message_text(info_message, parse_mode="Markdown")
            
        else:
            await query.edit_message_text("❓ Unknown mood action.")
            
    except Exception as e:
        logger.error("Error handling mood callback", callback_data=callback_data, error=str(e), exc_info=True)
        await query.edit_message_text("❌ Error processing mood request.")