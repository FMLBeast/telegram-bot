"""User utility handlers."""

import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.helpers import mention_html

from ..core.logging import get_logger
from ..decorators.auth import auth_check
from ..services.user_service import UserService

logger = get_logger(__name__)
user_service = UserService()


@auth_check
async def mention_all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /all command to mention all users in the chat."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat = update.effective_chat
    
    if not chat or chat.type == 'private':
        await update.message.reply_text(
            "❌ The `/all` command only works in group chats.",
            parse_mode="Markdown"
        )
        return
    
    logger.info("Mention all request", user_id=user_id, chat_id=chat.id)
    
    try:
        # Get chat administrators and members (this requires bot admin privileges)
        try:
            administrators = await context.bot.get_chat_administrators(chat.id)
            admin_ids = {admin.user.id for admin in administrators}
            
            # For large groups, we'll mention admins first, then show a warning
            if len(admin_ids) > 50:
                await update.message.reply_text(
                    "⚠️ This is a large group. I can only mention administrators to avoid spam.\n"
                    "Use with caution in large groups!",
                    parse_mode="Markdown"
                )
                return
            
        except Exception as e:
            logger.warning("Could not get chat administrators", error=str(e))
            await update.message.reply_text(
                "❌ I need administrator privileges to use the `/all` command.\n"
                "Please make me an admin first!",
                parse_mode="Markdown"
            )
            return
        
        # Limit mentions to prevent spam
        MAX_MENTIONS = 20
        
        # Create mention list
        mentions = []
        mentioned_users = set()
        
        # Add the person who called the command
        caller = update.effective_user
        mentions.append(mention_html(caller.id, caller.first_name or caller.username or "User"))
        mentioned_users.add(caller.id)
        
        # Add administrators first
        for admin in administrators:
            if len(mentions) >= MAX_MENTIONS:
                break
                
            user = admin.user
            if user.id not in mentioned_users and not user.is_bot:
                display_name = user.first_name or user.username or f"User{user.id}"
                mentions.append(mention_html(user.id, display_name))
                mentioned_users.add(user.id)
        
        # Add reason for mention if provided
        reason = ' '.join(context.args) if context.args else "General attention"
        
        # Format the message
        if len(mentions) == 1:
            message = f"👥 Only you are available to mention right now!\n\n📝 Reason: {reason}"
        else:
            mention_text = ' '.join(mentions)
            message = (
                f"👥 **Attention Everyone!**\n\n"
                f"{mention_text}\n\n"
                f"📝 **Reason:** {reason}\n"
                f"👤 **Called by:** {caller.first_name or caller.username}"
            )
        
        # Add warning for large groups
        if len(administrators) > MAX_MENTIONS:
            message += f"\n\n⚠️ Limited to {MAX_MENTIONS} mentions to prevent spam."
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Shuffle Users", callback_data="shuffle_users"),
                InlineKeyboardButton("📊 Chat Stats", callback_data="chat_member_stats"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error("Error in mention all handler", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ Error mentioning users. I might need admin privileges or this group might be too large.",
            parse_mode="Markdown"
        )


@auth_check
async def shuffle_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /shuffle_userlist command to randomly shuffle and display users."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat = update.effective_chat
    
    if not chat or chat.type == 'private':
        await update.message.reply_text(
            "❌ The `/shuffle_userlist` command only works in group chats.",
            parse_mode="Markdown"
        )
        return
    
    logger.info("Shuffle users request", user_id=user_id, chat_id=chat.id)
    
    try:
        # Get chat members
        try:
            administrators = await context.bot.get_chat_administrators(chat.id)
            
            # Extract user information
            users = []
            for admin in administrators:
                user = admin.user
                if not user.is_bot:  # Exclude bots
                    display_name = user.first_name or user.username or f"User{user.id}"
                    users.append({
                        'id': user.id,
                        'name': display_name,
                        'username': user.username,
                        'is_admin': True
                    })
            
            if not users:
                await update.message.reply_text(
                    "❌ No users found to shuffle.\n"
                    "This might be due to privacy settings or bot permissions.",
                    parse_mode="Markdown"
                )
                return
            
        except Exception as e:
            logger.warning("Could not get chat members for shuffle", error=str(e))
            await update.message.reply_text(
                "❌ I need appropriate permissions to see chat members.\n"
                "Please ensure I have admin privileges!",
                parse_mode="Markdown"
            )
            return
        
        # Shuffle the users
        shuffled_users = users.copy()
        random.shuffle(shuffled_users)
        
        # Format the shuffled list
        message_lines = [
            f"🎲 **Shuffled User List** ({len(shuffled_users)} users)\n"
        ]
        
        # Show up to 15 users to avoid message length limits
        display_limit = min(15, len(shuffled_users))
        
        for i, user in enumerate(shuffled_users[:display_limit], 1):
            name = user['name']
            username_part = f"@{user['username']}" if user['username'] else ""
            admin_badge = " 👑" if user['is_admin'] else ""
            
            if username_part:
                message_lines.append(f"{i:2d}. {name} ({username_part}){admin_badge}")
            else:
                message_lines.append(f"{i:2d}. {name}{admin_badge}")
        
        if len(shuffled_users) > display_limit:
            message_lines.append(f"\n... and {len(shuffled_users) - display_limit} more users")
        
        # Add some fun stats
        admin_count = sum(1 for user in shuffled_users if user['is_admin'])
        message_lines.extend([
            "",
            f"📊 **Stats:**",
            f"👑 Admins: {admin_count}",
            f"👤 Total: {len(shuffled_users)}",
            f"🎯 Random order generated!"
        ])
        
        keyboard = [
            [
                InlineKeyboardButton("🎲 Shuffle Again", callback_data="shuffle_again"),
                InlineKeyboardButton("👥 Mention All", callback_data="mention_all_users"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "\n".join(message_lines),
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error("Error in shuffle users handler", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ Error shuffling users. Please try again or check bot permissions.",
            parse_mode="Markdown"
        )


@auth_check
async def random_user_picker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /random_user command to pick a random user from the chat."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat = update.effective_chat
    
    if not chat or chat.type == 'private':
        await update.message.reply_text(
            "❌ The `/random_user` command only works in group chats.",
            parse_mode="Markdown"
        )
        return
    
    logger.info("Random user picker request", user_id=user_id, chat_id=chat.id)
    
    try:
        # Get chat members
        try:
            administrators = await context.bot.get_chat_administrators(chat.id)
            
            # Extract non-bot users
            users = []
            for admin in administrators:
                user = admin.user
                if not user.is_bot:
                    display_name = user.first_name or user.username or f"User{user.id}"
                    users.append({
                        'id': user.id,
                        'name': display_name,
                        'username': user.username,
                        'is_admin': True
                    })
            
            if not users:
                await update.message.reply_text(
                    "❌ No users available for random selection.",
                    parse_mode="Markdown"
                )
                return
            
        except Exception as e:
            logger.warning("Could not get chat members for random picker", error=str(e))
            await update.message.reply_text(
                "❌ I need appropriate permissions to access chat members.",
                parse_mode="Markdown"
            )
            return
        
        # Pick a random user
        selected_user = random.choice(users)
        
        # Create mention
        mention = mention_html(selected_user['id'], selected_user['name'])
        
        # Determine selection reason
        reason = ' '.join(context.args) if context.args else "random selection"
        
        # Fun messages for different scenarios
        fun_messages = [
            "🎯 The wheel of fate has chosen:",
            "🎲 Random selection complete:",
            "🎪 And the winner is:",
            "⭐ Destiny has decided:",
            "🎰 The random gods have spoken:",
        ]
        
        intro = random.choice(fun_messages)
        
        message = (
            f"{intro}\n\n"
            f"👤 **Selected User:** {mention}\n"
            f"📝 **Reason:** {reason}\n"
            f"👑 **Admin:** {'Yes' if selected_user['is_admin'] else 'No'}\n\n"
            f"🎲 *Randomly chosen from {len(users)} users*"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🎲 Pick Again", callback_data="random_user_again"),
                InlineKeyboardButton("🎪 Show All", callback_data="shuffle_users"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error("Error in random user picker handler", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error selecting random user. Please try again.")


async def handle_utility_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle utility-related callback queries."""
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = update.effective_user.id
    
    logger.info("Utility callback", user_id=user_id, callback_data=callback_data)
    
    try:
        if callback_data == "shuffle_users" or callback_data == "shuffle_again":
            # Shuffle users again
            chat = update.effective_chat
            if not chat:
                await query.edit_message_text("❌ Chat information not available.")
                return
            
            try:
                administrators = await context.bot.get_chat_administrators(chat.id)
                users = []
                
                for admin in administrators:
                    user = admin.user
                    if not user.is_bot:
                        display_name = user.first_name or user.username or f"User{user.id}"
                        users.append({
                            'name': display_name,
                            'username': user.username,
                            'is_admin': True
                        })
                
                if users:
                    random.shuffle(users)
                    
                    message_lines = [f"🎲 **Shuffled List** ({len(users)} users)\n"]
                    
                    for i, user in enumerate(users[:10], 1):
                        name = user['name']
                        admin_badge = " 👑" if user['is_admin'] else ""
                        message_lines.append(f"{i}. {name}{admin_badge}")
                    
                    if len(users) > 10:
                        message_lines.append(f"\n... and {len(users) - 10} more")
                    
                    message = "\n".join(message_lines)
                else:
                    message = "❌ No users available to shuffle."
                
                await query.edit_message_text(message, parse_mode="Markdown")
                
            except Exception as e:
                await query.edit_message_text(f"❌ Error shuffling users: {str(e)}")
        
        elif callback_data == "random_user_again":
            # Pick another random user
            chat = update.effective_chat
            if not chat:
                await query.edit_message_text("❌ Chat information not available.")
                return
            
            try:
                administrators = await context.bot.get_chat_administrators(chat.id)
                users = [admin.user for admin in administrators if not admin.user.is_bot]
                
                if users:
                    selected_user = random.choice(users)
                    display_name = selected_user.first_name or selected_user.username or f"User{selected_user.id}"
                    mention = mention_html(selected_user.id, display_name)
                    
                    message = f"🎲 **New Random Selection:**\n\n👤 {mention}"
                    
                    await query.edit_message_text(message, parse_mode="HTML")
                else:
                    await query.edit_message_text("❌ No users available for selection.")
                    
            except Exception as e:
                await query.edit_message_text(f"❌ Error selecting user: {str(e)}")
        
        elif callback_data == "chat_member_stats":
            # Show chat member statistics
            chat = update.effective_chat
            if not chat:
                await query.edit_message_text("❌ Chat information not available.")
                return
            
            try:
                administrators = await context.bot.get_chat_administrators(chat.id)
                admin_count = len([admin for admin in administrators if not admin.user.is_bot])
                bot_count = len([admin for admin in administrators if admin.user.is_bot])
                
                message = (
                    f"📊 **Chat Statistics**\n\n"
                    f"👑 Administrators: {admin_count}\n"
                    f"🤖 Bots: {bot_count}\n"
                    f"📋 Total visible: {admin_count + bot_count}\n\n"
                    f"ℹ️ *Only administrators are visible to bots*"
                )
                
                await query.edit_message_text(message, parse_mode="Markdown")
                
            except Exception as e:
                await query.edit_message_text(f"❌ Error getting stats: {str(e)}")
        
        else:
            await query.edit_message_text("❓ Unknown utility action.")
            
    except Exception as e:
        logger.error("Error handling utility callback", callback_data=callback_data, error=str(e), exc_info=True)
        await query.edit_message_text("❌ Error processing utility request.")