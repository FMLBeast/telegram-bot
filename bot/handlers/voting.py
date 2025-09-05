"""Voting and polling handlers for the bot."""

import re
from typing import Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..core.logging import get_logger
from ..services.voting_service import voting_service, PollType
from ..decorators.auth import auth_check
from ..core.exceptions import APIError

logger = get_logger(__name__)


def create_poll_keyboard(poll_data: dict, user_votes: List[int] = None) -> InlineKeyboardMarkup:
    """Create inline keyboard for a poll."""
    if user_votes is None:
        user_votes = []
    
    keyboard = []
    options = poll_data["options"]
    vote_counts = poll_data["vote_counts"]
    total_votes = poll_data["total_votes"]
    
    for i, option in enumerate(options):
        # Calculate percentage
        percentage = (vote_counts[i] / max(total_votes, 1)) * 100
        
        # Create progress bar
        bar_length = 10
        filled_length = int(bar_length * percentage / 100)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        
        # Check mark for user's votes
        check = "✅ " if i in user_votes else ""
        
        button_text = f"{check}{option} ({vote_counts[i]}) {bar} {percentage:.1f}%"
        
        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=f"vote_{poll_data['id']}_{i}"
            )
        ])
    
    # Add control buttons
    control_row = []
    if poll_data["status"] == "active":
        control_row.append(
            InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_poll_{poll_data['id']}")
        )
        control_row.append(
            InlineKeyboardButton("❌ Close Poll", callback_data=f"close_poll_{poll_data['id']}")
        )
    
    control_row.append(
        InlineKeyboardButton("📊 Results", callback_data=f"results_poll_{poll_data['id']}")
    )
    
    if control_row:
        keyboard.append(control_row)
    
    return InlineKeyboardMarkup(keyboard)


