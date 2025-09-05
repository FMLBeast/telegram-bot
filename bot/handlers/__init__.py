"""Bot handlers."""

from .commands import start_handler, help_handler, menu_handler
from .messages import message_handler, ask_gpt_handler
from .callbacks import callback_handler
from .errors import error_handler
from .admin import (
    grant_access_handler,
    revoke_access_handler,
    list_authorized_channels_handler,
    ban_user_handler,
    unban_user_handler,
    make_admin_handler,
    request_access_handler,
)
from .images import (
    draw_me_handler,
    draw_multiple_handler,
    view_personal_collection_handler,
    view_group_collection_handler,
    image_stats_handler,
)
from .image_callbacks import handle_image_callback
from .todo import (
    list_todos_handler,
    add_todo_handler,
    complete_todo_handler,
    remove_todo_handler,
    todo_stats_handler,
    handle_todo_callback,
)
from .timezone import (
    set_timezone_handler,
    search_timezone_handler,
    my_time_handler,
    remind_me_handler,
    list_reminders_handler,
    cancel_reminder_handler,
    handle_timezone_callback,
)
from .crypto import (
    crypto_price_handler,
    crypto_bet_handler,
    crypto_balance_handler,
    crypto_bets_handler,
    crypto_leaderboard_handler,
    crypto_convert_handler,
    handle_crypto_callback,
)
from .mines import (
    mines_calculator_handler,
    mines_compare_handler,
    handle_mines_callback,
)
from .b2b import (
    b2b_calculator_handler,
    handle_b2b_callback,
)
from .nsfw import (
    random_boobs_handler,
    show_me_handler,
    gimme_handler,
    handle_nsfw_callback,
)
from .gambling import (
    casino_handler,
    bet_handler,
    handle_gambling_callback,
)
from .voting import (
    create_poll_handler,
    list_polls_handler,
    vote_handler,
    handle_voting_callback,
)

__all__ = [
    # Basic handlers
    "start_handler",
    "help_handler",
    "menu_handler",
    "message_handler",
    "ask_gpt_handler",
    "callback_handler",
    "error_handler",
    # Admin handlers
    "grant_access_handler",
    "revoke_access_handler",
    "list_authorized_channels_handler",
    "ban_user_handler",
    "unban_user_handler",
    "make_admin_handler",
    "request_access_handler",
    # Image handlers
    "draw_me_handler",
    "draw_multiple_handler",
    "view_personal_collection_handler",
    "view_group_collection_handler",
    "image_stats_handler",
    "handle_image_callback",
    # Todo handlers
    "list_todos_handler",
    "add_todo_handler",
    "complete_todo_handler",
    "remove_todo_handler",
    "todo_stats_handler",
    "handle_todo_callback",
    # Timezone handlers
    "set_timezone_handler",
    "search_timezone_handler",
    "my_time_handler",
    "remind_me_handler",
    "list_reminders_handler",
    "cancel_reminder_handler",
    "handle_timezone_callback",
    # Crypto handlers
    "crypto_price_handler",
    "crypto_bet_handler",
    "crypto_balance_handler",
    "crypto_bets_handler",
    "crypto_leaderboard_handler",
    "crypto_convert_handler",
    "handle_crypto_callback",
    # Mines handlers
    "mines_calculator_handler",
    "mines_compare_handler",
    "handle_mines_callback",
    # B2B handlers
    "b2b_calculator_handler",
    "handle_b2b_callback",
    # NSFW handlers
    "random_boobs_handler",
    "show_me_handler",
    "gimme_handler",
    "handle_nsfw_callback",
    # Gambling handlers
    "casino_handler",
    "bet_handler",
    "handle_gambling_callback",
    # Voting handlers
    "create_poll_handler",
    "list_polls_handler",
    "vote_handler",
    "handle_voting_callback",
]