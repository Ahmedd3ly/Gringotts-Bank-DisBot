# Hogwarts Economy Discord Bot

A feature-rich Discord bot that implements a magical economy system inspired by the Harry Potter universe, complete with currency management, item shops, and inventory systems.

## Currency System

The bot uses the canonical Harry Potter currency system:
- Galleons (G) - Most valuable
- Sickles (S) - 1 Galleon = 17 Sickles
- Knuts (K) - 1 Sickle = 29 Knuts (1 Galleon = 493 Knuts)

## Commands

### Economy Commands

#### `/work`
- Earn money by working (cooldown: 4 hours)
- Earnings vary based on your roles
- Default earnings: 30-61 Knuts
- House-based earnings:
  - All Houses: 30-61 Knuts
- Shows a fun work-related message each time

#### `/collect_income`
- Collect weekly income based on your role
- House-based weekly income:
  - First House: 18,488 Knuts (≈ 37 Galleons, 8 Sickles, 5 Knuts)
  - Second House: 15,407 Knuts (≈ 31 Galleons, 4 Sickles, 24 Knuts)
  - Third House: 12,325 Knuts (≈ 25 Galleons, 0 Sickles, 14 Knuts)
  - Fourth House: 9,244 Knuts (≈ 18 Galleons, 13 Sickles, 3 Knuts)
- Default income: 3,082 Knuts (≈ 6 Galleons, 4 Sickles, 21 Knuts)
- Cooldown: 7 days
- Shows detailed breakdown of earnings

#### `/balance [user]`
- Check your balance or another user's balance (if you have banker role)
- Shows detailed breakdown in Galleons, Sickles, and Knuts
- Private by default unless checking as a banker

#### `/modify_balance` (Bank Masters Only)
- Modify a user's balance
- Can add or remove currency
- Requires special banker role
- Logs all modifications

#### `/leaderboard` (Bank Masters Only)
- View different types of leaderboards
- Categories:
  - wealth: Shows top 10 wealthiest users
  - transactions: Shows top 10 most active users
  - income: Shows top 10 highest earners
- Results visible to all users
- Requires Bank Master role to execute

### Shop System

#### `/shop`
- Browse and buy items from the shop
- Items are organized by categories
- Shows prices and descriptions
- Confirms purchases before processing

#### Item Categories:
1. Wands
2. Brooms
3. Accessories
4. Custom categories

### Shop Management Commands (Shop Managers Only)

#### `/add_item`
- Add a new item to the shop
- Parameters:
  - Name
  - Price
  - Currency type
  - Category
  - Description
  - Required role (optional)

#### `/create_wand`
- Create a custom wand
- Parameters:
  - Name
  - Price
  - Wood type
  - Core type
  - Length
  - Flexibility
  - Power level
  - Required role (optional)

#### `/create_broom`
- Create a custom broom
- Parameters:
  - Name
  - Price
  - Wood type
  - Bristle material
  - Length
  - Speed rating
  - Required role (optional)

#### `/craft_accessories`
- Create custom accessories
- Parameters:
  - Name
  - Price
  - Material
  - Type
  - Enchantment
  - Description
  - Required role (optional)

#### `/remove_item`
- Remove items from the shop
- Preserves items for current owners
- Moves items to a removed items table

### Inventory Management

#### `/profile [user]`
- View your or another user's profile
- Shows:
  - House affiliation
  - Equipped wand
  - Equipped broom
  - Accessories
  - Other inventory items

#### `/destroy`
- Destroy items from your inventory
- Categories:
  - Wand
  - Broom
  - Accessories
- Requires confirmation

#### `/use`
- Use consumable items from your inventory
- Excludes wands, brooms, and accessories
- Shows item effects
- Requires confirmation

## Role-Based Permissions

### Bank Masters
- Can view others' balances
- Can modify balances
- Can see transaction logs

### Shop Managers
- Can add items to shop
- Can remove items from shop
- Can create custom items

## Database Structure

The bot uses SQLite with the following main tables:
1. `users` - User data and balances
2. `cooldowns` - Command cooldown tracking
3. `transactions` - Transaction history
4. `shop_items` - Available shop items
5. `removed_shop_items` - Archived shop items
6. `inventory` - User inventories

## Configuration

The bot uses a `config.json` file for settings:
- Currency emoji
- Banker roles
- Shop manager roles
- House roles
- Work roles and rewards
- Income roles and amounts
- Default work/income values
- Log channel ID

## Logging System

All important actions are logged:
- Balance modifications
- Item purchases
- Item removals
- Item usage
- Income collection
- Work activity

## Setup Instructions

1. Create a `config.json` file with required settings
2. Set up the Discord bot token
3. Install required dependencies
4. Run the bot

## Required Permissions

The bot needs these Discord permissions:
- Read Messages
- Send Messages
- Embed Links
- Use External Emojis
- Add Reactions
- View Channels

## Error Handling

The bot includes comprehensive error handling:
- Command cooldowns
- Insufficient funds
- Missing permissions
- Database errors
- Invalid inputs

## Security Features

- Role-based access control
- Transaction logging
- Atomic database operations
- Confirmation for destructive actions
- Protected admin commands 