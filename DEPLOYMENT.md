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

### RapidAPI (for NSFW features):
- `RAPIDAPI_KEY` - Your RapidAPI key for NSFW content APIs (b3d94a48ffmsh77a9d7c5639d202p11fdc7jsn7b4229d8666e)

### Admin Users:
- `ADMIN_USER_IDS` - Comma-separated list of admin user IDs (e.g., "123456789,987654321")

## What This Fixes

The bot is constantly restarting because it's missing these environment variables on the server. The updated GitHub Actions workflow will now:

1. **Preserve existing `.env` files** - If a working `.env` file already exists, it won't be overwritten
2. Create a `.env` file from GitHub secrets only if missing or incomplete
3. Backup existing `.env` files with timestamp before any changes
4. Secure the file with proper permissions (600)
5. Deploy the bot with all required configuration

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

## .env File Management

The deployment process is now smart about handling `.env` files:

- **Existing files are preserved**: If you have a working `.env` file on the server (like one with RAPIDAPI_KEY), it won't be overwritten
- **Automatic backups**: Before any changes, existing `.env` files are backed up with timestamps
- **Fallback creation**: Only creates new `.env` from GitHub secrets if the file is missing or incomplete
- **Manual sync**: You can still use `./sync_env.sh` to manually sync your local `.env` to the server when needed

This prevents the issue where deployments would overwrite manually configured environment variables like `RAPIDAPI_KEY`.