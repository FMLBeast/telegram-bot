# Deployment Setup Instructions

## Required GitHub Secrets

To fix the bot constantly restarting issue, you need to add these secrets to your GitHub repository:

### Go to: Repository Settings > Secrets and Variables > Actions > New repository secret

Add the following secrets:

### Server Connection:
- `VPS_HOST` - Your server IP address (194.31.143.17)
- `VPS_USER` - Your server username (beast)  
- `VPS_KEY` - Your private SSH key (the one you created earlier)

### Bot Configuration:
- `TELEGRAM_BOT_TOKEN` - Your bot token from @BotFather
- `TELEGRAM_API_ID` - Your API ID from my.telegram.org
- `TELEGRAM_API_HASH` - Your API hash from my.telegram.org
- `BOT_USERNAME` - Your bot's username (without @)

### OpenAI:
- `OPENAI_API_KEY` - Your OpenAI API key

### Admin Users:
- `ADMIN_USER_IDS` - Comma-separated list of admin user IDs (e.g., "123456789,987654321")

## What This Fixes

The bot is constantly restarting because it's missing these environment variables on the server. The updated GitHub Actions workflow will now:

1. Create a `.env` file on the server using your GitHub secrets
2. Secure the file with proper permissions (600)
3. Deploy the bot with all required configuration

## After Adding Secrets

Once you've added all the secrets to GitHub:

1. Push any change to trigger a deployment (or re-run the last workflow)
2. The bot should start successfully and stop restarting
3. The dashboard logs should show successful startup messages
4. You can use the dashboard controls to start/stop/restart the bot

## Security Notes

- The `.env` file is never committed to git (it's in .gitignore)
- GitHub secrets are encrypted and only accessible during workflow runs
- The `.env` file on the server has restricted permissions (600 = owner read/write only)