# Overview

This is a Discord bot built with discord.py that provides basic server interaction and utility commands. The bot responds to text commands with a `!` prefix and includes welcome messages for new members, latency checking, and server information display functionality.

**Created**: October 2025
**Available Commands**: !ping, !hello, !info, !commandes

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework
- **Technology**: discord.py library with commands extension
- **Command System**: Prefix-based commands using `!` as the trigger
- **Intent Configuration**: Configured with `message_content` and `members` intents to enable message reading and member event tracking
- **Rationale**: discord.py is the standard Python library for Discord bot development, providing a robust and well-documented API wrapper

## Command Structure
- **Pattern**: Command extension framework (`commands.Bot`)
- **Event Handlers**: Asynchronous event listeners for `on_ready` and `on_member_join`
- **Custom Commands**: Decorator-based command registration (`@bot.command`)
- **Rationale**: The commands extension simplifies command creation and provides built-in parsing, making the codebase more maintainable

## Authentication
- **Method**: Discord bot token loaded from environment variables
- **Security**: Token stored in `.env` file and loaded via python-dotenv
- **Rationale**: Environment variables prevent hardcoding sensitive credentials and allow for different tokens across development/production environments

## Message Handling
- **Welcome System**: Automatic greeting messages sent to system channel when members join
- **Response Pattern**: Context-based responses using the `ctx` parameter
- **Embed Support**: Rich embeds for formatted information display (server info command)
- **Rationale**: Provides both simple text responses and rich formatted output depending on command complexity

# External Dependencies

## Core Libraries
- **discord.py**: Discord API wrapper for bot functionality
- **python-dotenv**: Environment variable management for configuration

## Discord Platform
- **API Integration**: Full Discord API access via bot token
- **Required Permissions**: Message content reading, member tracking, message sending
- **Gateway Intents**: `message_content` and `members` intents must be enabled in Discord Developer Portal

## Configuration
- **Environment Variables**: `DISCORD_TOKEN` (implied but not explicitly shown in code)
- **Runtime Environment**: Requires Python 3.8+ for discord.py compatibility