def format_poll_message(poll_data: dict, show_results: bool = False) -> str:
    """Format poll message."""
    status_emoji = {"active": "🗳️", "closed": "🔒", "cancelled": "❌"}[poll_data["status"]]
    type_emoji = {
        "single_choice": "1️⃣",
        "multiple_choice": "🔢",
        "anonymous": "👤",
        "quiz": "🧠"
    }[poll_data["poll_type"]]
    
    message = f"{status_emoji} **Poll:** {poll_data['title']}\n"
    message += f"{type_emoji} **Type:** {poll_data['poll_type'].replace('_', ' ').title()}\n"
    
    if poll_data.get("description"):
        message += f"📝 **Description:** {poll_data['description']}\n"
    
    message += f"\n📊 **Total Votes:** {poll_data['total_votes']} from {poll_data['unique_voters']} users\n"
    
    if poll_data["status"] == "active":
        import datetime
        time_left = poll_data["expires_at"] - datetime.datetime.utcnow()
        if time_left.total_seconds() > 0:
            hours = int(time_left.total_seconds() // 3600)
            minutes = int((time_left.total_seconds() % 3600) // 60)
            message += f"⏰ **Time Left:** {hours}h {minutes}m\n"
        else:
            message += "⏰ **Status:** Expired (closing soon)\n"
    
    if show_results or poll_data["status"] != "active":
        message += "\n**Results:**\n"
        options = poll_data["options"]
        vote_counts = poll_data["vote_counts"]
        total_votes = max(poll_data["total_votes"], 1)
        
        # Find winner(s)
        max_votes = max(vote_counts) if vote_counts else 0
        
        for i, (option, count) in enumerate(zip(options, vote_counts)):
            percentage = (count / total_votes) * 100
            
            # Progress bar
            bar_length = 15
            filled_length = int(bar_length * percentage / 100)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            
            # Winner crown
            crown = "👑 " if count == max_votes and count > 0 else ""
            
            message += f"{crown}**{i+1}.** {option}\n"
            message += f"   {bar} {count} votes ({percentage:.1f}%)\n\n"
        
        # Show correct answer for quiz
        if poll_data["poll_type"] == "quiz" and poll_data.get("correct_option") is not None:
            correct_idx = poll_data["correct_option"]
            if 0 <= correct_idx < len(options):
                message += f"✅ **Correct Answer:** {options[correct_idx]}\n"
    
    return message


@auth_check
async def create_poll_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /poll command to create a new poll."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if not context.args:
        await update.message.reply_text(
            "📊 **Create a Poll**\n\n"
            "**Usage:** `/poll \"Question\" \"Option 1\" \"Option 2\" [\"Option 3\" ...]`\n\n"
            "**Examples:**\n"
            "• `/poll \"Favorite color?\" \"Red\" \"Blue\" \"Green\"`\n"
            "• `/poll \"Best pizza topping?\" \"Pepperoni\" \"Mushrooms\" \"Pineapple\" \"Cheese\"`\n\n"
            "**Advanced Options:**\n"
            "• Add `--multiple` for multiple choice\n"
            "• Add `--anonymous` for anonymous voting\n"
            "• Add `--quiz=2` for quiz mode (option 2 is correct)\n"
            "• Add `--duration=60` for custom duration in minutes\n\n"
            "**Quiz Example:**\n"
            "• `/poll \"What is 2+2?\" \"3\" \"4\" \"5\" --quiz=2`",
            parse_mode="Markdown"
        )
        return
    
    try:
        # Parse command arguments
        full_text = " ".join(context.args)
        
        # Extract options (quoted strings)
        import shlex
        parts = shlex.split(full_text)
        
        # Separate options from flags
        options = []
        flags = []
        
        for part in parts:
            if part.startswith("--"):
                flags.append(part)
            else:
                options.append(part)
        
        if len(options) < 3:  # Question + at least 2 options
            await update.message.reply_text(
                "❌ Please provide a question and at least 2 options in quotes.\n\n"
                "Example: `/poll \"Question?\" \"Option 1\" \"Option 2\"`",
                parse_mode="Markdown"
            )
            return
        
        question = options[0]
        poll_options = options[1:]
        
        if len(poll_options) > 10:
            await update.message.reply_text("❌ Maximum 10 options allowed.")
            return
        
        # Parse flags
        poll_type = PollType.SINGLE_CHOICE
        is_anonymous = False
        duration_minutes = 1440  # 24 hours
        correct_option = None
        
        for flag in flags:
            if flag == "--multiple":
                poll_type = PollType.MULTIPLE_CHOICE
            elif flag == "--anonymous":
                is_anonymous = True
                poll_type = PollType.ANONYMOUS
            elif flag.startswith("--quiz="):
                try:
                    correct_idx = int(flag.split("=")[1]) - 1  # Convert to 0-based
                    if 0 <= correct_idx < len(poll_options):
                        poll_type = PollType.QUIZ
                        correct_option = correct_idx
                    else:
                        await update.message.reply_text("❌ Invalid correct option index.")
                        return
                except ValueError:
                    await update.message.reply_text("❌ Invalid quiz format. Use --quiz=1 (1-based index).")
                    return
            elif flag.startswith("--duration="):
                try:
                    duration_minutes = int(flag.split("=")[1])
                    if duration_minutes < 1 or duration_minutes > 10080:  # 1 week max
                        await update.message.reply_text("❌ Duration must be between 1 minute and 1 week.")
                        return
                except ValueError:
                    await update.message.reply_text("❌ Invalid duration format. Use --duration=60 (minutes).")
                    return
        
        # Create the poll
        poll_data = await voting_service.create_poll(
            creator_id=user_id,
            chat_id=chat_id,
            title=question,
            options=poll_options,
            poll_type=poll_type,
            duration_minutes=duration_minutes,
            is_anonymous=is_anonymous,
            correct_option=correct_option
        )
        
        if not poll_data:
            await update.message.reply_text("❌ Failed to create poll. Please try again.")
            return
        
        # Get full poll data for display
        full_poll_data = await voting_service.get_poll(poll_data["id"])
        
        if full_poll_data:
            # Create poll message and keyboard
            poll_message = format_poll_message(full_poll_data)
            keyboard = create_poll_keyboard(full_poll_data)
            
            await update.message.reply_text(
                poll_message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
            logger.info("Poll created successfully", 
                       poll_id=poll_data["id"], user_id=user_id, chat_id=chat_id)
        else:
            await update.message.reply_text("❌ Failed to display poll. Please try again.")
        
    except Exception as e:
        logger.error("Error creating poll", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text(
            "❌ Error creating poll. Please check your format and try again."
        )


@auth_check
async def list_polls_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /polls command to list active polls."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    try:
        # Get active polls for this chat
        active_polls = await voting_service.get_active_polls(chat_id=chat_id)
        
        if not active_polls:
            await update.message.reply_text(
                "📊 **No Active Polls**\n\n"
                "Create a poll with `/poll \"Question\" \"Option 1\" \"Option 2\"`",
                parse_mode="Markdown"
            )
            return
        
        message = f"📊 **Active Polls in this chat** ({len(active_polls)})\n\n"
        
        for poll in active_polls[:10]:  # Limit to 10 polls
            # Calculate time remaining
            import datetime
            time_left = poll["expires_at"] - datetime.datetime.utcnow()
            
            if time_left.total_seconds() > 0:
                hours = int(time_left.total_seconds() // 3600)
                minutes = int((time_left.total_seconds() % 3600) // 60)
                time_str = f"{hours}h {minutes}m left"
            else:
                time_str = "Expired"
            
            message += (
                f"**🗳️ Poll #{poll['id']}:** {poll['title']}\n"
                f"📊 {poll['total_votes']} votes | ⏰ {time_str}\n"
                f"👤 Created by User{str(poll['creator_id'])[-3:]}\n\n"
            )
        
        # Add quick access buttons
        if len(active_polls) <= 5:
            keyboard = []
            for poll in active_polls[:5]:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🗳️ {poll['title'][:30]}...",
                        callback_data=f"show_poll_{poll['id']}"
                    )
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(message, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("Error listing polls", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error loading polls. Please try again.")


@auth_check
async def vote_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /vote command."""
    if not update.message or not update.effective_user:
        return
    
    user_id = update.effective_user.id
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "🗳️ **Cast a Vote**\n\n"
            "**Usage:** `/vote <poll_id> <option_number>`\n"
            "**Multiple Choice:** `/vote <poll_id> 1,3,5`\n\n"
            "**Examples:**\n"
            "• `/vote 123 2` - Vote for option 2 in poll 123\n"
            "• `/vote 123 1,3` - Vote for options 1 and 3\n\n"
            "Use `/polls` to see active polls.",
            parse_mode="Markdown"
        )
        return
    
    try:
        poll_id = int(context.args[0])
        option_input = context.args[1]
        
        # Parse option IDs (support comma-separated for multiple choice)
        if "," in option_input:
            option_numbers = [int(x.strip()) for x in option_input.split(",")]
        else:
            option_numbers = [int(option_input)]
        
        # Convert to 0-based indexing
        option_ids = [num - 1 for num in option_numbers]
        
        # Validate option IDs
        for option_id in option_ids:
            if option_id < 0:
                await update.message.reply_text("❌ Option numbers must be positive.")
                return
        
        # Cast vote
        vote_result = await voting_service.vote_on_poll(poll_id, user_id, option_ids)
        
        if vote_result:
            # Get updated poll data
            poll_data = await voting_service.get_poll(poll_id)
            
            if poll_data:
                selected_options = [poll_data["options"][i] for i in option_ids 
                                 if 0 <= i < len(poll_data["options"])]
                
                action_text = "updated" if vote_result["action"] == "updated" else "cast"
                
                message = (
                    f"✅ **Vote {action_text}!**\n\n"
                    f"🗳️ **Poll:** {poll_data['title']}\n"
                    f"🎯 **Your Choice(s):** {', '.join(selected_options)}\n"
                    f"📊 **Total Votes:** {poll_data['total_votes']}"
                )
                
                await update.message.reply_text(message, parse_mode="Markdown")
            else:
                await update.message.reply_text("✅ Vote cast successfully!")
        else:
            await update.message.reply_text("❌ Failed to cast vote. Please try again.")
        
    except ValueError:
        await update.message.reply_text("❌ Invalid format. Use: `/vote <poll_id> <option_number>`")
    except APIError as e:
        await update.message.reply_text(f"❌ {str(e)}")
    except Exception as e:
        logger.error("Error casting vote", user_id=user_id, error=str(e), exc_info=True)
        await update.message.reply_text("❌ Error casting vote. Please try again.")


async def handle_voting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voting-related callback queries."""
    if not update.callback_query or not update.effective_user:
        return
    
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    try:
        if callback_data.startswith("vote_"):
            # Handle vote: vote_poll_id_option_id
            parts = callback_data.split("_")
            if len(parts) >= 3:
                poll_id = int(parts[1])
                option_id = int(parts[2])
                
                # Get current user votes to toggle
                user_votes = await voting_service.get_user_votes(user_id, poll_id)
                current_option_ids = []
                
                if user_votes:
                    current_option_ids = user_votes[0]["option_ids"]
                
                # Get poll info to check type
                poll_data = await voting_service.get_poll(poll_id)
                if not poll_data:
                    await query.answer("❌ Poll not found", show_alert=True)
                    return
                
                # Toggle vote logic
                if poll_data["allows_multiple"]:
                    # Multiple choice: toggle the option
                    if option_id in current_option_ids:
                        # Remove vote
                        new_option_ids = [oid for oid in current_option_ids if oid != option_id]
                    else:
                        # Add vote
                        new_option_ids = current_option_ids + [option_id]
                else:
                    # Single choice: replace vote
                    new_option_ids = [option_id]
                
                if not new_option_ids:
                    await query.answer("❌ You must select at least one option", show_alert=True)
                    return
                
                # Cast vote
                vote_result = await voting_service.vote_on_poll(poll_id, user_id, new_option_ids)
                
                if vote_result:
                    # Update message with new results
                    updated_poll_data = await voting_service.get_poll(poll_id)
                    if updated_poll_data:
                        user_votes = await voting_service.get_user_votes(user_id, poll_id)
                        user_option_ids = user_votes[0]["option_ids"] if user_votes else []
                        
                        poll_message = format_poll_message(updated_poll_data)
                        keyboard = create_poll_keyboard(updated_poll_data, user_option_ids)
                        
                        await query.edit_message_text(
                            poll_message,
                            reply_markup=keyboard,
                            parse_mode="Markdown"
                        )
                        
                        selected_option = updated_poll_data["options"][option_id]
                        await query.answer(f"✅ Voted for: {selected_option}")
                    else:
                        await query.answer("❌ Error updating poll", show_alert=True)
                else:
                    await query.answer("❌ Vote failed", show_alert=True)
        
        elif callback_data.startswith("refresh_poll_"):
            # Refresh poll results
            poll_id = int(callback_data.replace("refresh_poll_", ""))
            
            poll_data = await voting_service.get_poll(poll_id)
            if poll_data:
                user_votes = await voting_service.get_user_votes(user_id, poll_id)
                user_option_ids = user_votes[0]["option_ids"] if user_votes else []
                
                poll_message = format_poll_message(poll_data)
                keyboard = create_poll_keyboard(poll_data, user_option_ids)
                
                await query.edit_message_text(
                    poll_message,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                
                await query.answer("🔄 Poll refreshed!")
            else:
                await query.answer("❌ Poll not found", show_alert=True)
        
        elif callback_data.startswith("close_poll_"):
            # Close poll
            poll_id = int(callback_data.replace("close_poll_", ""))
            
            result = await voting_service.close_poll(poll_id, user_id)
            if result:
                poll_data = await voting_service.get_poll(poll_id)
                if poll_data:
                    poll_message = format_poll_message(poll_data, show_results=True)
                    
                    # Remove voting buttons, keep only results button
                    keyboard = [[
                        InlineKeyboardButton("📊 Final Results", 
                                           callback_data=f"results_poll_{poll_id}")
                    ]]
                    
                    await query.edit_message_text(
                        poll_message,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode="Markdown"
                    )
                    
                    await query.answer("🔒 Poll closed successfully!")
            else:
                await query.answer("❌ Cannot close poll", show_alert=True)
        
        elif callback_data.startswith("results_poll_"):
            # Show detailed results
            poll_id = int(callback_data.replace("results_poll_", ""))
            
            poll_data = await voting_service.get_poll(poll_id)
            if poll_data:
                results_message = format_poll_message(poll_data, show_results=True)
                await query.answer()
                await query.message.reply_text(results_message, parse_mode="Markdown")
            else:
                await query.answer("❌ Poll not found", show_alert=True)
        
        elif callback_data.startswith("show_poll_"):
            # Show specific poll
            poll_id = int(callback_data.replace("show_poll_", ""))
            
            poll_data = await voting_service.get_poll(poll_id)
            if poll_data:
                user_votes = await voting_service.get_user_votes(user_id, poll_id)
                user_option_ids = user_votes[0]["option_ids"] if user_votes else []
                
                poll_message = format_poll_message(poll_data)
                keyboard = create_poll_keyboard(poll_data, user_option_ids)
                
                await query.message.reply_text(
                    poll_message,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
                await query.answer("📊 Poll displayed!")
            else:
                await query.answer("❌ Poll not found", show_alert=True)
        
        else:
            await query.answer("❓ Unknown voting action", show_alert=True)
            
    except Exception as e:
        logger.error("Error handling voting callback", callback_data=callback_data, 
                    user_id=user_id, error=str(e), exc_info=True)
        await query.answer("❌ An error occurred", show_alert=True)