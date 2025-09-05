# 🤖 Modern Telegram Bot

A cutting-edge, production-ready Telegram bot built with Python 3.11+, featuring AI-powered conversations, comprehensive testing, and modern development practices.

## ✨ Features

- 🧠 **AI-Powered Conversations** - GPT-4 integration for intelligent responses
- 🎨 **Image Generation** - DALL-E 3 powered image creation
- 📊 **Analytics & Monitoring** - Comprehensive logging and user analytics
- 🔒 **Security** - Rate limiting, input validation, and secure configuration
- 🗄️ **Database Integration** - Async SQLAlchemy with SQLite/PostgreSQL support
- 🧪 **Comprehensive Testing** - Unit and integration tests with 90%+ coverage
- 🚀 **Production Ready** - Docker support, CI/CD ready
- 📝 **Modern Architecture** - Clean code, type hints, async/await

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- A Telegram Bot Token ([Get one from @BotFather](https://t.me/BotFather))
- OpenAI API Key ([Get one here](https://platform.openai.com/api-keys))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/telegram-bot.git
   cd telegram-bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your tokens and configuration
   ```

5. **Run the bot**
   ```bash
   python -m bot.main
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here

# Optional
DATABASE_URL=sqlite:///./bot.db
LOG_LEVEL=INFO
ENVIRONMENT=development
WEBHOOK_URL=  # Leave empty for polling mode
```

### Advanced Configuration

The bot uses Pydantic settings for configuration management. See `bot/core/config.py` for all available options.

## 🏗️ Architecture

```
bot/
├── core/           # Core functionality
│   ├── app.py      # Main application class
│   ├── config.py   # Configuration management
│   ├── database.py # Database models and manager
│   └── logging.py  # Structured logging setup
├── handlers/       # Telegram handlers
│   ├── commands.py # Command handlers (/start, /help)
│   ├── messages.py # Message handlers
│   ├── callbacks.py# Callback query handlers
│   └── errors.py   # Error handlers
├── services/       # Business logic services
│   ├── openai_service.py  # OpenAI integration
│   └── user_service.py    # User management
├── utils/          # Utility functions
│   ├── validators.py      # Input validation
│   ├── formatters.py      # Text formatting
│   └── rate_limiter.py    # Rate limiting
└── main.py         # Entry point
```

## 🤖 Bot Commands

### Basic Commands
- `/start` - Start the bot and see welcome message
- `/help` - Show available commands and features
- `/settings` - Configure bot settings

### AI Features
- `/ask [question]` - Ask AI a question
- `/chat` - Start AI conversation mode
- `/generate [prompt]` - Generate image from text description

### Productivity
- `/todo [task]` - Add a todo item
- `/todos` - List all todos
- `/remind [time] [message]` - Set reminder
- `/stats` - Show usage statistics

## 🧪 Testing

The project includes comprehensive test coverage:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=bot --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/

# Run tests with verbose output
pytest -v
```

### Test Structure
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Fixtures**: Reusable test data and mocks
- **Coverage**: Maintains 90%+ test coverage

## 🚀 Deployment

### Using Docker

1. **Build image**
   ```bash
   docker build -t telegram-bot .
   ```

2. **Run container**
   ```bash
   docker run -d --name telegram-bot \
     --env-file .env \
     telegram-bot
   ```

### Using Docker Compose

```bash
docker-compose up -d
```

### Production Deployment

1. **Set up environment**
   ```bash
   export ENVIRONMENT=production
   export LOG_LEVEL=INFO
   # Set other production variables
   ```

2. **Use webhooks for better performance**
   ```bash
   export WEBHOOK_URL=https://yourdomain.com
   export WEBHOOK_PORT=8443
   ```

3. **Run with process manager**
   ```bash
   # Using systemd, pm2, or similar
   python -m bot.main
   ```

## 📊 Monitoring & Logging

### Structured Logging
The bot uses structured logging with different outputs for development and production:

- **Development**: Pretty console output
- **Production**: JSON formatted logs for log aggregation

### Monitoring
Built-in monitoring includes:
- User activity tracking
- Message analytics
- Error tracking
- Performance metrics

## 🔒 Security Features

### Input Validation
- Sanitizes all user inputs
- Validates command arguments
- Prevents malicious content injection

### Rate Limiting
- Per-user rate limiting
- Different limits for different operations
- Automatic cleanup of expired requests

### Security Best Practices
- No secrets in code or logs
- Environment-based configuration
- Secure error handling
- Input sanitization

## 🛠️ Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install

# Run code formatting
black bot/ tests/
isort bot/ tests/

# Run type checking
mypy bot/

# Run linting
flake8 bot/ tests/
```

### Code Style
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking
- **pytest** for testing

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## 📚 API Documentation

### OpenAI Integration
The bot integrates with OpenAI's API for:
- Text generation (GPT-4)
- Image generation (DALL-E 3)
- Content analysis

### Database Schema
```sql
-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages table  
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    telegram_message_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    text TEXT,
    message_type VARCHAR(50) DEFAULT 'text',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 Troubleshooting

### Common Issues

**Bot not responding**
- Check if bot token is correct
- Verify bot is started with `/start`
- Check logs for errors

**OpenAI errors**
- Verify API key is valid
- Check OpenAI usage limits
- Review error logs for specific issues

**Database errors**
- Ensure database file permissions are correct
- Check if database tables exist
- Verify connection string

**Rate limiting**
- Users hitting rate limits will see warning messages
- Adjust limits in configuration if needed
- Clear rate limits for testing: `rate_limiter.clear_all_limits()`

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python -m bot.main
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

- 📧 Email: [support@example.com](mailto:support@example.com)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/telegram-bot/issues)
- 💬 Telegram: [@YourBotUsername](https://t.me/YourBotUsername)

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [OpenAI](https://openai.com/) - AI API services
- [FastAPI](https://fastapi.tiangolo.com/) - Inspiration for modern Python architecture
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation and settings

---

**Made with ❤️ for the Telegram Bot community**