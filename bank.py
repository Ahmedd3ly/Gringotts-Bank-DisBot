import discord
from discord.ext import commands
import random
from datetime import datetime, timedelta
import sqlite3
from discord import app_commands
from discord import Embed, Color, SelectOption
from typing import Optional, Literal
from discord.ui import View, Button, Select
import json
import time
from contextlib import contextmanager

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Store user balances and cooldowns
class BankSystem:
    def __init__(self):
        # Set database connection parameters first
        self.max_retries = 5
        self.retry_delay = 0.1
        
        # Then load config
        with open('config.json') as f:
            self.config = json.load(f)
        
        self.currency_emoji = self.config['currency_emoji']
        self.banker_roles = self.config['banker_roles']
        self.default_work = self.config['default_work']
        self.house_emoji = self.config['house_emoji']
        
        self.work_emoji = "💼"
        self.bank_emoji = "🏦"
        self.time_emoji = "⏳"
        
        self.success_color = Color.green()
        self.error_color = Color.red()
        self.info_color = Color.blue()
        
        # Currency conversion rates
        self.SICKLES_PER_GALLEON = 17
        self.KNUTS_PER_SICKLE = 29
        self.KNUTS_PER_GALLEON = 493  # 17 * 29
        
        # Initialize database
        self.init_database()
        
        # Add work quotes
        self.work_quotes = [
            "قمت بتوصيل عدد المتنبئ للعالم السحري نيابه عن بومه الانسه رولا فكافئتك ب",
            "ساعدت الانسه رولا في تنظبم بعضا من الاوراق فكافئتك ب",
            "شاركتَ في إحدى مسابقات مكتب الألعاب، وأسفرت تعويذتك عن نشوب فوضى طريفة بين الطلاب، فقامت الآنسة ليان بلاك بمنحك ",
            "بينما تساعد كائنًا مصابًا قرب الغابة المحرمة، يلفت انتباهك غراب غريب، وفجأة، تسمع خطوات غامضة لتجد البروفيسور دارك زولديك خلفك يبتسم بلطف، يساعدك ثم يكافئك بالجاليونز، محذرًا إياك من العودة إلى الغابة.",
            "أثناء تقديم الطعام لـ سياه ، قرر أن الطعام أقل أهمية من اختبار سرعتك في الجري، فأعطتك الآنسة ليان بلاك تعويضك ب",
            "قمت بمساعدة قسم الاصلاح في عرض الطقس على الشاشة فكائفك وزا زولديك ب ",
            "قمت بالإبلاغ عن عطل فني فقام وزا زولديك بكفالتك ب",
            "ذكّرت اصدقائك ببعض القوانين الخاصة بالإلقاء التعاويذ في الحانات والنوادي فكافئك بروفيسور فيدريكو بـ",
            "قمت بلقاء صحفي رائع مع السيد لويس بانر ونالت الاسئلة أعجابه فأعطاك",
            "ساعدت السيد لويس بانر في ترتيب مكتبه فاعطاك",
            "ساعدت بعض الاورورز في القبض علي سارق في حارة دياجون فأعطاك بروفيسور فيدريكو",
            "قمت بساعدة بروف ريتشارد هاجريد في اطعام المخلوقات السحرية فأعطاك",
            "حضرت وصفة الحظ السائل بإتقان فأعطاك السيد زينو دمبلدور",
            "وجدت بعضاً من جذور الماندريك وقدمتها للسيد زينو دمبلدور فكافأك بـ",
            "اقترحت فكرة رائعة على السيد چوناه ايرنست فأعطاك",
            "كشفت مخطط لبعض اللصوص الذين يخططون لسرقة بعض الادوات السحرية المحظورة وأبلغت عنهم فتم مكافأتك ب",
            "ساعدت السيد جيمس دووم في تصنيف بعض السحرة في شجرة عائلاتهم السحرية فأعطاك",
            "`رآك الهيدماستر ديلان تعتني بشجرة الصفصاف رغم خطورتها فمنحك بقشيشًا وقال لك بجدية:`عمل جيد ولكن الخروج من القلعة دون اذن غير مقبول, اذهب لغرفة العقاب حالًا",
            "علم الهيدماستر ديلان انك مرضت وبقيت الليلة الماضية عند مدام بومفري ف ارسل لك حلوى البيرتي بوتس ومنحك"
        ]
        
        self.log_channel_id = self.config['log_channel_id']

    def init_database(self):
        with self.get_db_connection() as conn:
            c = conn.cursor()
            try:
                # Enable foreign key support
                c.execute('PRAGMA foreign_keys = ON')
                c.execute('BEGIN TRANSACTION')
                
                # Create cooldowns table first
                c.execute('''CREATE TABLE IF NOT EXISTS cooldowns
                            (user_id TEXT PRIMARY KEY,
                             work_cooldown TEXT,
                             income_cooldown TEXT)''')
                
                # Create transactions table
                c.execute('''CREATE TABLE IF NOT EXISTS transactions
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             user_id TEXT,
                             amount INTEGER,
                             type TEXT,
                             timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                             modifier_id TEXT,
                             details TEXT)''')
                
                # Create version table
                c.execute('''CREATE TABLE IF NOT EXISTS db_version
                            (version INTEGER PRIMARY KEY)''')
                
                # Get current version
                c.execute('SELECT version FROM db_version')
                result = c.fetchone()
                current_version = result[0] if result else 0
                
                # Create tables in proper order (dependencies first)
                c.execute('''CREATE TABLE IF NOT EXISTS users
                            (user_id TEXT PRIMARY KEY,
                             username TEXT,
                             galleons INTEGER DEFAULT 0,
                             sickles INTEGER DEFAULT 0,
                             knuts INTEGER DEFAULT 0,
                             favorite_spells TEXT DEFAULT '',
                             pets TEXT DEFAULT '',
                             bio TEXT DEFAULT '')''')
                
                c.execute('''CREATE TABLE IF NOT EXISTS shop_items
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             name TEXT NOT NULL,
                             price INTEGER NOT NULL,
                             category TEXT NOT NULL,
                             description TEXT,
                             properties TEXT,
                             required_role TEXT,
                             added_by TEXT NOT NULL,
                             added_timestamp TEXT DEFAULT CURRENT_TIMESTAMP)''')
                
                c.execute('''CREATE TABLE IF NOT EXISTS removed_shop_items
                            (id INTEGER PRIMARY KEY,
                             name TEXT NOT NULL,
                             price INTEGER NOT NULL,
                             category TEXT NOT NULL,
                             description TEXT,
                             properties TEXT,
                             added_by TEXT NOT NULL,
                             removed_timestamp TEXT DEFAULT CURRENT_TIMESTAMP)''')
                
                c.execute('''CREATE TABLE IF NOT EXISTS inventory
                            (id INTEGER PRIMARY KEY AUTOINCREMENT,
                             user_id TEXT NOT NULL,
                             item_id INTEGER NOT NULL,
                             properties TEXT,
                             obtained_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                             is_removed_item BOOLEAN DEFAULT 0,
                             category TEXT,
                             FOREIGN KEY(user_id) REFERENCES users(user_id))''')

                # Add indexes for performance
                c.execute('CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id)')
                c.execute('CREATE INDEX IF NOT EXISTS idx_shop_items_category ON shop_items(category)')
                
                # Add default items if needed
                if current_version < 5:
                    try:
                        # Add default wand if none exists
                        c.execute('SELECT 1 FROM shop_items WHERE category = "Wands" LIMIT 1')
                        if not c.fetchone():
                            c.execute('''INSERT INTO shop_items 
                                        (name, price, category, description, properties, added_by)
                                        VALUES (?, ?, ?, ?, ?, ?)''',
                                     ("Training Wand", 
                                      1 * self.KNUTS_PER_GALLEON,  # 1 Galleons
                                      "Wands",
                                      "A basic training wand for new students",
                                      json.dumps({
                                          "wood": "Cherry",
                                          "core": "Unicorn Hair",
                                          "length": 8.75,
                                          "flexibility": "Slightly Springy",
                                          "power": "0"
                                      }),
                                      "SYSTEM"))
                            print("Added default wand")

                        # Add default broom if none exists
                        c.execute('SELECT 1 FROM shop_items WHERE category = "Brooms" LIMIT 1')
                        if not c.fetchone():
                            c.execute('''INSERT INTO shop_items 
                                        (name, price, category, description, properties, added_by)
                                        VALUES (?, ?, ?, ?, ?, ?)''',
                                     ("Training Broom", 
                                      1 * self.KNUTS_PER_GALLEON,  # 1 Galloen
                                      "Brooms",
                                      "A reliable training broom for beginners",
                                      json.dumps({
                                          "wood": "Birch",
                                          "bristle": "Twiggy Birch",
                                          "length": 48,
                                          "speed": "0"
                                      }),
                                      "SYSTEM"))
                            print("Added default broom")

                        # Add default accessory if none exists
                        c.execute('SELECT 1 FROM shop_items WHERE category = "Accessories" LIMIT 1')
                        if not c.fetchone():
                            c.execute('''INSERT INTO shop_items 
                                        (name, price, category, description, properties, added_by)
                                        VALUES (?, ?, ?, ?, ?, ?)''',
                                     ("Basic Necklace", 
                                      1 * self.KNUTS_PER_GALLEON, # 1 Galloen
                                      "Accessories",
                                      "A simple magical necklace",
                                      json.dumps({
                                          "material": "Silver",
                                          "type": "Necklace",
                                          "enchantment": "+1 Ac"
                                      }),
                                      "SYSTEM"))
                            print("Added default accessory")
                    except Exception as e:
                        print(f"Error adding default items: {e}")
                        raise

                # Update version if needed
                if current_version < 5:
                    if current_version == 0:
                        c.execute('INSERT INTO db_version (version) VALUES (5)')
                    else:
                        c.execute('UPDATE db_version SET version = 5')
                    print("Updated database to version 5")
                
                conn.commit()
                print("Database initialization complete!")
                
            except Exception as e:
                conn.rollback()
                print(f"Error initializing database: {e}")
                raise

    def update_username(self, user_id: str, username: str):
        with self.get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''INSERT INTO users (user_id, username, galleons, sickles, knuts) 
                        VALUES (?, ?, 0, 0, 0)
                        ON CONFLICT(user_id) 
                        DO UPDATE SET username = ?''',
                     (user_id, username, username))
            conn.commit()

    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = sqlite3.connect('bank.db', timeout=60.0)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA busy_timeout=30000')
            conn.execute('PRAGMA synchronous=NORMAL')
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            raise e
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def safe_execute(self, query, params=None):
        """Safe database execution with retries"""
        retries = 0
        while retries < self.max_retries:
            try:
                with self.get_db_connection() as conn:
                    c = conn.cursor()
                    if params:
                        c.execute(query, params)
                    else:
                        c.execute(query)
                    return c.fetchall()
            except sqlite3.OperationalError as e:
                retries += 1
                if retries == self.max_retries:
                    print(f"Failed after {retries} retries: {e}")
                    raise e
                time.sleep(self.retry_delay)

    def get_balance(self, user_id: str) -> int:
        """Get total balance in knuts"""
        with self.get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT galleons, sickles, knuts FROM users WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            
            if result:
                galleons, sickles, knuts = result
                return (galleons * self.KNUTS_PER_GALLEON + 
                       sickles * self.KNUTS_PER_SICKLE + 
                       knuts)
            return 0

    def update_balance(self, user_id: str, knuts_amount: int, username: str = None):
        """Update user balance by converting to proper denominations"""
        with self.get_db_connection() as conn:
            c = conn.cursor()
            try:
                # Start transaction
                c.execute('BEGIN TRANSACTION')
                
                # Get current balance
                c.execute('SELECT galleons, sickles, knuts FROM users WHERE user_id = ?', (user_id,))
                result = c.fetchone()
                if result:
                    current_galleons, current_sickles, current_knuts = result
                else:
                    # Create new user with username if doesn't exist
                    c.execute('''INSERT INTO users (user_id, username, galleons, sickles, knuts)
                                VALUES (?, ?, 0, 0, 0)''', (user_id, username))
                    current_galleons = current_sickles = current_knuts = 0
                
                # Calculate total knuts
                total_knuts = (current_galleons * self.KNUTS_PER_GALLEON + 
                              current_sickles * self.KNUTS_PER_SICKLE + 
                              current_knuts + knuts_amount)
                
                if total_knuts < 0:
                    total_knuts = 0
                
                # Convert to denominations
                new_galleons = total_knuts // self.KNUTS_PER_GALLEON
                remaining = total_knuts % self.KNUTS_PER_GALLEON
                new_sickles = remaining // self.KNUTS_PER_SICKLE
                new_knuts = remaining % self.KNUTS_PER_SICKLE
                
                # Update database
                c.execute('''UPDATE users 
                            SET galleons = ?, sickles = ?, knuts = ?
                            WHERE user_id = ?''',
                         (new_galleons, new_sickles, new_knuts, user_id))
                
                # Commit transaction
                conn.commit()
                
                return new_galleons, new_sickles, new_knuts
                
            except Exception as e:
                conn.rollback()
                print(f"Error updating balance: {e}")
                raise

    def convert_to_all_denominations(self, knuts: int) -> tuple:
        """Convert knuts to galleons, sickles, and remaining knuts"""
        galleons = knuts // self.KNUTS_PER_GALLEON
        remaining_knuts = knuts % self.KNUTS_PER_GALLEON
        sickles = remaining_knuts // self.KNUTS_PER_SICKLE
        final_knuts = remaining_knuts % self.KNUTS_PER_SICKLE
        return (galleons, sickles, final_knuts)

    def format_currency(self, knuts: int) -> str:
        """Format currency amount into readable string"""
        if knuts <= 0:
            return f"{self.currency_emoji['knut']} **0** Knuts"
        
        galleons, sickles, knuts = self.convert_to_all_denominations(knuts)
        parts = []
        if galleons > 0:
            parts.append(f"{self.currency_emoji['galleon']} **{galleons}** Galleons")
        if sickles > 0:
            parts.append(f"{self.currency_emoji['sickle']} **{sickles}** Sickles")
        if knuts > 0 or not parts:  # Show knuts if it's the only currency or there are some
            parts.append(f"{self.currency_emoji['knut']} **{knuts}** Knuts")
        return ", ".join(parts)

    def format_currency_short(self, knuts: int) -> str:
        """Format currency amount into short readable string (e.g., 10G 5S 3K)"""
        if knuts <= 0:
            return "0K"
        
        galleons, sickles, knuts = self.convert_to_all_denominations(knuts)
        parts = []
        if galleons > 0:
            parts.append(f"{galleons}G")
        if sickles > 0:
            parts.append(f"{sickles}S")
        if knuts > 0 or not parts:  # Show knuts if it's the only currency or there are some
            parts.append(f"{knuts}K")
        return " ".join(parts)

    def normalize_currency(self, knuts: int) -> int:
        """Convert excess lower currencies to higher ones"""
        if knuts < 0:
            return 0  # Return 0 instead of negative values
            
        galleons = knuts // self.KNUTS_PER_GALLEON
        remaining_knuts = knuts % self.KNUTS_PER_GALLEON
        sickles = remaining_knuts // self.KNUTS_PER_SICKLE
        final_knuts = remaining_knuts % self.KNUTS_PER_SICKLE
        
        return (galleons * self.KNUTS_PER_GALLEON) + (sickles * self.KNUTS_PER_SICKLE) + final_knuts

    def get_cooldown(self, user_id: str, cooldown_type: str) -> str:
        try:
            with self.get_db_connection() as conn:
                c = conn.cursor()
                c.execute(f'SELECT {cooldown_type} FROM cooldowns WHERE user_id = ?', (user_id,))
                result = c.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Error getting cooldown: {e}")
            return None

    def set_cooldown(self, user_id: str, cooldown_type: str, time: str):
        try:
            with self.get_db_connection() as conn:
                c = conn.cursor()
                c.execute('''INSERT INTO cooldowns (user_id, ''' + cooldown_type + ''')
                           VALUES (?, ?)
                           ON CONFLICT(user_id) 
                           DO UPDATE SET ''' + cooldown_type + ''' = ?''',
                        (user_id, time, time))
                conn.commit()
        except Exception as e:
            print(f"Error setting cooldown: {e}")
            raise

    def log_transaction(self, user_id: str, amount: int, type: str, modifier_id: str, details: str):
        """Log a transaction with proper connection and transaction handling."""
        with self.get_db_connection() as conn:
            c = conn.cursor()
            try:
                c.execute('BEGIN TRANSACTION')
                c.execute('''INSERT INTO transactions 
                            (user_id, amount, type, timestamp, modifier_id, details)
                            VALUES (?, ?, ?, datetime('now'), ?, ?)''',
                         (user_id, amount, type, modifier_id, details))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Error logging transaction: {e}")
                raise

    def update_profile(self, user_id: str, favorite_spells: str, pets: str, bio: str):
        """Update user profile information."""
        with self.get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''UPDATE users 
                         SET favorite_spells = ?, pets = ?, bio = ?
                         WHERE user_id = ?''',
                       (favorite_spells, pets, bio, user_id))
            conn.commit()

    def get_profile(self, user_id: str) -> dict:
        """Retrieve user profile information."""
        with self.get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT username, favorite_spells, pets, bio FROM users WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            if result:
                return {
                    "username": result[0],
                    "favorite_spells": result[1],
                    "pets": result[2],
                    "bio": result[3]
                }
            return None

    def log_to_channel(self, bot, embed):
        """Send log message to the configured log channel"""
        try:
            log_channel = bot.get_channel(self.config['log_channel_id'])
            if log_channel:
                return bot.loop.create_task(log_channel.send(embed=embed))
            else:
                print(f"Could not find log channel with ID {self.config['log_channel_id']}")
        except Exception as e:
            print(f"Error sending log message: {e}")

    # Add this helper method to check if a user can afford an item
    def can_afford_item(self, user_id: str, price: int) -> bool:
        with self.get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT (galleons * ? + sickles * ? + knuts) as total_knuts 
                         FROM users WHERE user_id = ?''',
                      (self.KNUTS_PER_GALLEON, self.KNUTS_PER_SICKLE, user_id))
            result = c.fetchone()
            if not result:
                return False
            return result[0] >= price

    # Add this helper method to get item details
    def get_item_details(self, item_id: int) -> dict:
        with self.get_db_connection() as conn:
            c = conn.cursor()
            c.execute('''SELECT id, name, price, category, description, properties, required_role 
                         FROM shop_items WHERE id = ?''', (item_id,))
            result = c.fetchone()
            if not result:
                return None
            return dict(result)

    # Add this helper method to add item to inventory
    def add_to_inventory(self, user_id: str, item_id: int, category: str):
        with self.get_db_connection() as conn:
            c = conn.cursor()
            try:
                c.execute('BEGIN TRANSACTION')
                c.execute('''INSERT INTO inventory 
                            (user_id, item_id, category) 
                            VALUES (?, ?, ?)''',
                         (user_id, item_id, category))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                print(f"Error adding item to inventory: {e}")
                return False

    def process_purchase(self, user_id: str, item_id: int, category: str, price: int, name: str, description: str = None) -> bool:
        """Process a purchase atomically. Returns True if successful, False otherwise."""
        with self.get_db_connection() as conn:
            c = conn.cursor()
            try:
                # Check balance
                c.execute('''SELECT (galleons * ? + sickles * ? + knuts) as total_knuts 
                            FROM users WHERE user_id = ?''',
                         (self.KNUTS_PER_GALLEON, self.KNUTS_PER_SICKLE, user_id))
                result = c.fetchone()
                current_balance = result[0] if result else 0

                if current_balance < price:
                    return False

                # Calculate new balance
                new_total = current_balance - price
                new_galleons = new_total // self.KNUTS_PER_GALLEON
                remaining = new_total % self.KNUTS_PER_GALLEON
                new_sickles = remaining // self.KNUTS_PER_SICKLE
                new_knuts = remaining % self.KNUTS_PER_SICKLE

                # Update balance
                c.execute('''UPDATE users 
                           SET galleons = ?, sickles = ?, knuts = ?
                           WHERE user_id = ?''',
                        (new_galleons, new_sickles, new_knuts, user_id))

                # Add to inventory
                c.execute('''INSERT INTO inventory 
                           (user_id, item_id, category) 
                           VALUES (?, ?, ?)''',
                        (user_id, item_id, category))

                # Log transaction
                c.execute('''INSERT INTO transactions 
                           (user_id, amount, type, timestamp, modifier_id, details)
                           VALUES (?, ?, ?, datetime('now'), ?, ?)''',
                        (user_id, -price, 'purchase', user_id, f"Purchased {name}"))

                return True

            except Exception as e:
                print(f"Error processing purchase: {e}")
                return False

bank = BankSystem()


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    try:
        # Test database connection
        with bank.get_db_connection() as conn:
            c = conn.cursor()
            c.execute('SELECT 1')
            print("Database connection successful!")
    except Exception as e:
        print(f"Database connection error: {e}")
        return

    try:
        app_info = await bot.application_info()
        bot.owner_id = app_info.owner.id
        print(f"Bot owner ID is correct")
    except Exception as e:
        print(f"Error fetching owner ID: {e}")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_command_error(ctx, error):
    print(f"Command error: {error}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        # Convert seconds to minutes and seconds
        minutes = int(error.retry_after // 60)
        seconds = int(error.retry_after % 60)
        
        embed = Embed(
            title=f"{bank.time_emoji} Work Cooldown",
            description=f"You need to rest for **{minutes}** minutes and **{seconds}** seconds before working again!",
            color=bank.error_color
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        print(f"App command error: {error}")  # Log other errors to console
        try:
            await interaction.response.send_message(
                f"An error occurred: {str(error)}", 
                ephemeral=True
            )
        except:
            try:
                await interaction.followup.send(
                    f"An error occurred: {str(error)}", 
                    ephemeral=True
                )
            except:
                print("Could not send error message to user")

@bot.tree.command(name="work", description="Work to earn money")
@app_commands.checks.cooldown(1, 14400)  # 1 use per 4 hours (4 * 60 * 60 = 14400 seconds)
async def work(interaction: discord.Interaction):
    try:
        user_id = str(interaction.user.id)
        username = interaction.user.display_name
        current_time = datetime.now()
        
        # Check cooldown
        last_work = bank.get_cooldown(user_id, 'work_cooldown')
        if last_work:
            last_work = datetime.fromisoformat(last_work)
            if current_time < last_work + timedelta(minutes=60):
                remaining = (last_work + timedelta(minutes=60) - current_time).seconds // 60
                embed = Embed(
                    title=f"{bank.time_emoji} Work Cooldown",
                    description=f"You need to rest for **{remaining}** minutes before working again!",
                    color=bank.error_color
                )
                await interaction.response.send_message(embed=embed)
                return

        # Determine highest work role
        work_config = bank.default_work
        for role in interaction.user.roles:
            if role.id in bank.config['work_roles']:
                current_role = bank.config['work_roles'][role.id]
                # Compare roles based on max possible earnings in knuts
                current_max_knuts = current_role['max']
                if current_role['currency'] == 'galleon':
                    current_max_knuts *= bank.KNUTS_PER_GALLEON
                elif current_role['currency'] == 'sickle':
                    current_max_knuts *= bank.KNUTS_PER_SICKLE
                    
                work_max_knuts = work_config['max']
                if work_config['currency'] == 'galleon':
                    work_max_knuts *= bank.KNUTS_PER_GALLEON
                elif work_config['currency'] == 'sickle':
                    work_max_knuts *= bank.KNUTS_PER_SICKLE
                    
                if current_max_knuts > work_max_knuts:
                    work_config = current_role
        
        # Generate earnings based on role
        amount = random.randint(work_config['min'], work_config['max'])
        
        # Convert to knuts
        if work_config['currency'] == 'galleon':
            knuts_earned = amount * bank.KNUTS_PER_GALLEON
            currency_name = 'Galleons'
        elif work_config['currency'] == 'sickle':
            knuts_earned = amount * bank.KNUTS_PER_SICKLE
            currency_name = 'Sickles'
        else:
            knuts_earned = amount
            currency_name = 'Knuts'
        
        bank.update_balance(user_id, knuts_earned, username)
        bank.set_cooldown(user_id, 'work_cooldown', current_time.isoformat())
        
        current_balance = bank.get_balance(user_id)
        work_quote = random.choice(bank.work_quotes)
        
        embed = Embed(
            title=f"{bank.work_emoji} Work Complete!",
            description=work_quote,
            color=bank.success_color
        )
        embed.add_field(
            name="Earnings",
            value=f"**{amount}** {currency_name}\n({bank.format_currency(knuts_earned)})",
            inline=False
        )
        embed.add_field(
            name="New Balance",
            value=bank.format_currency(current_balance),
            inline=False
        )
        embed.set_footer(text=f"Come back in 4 hours to work again!")
        
        bank.log_transaction(
            user_id, 
            knuts_earned, 
            'work',  # Changed from 'income' to be more specific
            str(interaction.user.id),
            f"Work earnings: {amount} {currency_name}"
        )
        
        # After successful work, create and send log
        log_embed = Embed(
            title="Work Activity Log",
            description=f"{interaction.user.mention} worked and earned {bank.format_currency(knuts_earned)}",
            color=bank.info_color,
            timestamp=datetime.now()
        )
        log_embed.set_footer(text=f"User ID: {interaction.user.id}")
        
        # Send to log channel
        await bank.log_to_channel(bot, log_embed)
        
        # Send original response to user
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        print(f"Error in work command: {e}")
        await interaction.response.send_message(
            "An error occurred while processing your command. Please try again later.",
            ephemeral=True
        )

@bot.tree.command(name="collect_income", description="Collect weekly income based on your role")
async def collect_income(interaction: discord.Interaction):
    try:
        user_id = str(interaction.user.id)
        username = interaction.user.display_name
        current_time = datetime.now()
        
        # Check cooldown
        last_income = bank.get_cooldown(user_id, 'income_cooldown')
        if last_income:
            last_income = datetime.fromisoformat(last_income)
            if current_time < last_income + timedelta(weeks=1):
                days_remaining = ((last_income + timedelta(weeks=1) - current_time).days)
                hours_remaining = ((last_income + timedelta(weeks=1) - current_time).seconds // 3600)
                
                embed = Embed(
                    title=f"{bank.time_emoji} Income Cooldown",
                    description=f"You must wait **{days_remaining}** days and **{hours_remaining}** hours before collecting again!",
                    color=bank.error_color
                )
                await interaction.response.send_message(embed=embed)
                return
        
        # Find highest paying role
        highest_income = None
        highest_role = None
        highest_config = None
        
        for role in interaction.user.roles:
            role_id_str = str(role.id)
            if role_id_str in bank.config['income_roles']:
                current_role = bank.config['income_roles'][role_id_str]
                current_knuts = current_role['amount']
                
                if current_role['currency'] == 'galleon':
                    current_knuts *= bank.KNUTS_PER_GALLEON
                elif current_role['currency'] == 'sickle':
                    current_knuts *= bank.KNUTS_PER_SICKLE
                    
                if highest_income is None or current_knuts > highest_income:
                    highest_income = current_knuts
                    highest_role = role
                    highest_config = current_role
        
        # If no role-based income, use default
        if highest_income is None:
            default_config = bank.config['default_income']
            highest_income = default_config['amount']
            if default_config['currency'] == 'galleon':
                highest_income *= bank.KNUTS_PER_GALLEON
            elif default_config['currency'] == 'sickle':
                highest_income *= bank.KNUTS_PER_SICKLE
            highest_config = default_config
        
        # Update balance and set cooldown
        bank.update_balance(user_id, highest_income, username)
        bank.set_cooldown(user_id, 'income_cooldown', current_time.isoformat())
        
        # Log transaction with specific type
        bank.log_transaction(
            user_id, 
            highest_income, 
            'income',
            str(interaction.user.id),
            f"Weekly income - {'Role: ' + highest_role.name if highest_role else 'Default'}"
        )
        
        # Get new balance
        new_balance = bank.get_balance(user_id)
        
        embed = Embed(
            title=f"{bank.bank_emoji} Weekly Income Collected!",
            color=bank.success_color
        )
        
        if highest_role:
            embed.add_field(
                name="Role Income",
                value=f"Role: {highest_role.mention}\n"
                      f"Amount: **{highest_config['amount']}** {highest_config['currency'].title()}s\n"
                      f"({bank.format_currency(highest_income)})",
                inline=False
            )
        else:
            embed.add_field(
                name="Basic Income",
                value=f"Amount: **{highest_config['amount']}** {highest_config['currency'].title()}s\n"
                      f"({bank.format_currency(highest_income)})",
                inline=False
            )
        
        embed.add_field(
            name="New Balance",
            value=bank.format_currency(new_balance),
            inline=False
        )
        embed.set_footer(text="Come back next week to collect again!")
        
        # After successful income collection, before sending response, add log
        log_embed = Embed(
            title="💰 Income Collected",
            description=f"{interaction.user.mention} collected their weekly income",
            color=bank.info_color,
            timestamp=datetime.now()
        )
        
        if highest_role:
            log_embed.add_field(
                name="Role Income",
                value=f"Role: {highest_role.mention}\n"
                      f"Amount: **{highest_config['amount']}** {highest_config['currency'].title()}s\n"
                      f"({bank.format_currency(highest_income)})",
                inline=False
            )
        else:
            log_embed.add_field(
                name="Basic Income",
                value=f"Amount: **{highest_config['amount']}** {highest_config['currency'].title()}s\n"
                      f"({bank.format_currency(highest_income)})",
                inline=False
            )
        
        log_embed.set_footer(text=f"User ID: {interaction.user.id}")
        
        # Send to log channel
        await bank.log_to_channel(bot, log_embed)
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        print(f"Error in collect_income command: {e}")
        await interaction.response.send_message(
            "An error occurred while processing your command. Please try again later.",
            ephemeral=True
        )

@bot.tree.command(name="balance", description="Check your balance or another user's balance")
async def balance(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    # If no user specified, show own balance
    if user is None:
        user = interaction.user
    # If trying to view someone else's balance, check permissions
    elif user != interaction.user:
        has_permission = False
        for role in interaction.user.roles:
            if role.id in bank.banker_roles:
                has_permission = True
                break
        
        if not has_permission:
            embed = Embed(
                title="❌ Access Denied",
                description="You can only check your own balance!",
                color=bank.error_color
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    user_id = str(user.id)
    # Update username in database
    bank.update_username(user_id, user.display_name)
    
    balance_knuts = bank.get_balance(user_id)
    galleons, sickles, knuts = bank.convert_to_all_denominations(balance_knuts)
    
    embed = Embed(
        title=f"{bank.bank_emoji} Bank Statement",
        color=bank.info_color
    )
    embed.add_field(
        name=f"{bank.currency_emoji['galleon']} Galleons",
        value=f"**{galleons}**",
        inline=True
    )
    embed.add_field(
        name=f"{bank.currency_emoji['sickle']} Sickles",
        value=f"**{sickles}**",
        inline=True
    )
    embed.add_field(
        name=f"{bank.currency_emoji['knut']} Knuts",
        value=f"**{knuts}**",
        inline=True
    )
    
    if user == interaction.user:
        embed.set_footer(text=f"Account Holder: {user.display_name}")
    else:
        embed.set_footer(text=f"Account Holder: {user.display_name} | Viewed by: {interaction.user.display_name}")
    
    # Send as ephemeral message if checking own balance or if viewer is not a bank master
    is_private = user == interaction.user or not has_permission
    await interaction.response.send_message(embed=embed, ephemeral=is_private)

@bot.tree.command(name="modify_balance", description="Modify a user's balance (Bank Masters only)")
@app_commands.describe(
    user="The user whose balance to modify",
    amount="Amount to add/remove",
    currency="Currency type (Galleons, Sickles, or Knuts)"
)
async def modify_balance(interaction: discord.Interaction, user: discord.Member, amount: int, currency: Literal["Galleons", "Sickles", "Knuts"]):
    has_permission = False
    for role in interaction.user.roles:
        if role.id in bank.banker_roles:
            has_permission = True
            break
    
    if not has_permission and interaction.user.id != bot.owner_id:
        embed = Embed(
            title="❌ Access Denied",
            description="You don't have permission to modify balances!",
            color=bank.error_color
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    user_id = str(user.id)
    username = user.display_name
    
    # Convert to knuts
    if currency == "Galleons":
        knuts_amount = amount * bank.KNUTS_PER_GALLEON
    elif currency == "Sickles":
        knuts_amount = amount * bank.KNUTS_PER_SICKLE
    else:
        knuts_amount = amount
    
    # Get old balance for logging
    old_balance = bank.get_balance(user_id)
    
    # Update balance
    bank.update_balance(user_id, knuts_amount, username)
    
    # Log admin modification
    bank.log_transaction(
        user_id,
        knuts_amount,
        'admin',
        str(interaction.user.id),
        f"Admin balance modification: {amount} {currency} by {interaction.user.display_name}"
    )
    
    # Get new balance
    new_balance = bank.get_balance(user_id)
    
    embed = Embed(
        title="💰 Balance Modified",
        description=f"Modified {user.mention}'s balance",
        color=bank.success_color
    )
    
    embed.add_field(
        name="Modification",
        value=f"Added: **{amount}** {currency}\n({bank.format_currency(knuts_amount)})",
        inline=False
    )
    
    embed.add_field(
        name="Old Balance",
        value=bank.format_currency(old_balance),
        inline=False
    )
    
    embed.add_field(
        name="New Balance",
        value=bank.format_currency(new_balance),
        inline=False
    )
    
    # Create log embed
    log_embed = Embed(
        title="Balance Modification Log",
        description=f"Balance modified by {interaction.user.mention}",
        color=bank.info_color,
        timestamp=datetime.now()
    )
    log_embed.add_field(
        name="Target User",
        value=f"{user.mention} ({user.id})",
        inline=False
    )
    log_embed.add_field(
        name="Modification",
        value=f"Amount: {bank.format_currency(knuts_amount)}",
        inline=False
    )
    log_embed.add_field(
        name="New Balance",
        value=bank.format_currency(new_balance),
        inline=False
    )
    
    # Send to log channel
    await bank.log_to_channel(bot, log_embed)
    
    # Send original response
    await interaction.response.send_message(embed=embed)

# Owner-only commands - hidden from everyone else


@bot.tree.command(name="shop", description="Browse and buy items from the shop")
async def shop(interaction: discord.Interaction):
    with bank.get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT DISTINCT category FROM shop_items ORDER BY category')
        categories = c.fetchall()
        
        if not categories:
            await interaction.response.send_message("No items in shop yet!", ephemeral=True)
            return

        # Create category selection menu
        options = []
        for cat in categories:
            c.execute('SELECT COUNT(*) FROM shop_items WHERE category = ?', (cat[0],))
            count = c.fetchone()[0]
            options.append(
                SelectOption(
                    label=cat[0],
                    value=cat[0],
                    description=f"{count} items available"
                )
            )

        class ShopView(View):
            def __init__(self):
                super().__init__(timeout=60)
                self.add_item(CategorySelect(options))

        class CategorySelect(Select):
            def __init__(self, options):
                super().__init__(
                    placeholder="Choose a category",
                    options=options
                )

            async def callback(self, interaction: discord.Interaction):
                # Get items for selected category
                with bank.get_db_connection() as conn:
                    c = conn.cursor()
                    c.execute('''SELECT id, name, price, description, required_role 
                                FROM shop_items 
                                WHERE category = ?
                                ORDER BY price''', (self.values[0],))
                    items = c.fetchall()

                # Create item selection menu
                options = []
                for item in items:
                    price_text = bank.format_currency_short(item[2])  # Using new short format
                    options.append(
                        SelectOption(
                            label=f"{item[1]} ({price_text})",  # Include price in label
                            value=str(item[0]),   # id
                            description=item[3][:100] if item[3] else "No description"  # Show description instead of price
                        )
                    )

                class ItemSelect(Select):
                    def __init__(self):
                        super().__init__(
                            placeholder="Choose an item to buy",
                            options=options
                        )

                    async def callback(self, interaction: discord.Interaction):
                        item_id = int(self.values[0])
                        
                        # Get item details first
                        with bank.get_db_connection() as conn:
                            c = conn.cursor()
                            c.execute('''SELECT name, price, category, description, required_role 
                                        FROM shop_items WHERE id = ?''', (item_id,))
                            item = c.fetchone()
                            
                            if not item:
                                await interaction.response.send_message(
                                    "This item is no longer available!",
                                    ephemeral=True
                                )
                                return

                            name, price, category, description, required_role = item
                            
                            # Check if user can afford the item
                            user_balance = bank.get_balance(str(interaction.user.id))
                            if user_balance < price:
                                await interaction.response.send_message(
                                    f"You cannot afford this item! Price: {bank.format_currency(price)}",
                                    ephemeral=True
                                )
                                return

                            # Check required role if any
                            if required_role:
                                has_role = False
                                for role in interaction.user.roles:
                                    if str(role.id) == required_role:
                                        has_role = True
                                        break
                                if not has_role:
                                    await interaction.response.send_message(
                                        f"You need the <@&{required_role}> role to buy this item!",
                                        ephemeral=True
                                    )
                                    return

                        # Create confirmation buttons
                        class ConfirmPurchase(View):
                            def __init__(self):
                                super().__init__(timeout=60)

                            @discord.ui.button(label="Confirm Purchase", style=discord.ButtonStyle.green)
                            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                                try:
                                    # Process the purchase
                                    success = bank.process_purchase(
                                        str(interaction.user.id),
                                        item_id,
                                        category,
                                        price,
                                        name,
                                        description
                                    )

                                    if success:
                                            # Create success embed
                                            success_embed = Embed(
                                                title="✅ Purchase Successful!",
                                                description=f"You bought {name} for {bank.format_currency_short(price)}!",
                                                color=bank.success_color
                                            )
                                            
                                            if description:
                                                success_embed.add_field(
                                                    name="Item Description",
                                                    value=description,
                                                    inline=False
                                                )

                                            await interaction.response.edit_message(
                                                embed=success_embed,
                                                view=None
                                            )
                                    else:
                                            error_embed = Embed(
                                                title="❌ Purchase Failed",
                                            description="You cannot afford this item or an error occurred during purchase.",
                                                color=bank.error_color
                                            )
                                            await interaction.response.edit_message(
                                                embed=error_embed,
                                                view=None
                                            )

                                except Exception as e:
                                    print(f"Purchase error: {e}")
                                    error_embed = Embed(
                                        title="❌ Purchase Failed",
                                        description="An error occurred during purchase. Please try again.",
                                        color=bank.error_color
                                    )
                                    try:
                                        await interaction.response.edit_message(
                                            embed=error_embed,
                                            view=None
                                        )
                                    except:
                                        await interaction.followup.send(
                                            embed=error_embed,
                                            ephemeral=True
                                        )

                            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
                            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                                cancel_embed = Embed(
                                    title="❌ Purchase Cancelled",
                                    description="Your purchase has been cancelled.",
                                    color=bank.error_color
                                )
                                await interaction.response.edit_message(
                                    embed=cancel_embed,
                                    view=None
                                )

                        # Show purchase confirmation
                        confirm_embed = Embed(
                            title="🛍️ Confirm Purchase",
                            description=f"Are you sure you want to buy **{name}**?",
                            color=bank.info_color
                        )
                        confirm_embed.add_field(
                            name="Price",
                            value=f"{bank.format_currency_short(price)}\n({bank.format_currency(price)})",
                            inline=False
                        )
                        if description:
                            confirm_embed.add_field(
                                name="Description",
                                value=description,
                                inline=False
                            )

                        await interaction.response.edit_message(
                            embed=confirm_embed,
                            view=ConfirmPurchase()
                        )

                # Update view with item selection
                view = View()
                view.add_item(ItemSelect())
                
                # Create embed for items list
                embed = Embed(
                    title=f"🛍️ Shop - {self.values[0]}",
                    description="Select an item to purchase:",
                    color=bank.info_color
                )

                # Add items list to embed
                items_text = []
                for item in items:
                    price_text = bank.format_currency_short(item[2])
                    items_text.append(f"**{item[1]}** - {price_text}")
                    if item[3]:  # If there's a description
                        items_text.append(f"*{item[3]}*")
                    items_text.append("")  # Add blank line between items
                
                if items_text:
                    embed.description = "Select an item to purchase:\n\n" + "\n".join(items_text)
                
                await interaction.response.edit_message(embed=embed, view=view)

        # Send initial category selection
        embed = Embed(
            title="🏪 Shop Categories",
            description="Select a category to browse:",
            color=bank.info_color
        )
        
        await interaction.response.send_message(
            embed=embed,
            view=ShopView(),
            ephemeral=True
        )

@bot.tree.command(name="add_item", description="Add an item to the shop (Shop Managers only)")
async def add_item(interaction: discord.Interaction, 
                  name: str, 
                  price: int, 
                  currency: Literal["Galleons", "Sickles", "Knuts"],
                  category: str,
                  description: str,
                  required_role: Optional[str] = None):
    
    # Check if trying to add to default categories
    if category in ['Wands', 'Brooms', 'Accessories']:
        await interaction.response.send_message(
            f"Cannot add items to {category} category. Use the appropriate craft command instead:\n"
            "• `/craft_wand` for Wands\n"
            "• `/craft_broom` for Brooms\n"
            "• `/craft_accessories` for Accessories",
            ephemeral=True
        )
        return

    # Check if user has shop manager role
    has_permission = False
    for role in interaction.user.roles:
        if role.id in bank.config['shop_manager_roles']:
            has_permission = True
            break
    
    if not has_permission and interaction.user.id != bot.owner_id:
        await interaction.response.send_message(
            "You don't have permission to add shop items!",
            ephemeral=True
        )
        return
    
    # Convert to knuts
    if currency == "Galleons":
        price_in_knuts = price * bank.KNUTS_PER_GALLEON
    elif currency == "Sickles":
        price_in_knuts = price * bank.KNUTS_PER_SICKLE
    else:
        price_in_knuts = price
    
    # Add item directly
    with bank.get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO shop_items 
                    (name, price, category, description, required_role, added_by)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (name, price_in_knuts, category, description, 
                  required_role, str(interaction.user.id)))
        conn.commit()
    
    embed = Embed(
        title="✨ New Item Added",
        description=f"Added **{name}** to {category}",
        color=bank.success_color
    )
    embed.add_field(
        name="Price",
        value=f"{bank.format_currency(price_in_knuts)}",
        inline=False
    )
    if description:
        embed.add_field(
            name="Description",
            value=description,
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Add logging for item creation
    log_embed = Embed(
        title="📦 New Shop Item Added",
        description=f"{interaction.user.mention} added a new item to the shop",
        color=bank.info_color,
        timestamp=datetime.now()
    )
    log_embed.add_field(
        name="Item Details",
        value=f"**{name}**\nCategory: {category}\nPrice: {bank.format_currency(price_in_knuts)}",
        inline=False
    )
    if description:
        log_embed.add_field(
            name="Description",
            value=description,
            inline=False
        )
    if required_role:
        log_embed.add_field(
            name="Required Role",
            value=f"<@&{required_role}>",
            inline=False
        )
    log_embed.set_footer(text=f"Added by: {interaction.user.id}")
    
    # Send to log channel
    await bank.log_to_channel(bot, log_embed)

@add_item.autocomplete('category')
async def category_autocomplete(interaction: discord.Interaction, current: str):
    # Get existing categories from database, excluding default ones
    with bank.get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT DISTINCT category 
            FROM shop_items 
            WHERE category NOT IN ('Wands', 'Brooms', 'Accessories')
        ''')
        categories = [row[0] for row in c.fetchall()]
    
    # Filter categories based on what user has typed
    filtered = [
        app_commands.Choice(name=cat, value=cat)
        for cat in categories
        if current.lower() in cat.lower()
    ]
    
    # If no matches and user is typing a new category
    if not filtered and current:
        filtered.append(app_commands.Choice(name=f"Create new category: {current}", value=current))
    
    return filtered[:25]  # Discord limits to 25 choices

@bot.tree.command(name="profile", description="View your or another user's profile")
@app_commands.describe(user="The user whose profile to view")
async def profile(interaction: discord.Interaction, user: Optional[discord.Member] = None):
    target_user = user or interaction.user
    user_id = str(target_user.id)
    
    # Get user's house role
    house_roles = {
        bank.config['house_roles']['gryffindor']: ("Gryffindor", 0xAE0001),
        bank.config['house_roles']['slytherin']: ("Slytherin", 0x2A623D),
        bank.config['house_roles']['ravenclaw']: ("Ravenclaw", 0x222F5B),
        bank.config['house_roles']['hufflepuff']: ("Hufflepuff", 0xFDB347)
    }
    
    user_house = "Unsorted"
    house_color = 0x808080  # Default gray
    house_emoji = "🏰"  # Default castle emoji for unsorted users
    
    for role in target_user.roles:
        if role.id in house_roles:
            user_house, house_color = house_roles[role.id]
            house_emoji = bank.house_emoji[user_house.lower()]
            break
    
    with bank.get_db_connection() as conn:
        c = conn.cursor()
        
        # Get wand info
        c.execute('''
            SELECT COALESCE(s.name, r.name) as name, 
                   COALESCE(s.properties, r.properties) as properties
            FROM inventory i
            LEFT JOIN shop_items s ON i.item_id = s.id AND i.is_removed_item = 0
            LEFT JOIN removed_shop_items r ON i.item_id = r.id AND i.is_removed_item = 1
            WHERE i.user_id = ? AND COALESCE(s.category, r.category) = 'Wands'
        ''', (user_id,))
        wand = c.fetchone()
        
        # Get accessories (separate query)
        c.execute('''
            SELECT COALESCE(s.name, r.name) as name, 
                   COALESCE(s.properties, r.properties) as properties,
                   COALESCE(s.description, r.description) as description
            FROM inventory i
            LEFT JOIN shop_items s ON i.item_id = s.id AND i.is_removed_item = 0
            LEFT JOIN removed_shop_items r ON i.item_id = r.id AND i.is_removed_item = 1
            WHERE i.user_id = ? AND COALESCE(s.category, r.category) = 'Accessories'
            ORDER BY name
        ''', (user_id,))
        accessories = c.fetchall()
        
        # Get broom info
        c.execute('''
            SELECT COALESCE(s.name, r.name) as name, 
                   COALESCE(s.properties, r.properties) as properties
            FROM inventory i
            LEFT JOIN shop_items s ON i.item_id = s.id AND i.is_removed_item = 0
            LEFT JOIN removed_shop_items r ON i.item_id = r.id AND i.is_removed_item = 1
            WHERE i.user_id = ? AND COALESCE(s.category, r.category) = 'Brooms'
        ''', (user_id,))
        broom = c.fetchone()
        
        # Get other inventory items
        c.execute('''
            SELECT COALESCE(s.name, r.name) as name,
                   COALESCE(s.description, r.description) as description,
                   COALESCE(s.category, r.category) as category
            FROM inventory i
            LEFT JOIN shop_items s ON i.item_id = s.id AND i.is_removed_item = 0
            LEFT JOIN removed_shop_items r ON i.item_id = r.id AND i.is_removed_item = 1
            WHERE i.user_id = ? 
            AND COALESCE(s.category, r.category) NOT IN ('Wands', 'Brooms', 'Accessories')
            ORDER BY category, name
        ''', (user_id,))
        inventory_items = c.fetchall()
    
    embed = Embed(
        title=f"{target_user.display_name}'s Profile",
        color=house_color
    )
    
    # Add user info
    embed.set_thumbnail(url=target_user.display_avatar.url)
    embed.add_field(
        name="House",
        value=f"{house_emoji} {user_house}",
        inline=True
    )
    
    # Add wand info if they have one
    if wand:
        name, properties = wand
        if properties:
            wand_props = json.loads(properties)
            embed.add_field(
                name="Wand",
                value=f"{wand_props['length']} inches, {wand_props['wood']}\n"
                      f"{wand_props['core']} core, {wand_props['flexibility']}",
                inline=False
            )
    
    # Add accessories if they have any
    if accessories:
        accessories_dict = {}  # To group duplicate accessories
        for name, properties, description in accessories:
            if properties:
                props = json.loads(properties)
                key = f"{name}|{properties}"  # Use name and properties as unique key
                
                if key in accessories_dict:
                    accessories_dict[key]['count'] += 1
                else:
                    accessories_dict[key] = {
                        'name': name,
                        'props': props,
                        'description': description,
                        'count': 1
                    }
        
        if accessories_dict:
            accessories_text = []
            for acc_data in accessories_dict.values():
                acc_text = f"**{acc_data['name']}"
                if acc_data['count'] > 1:
                    acc_text += f" (x{acc_data['count']})"
                acc_text += "**\n"
                acc_text += f"Material: {acc_data['props']['material']}\n" \
                           f"Type: {acc_data['props']['type']}\n" \
                           f"Enchantment: {acc_data['props']['enchantment']}"
                if acc_data['description']:
                    acc_text += f"\n{acc_data['description']}"
                accessories_text.append(acc_text)
            
            embed.add_field(
                name="Accessories",
                value="\n\n".join(accessories_text),
                inline=False
            )
    
    # Add broom info if they have one
    if broom:
        name, properties = broom
        if properties:
            broom_props = json.loads(properties)
            embed.add_field(
                name="Broom",
                value=f"{broom_props['length']} inches, {broom_props['wood']} handle\n"
                      f"{broom_props['bristle']}, {broom_props['speed']} speed",
                inline=False
            )
    
    # Add other inventory items
    if inventory_items:
        current_category = None
        category_items = []
        
        for name, description, category in inventory_items:
            if category != current_category:
                if category_items:
                    embed.add_field(
                        name=current_category,
                        value="\n".join(category_items),
                        inline=False
                    )
                current_category = category
                category_items = []
            item_text = f"• {name}"
            if description:
                item_text += f" - {description}"
            category_items.append(item_text)
        
        if category_items:
            embed.add_field(
                name=current_category,
                value="\n".join(category_items),
                inline=False
            )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="create_wand", description="Add a wand to the shop (Shop Managers only)")
@app_commands.describe(
    name="Name of the wand",
    price="Amount to set as price",
    currency="Currency type (Galleons, Sickles, or Knuts)",
    wood="Type of wood (e.g., Oak, Holly, Yew)",
    core="Wand core (e.g., Phoenix Feather, Dragon Heartstring)",
    length="Length in inches (e.g., 11.5)",
    flexibility="Wand flexibility (e.g., Quite Flexible, Rigid)",
    power="Wand power level (e.g., Strong, Average, Exceptional)",
    required_role="Role ID required to purchase this wand (optional)"
)
async def create_wand(
    interaction: discord.Interaction, 
    name: str,
    price: int,
    currency: Literal["Galleons", "Sickles", "Knuts"],
    wood: str,
    core: str,
    length: float,
    flexibility: str,
    power: str,
    required_role: Optional[str] = None
):
    # Check if user has shop manager role
    has_permission = False
    for role in interaction.user.roles:
        if role.id in bank.config['shop_manager_roles']:
            has_permission = True
            break
    
    if not has_permission and interaction.user.id != bot.owner_id:
        await interaction.response.send_message(
            "You don't have permission to create wands!",
            ephemeral=True
        )
        return
    
    # Convert to knuts
    if currency == "Galleons":
        price_in_knuts = price * bank.KNUTS_PER_GALLEON
    elif currency == "Sickles":
        price_in_knuts = price * bank.KNUTS_PER_SICKLE
    else:
        price_in_knuts = price
    
    # Create wand properties
    properties = {
        "wood": wood,
        "core": core,
        "length": length,
        "flexibility": flexibility,
        "power": power
    }
    
    with bank.get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO shop_items 
                    (name, price, category, description, added_by, properties, required_role)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (name, 
                  price_in_knuts, 
                  "Wands",
                  f"{length} inches, {wood} with {core} core, {flexibility}, {power} power",
                  str(interaction.user.id),
                  json.dumps(properties),
                  required_role))
        conn.commit()
    
    embed = Embed(
        title="✨ New Wand Added",
        description=f"Added **{name}** to the shop",
        color=bank.success_color
    )
    embed.add_field(
        name="Price",
        value=f"**{price}** {currency}\n({bank.format_currency(price_in_knuts)})",
        inline=False
    )
    embed.add_field(
        name="Properties",
        value=f"Wood: {wood}\n"
              f"Core: {core}\n"
              f"Length: {length} inches\n"
              f"Flexibility: {flexibility}\n"
              f"Power: {power}",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

    # After successful wand creation, before sending response
    log_embed = Embed(
        title="🪄 New Wand Created",
        description=f"{interaction.user.mention} created a new wand",
        color=bank.info_color,
        timestamp=datetime.now()
    )
    log_embed.add_field(
        name="Wand Details",
        value=f"**{name}**\nPrice: {bank.format_currency(price_in_knuts)}",
        inline=False
    )
    log_embed.add_field(
        name="Properties",
        value=f"Wood: {wood}\n"
              f"Core: {core}\n"
              f"Length: {length} inches\n"
              f"Flexibility: {flexibility}\n"
              f"Power: {power}",
        inline=False
    )
    log_embed.set_footer(text=f"Created by: {interaction.user.id}")
    
    # Send to log channel
    await bank.log_to_channel(bot, log_embed)

    # Update the log embed to include required role
    log_embed.add_field(
        name="Required Role",
        value=f"<@&{required_role}>" if required_role else "None",
        inline=False
    )

@bot.tree.command(name="create_broom", description="Add a broom to the shop (Shop Managers only)")
@app_commands.describe(
    name="Name of the broom",
    price="Amount to set as price",
    currency="Currency type (Galleons, Sickles, or Knuts)",
    wood="Type of wood (e.g., Oak, Ash, Hazel)",
    bristle="Bristle material (e.g., Birch twigs, Hazel twigs)",
    length="Length in inches (e.g., 45.5)",
    speed="Speed rating (e.g., Fast, Average, Racing)",
    required_role="Role ID required to purchase this broom (optional)"
)
async def create_broom(
    interaction: discord.Interaction, 
    name: str,
    price: int,
    currency: Literal["Galleons", "Sickles", "Knuts"],
    wood: str,
    bristle: str,
    length: float,
    speed: str,
    required_role: Optional[str] = None
):
    # Check if user has shop manager role
    has_permission = False
    for role in interaction.user.roles:
        if role.id in bank.config['shop_manager_roles']:
            has_permission = True
            break
    
    if not has_permission and interaction.user.id != bot.owner_id:
        await interaction.response.send_message(
            "You don't have permission to create brooms!",
            ephemeral=True
        )
        return
    
    # Convert to knuts
    if currency == "Galleons":
        price_in_knuts = price * bank.KNUTS_PER_GALLEON
    elif currency == "Sickles":
        price_in_knuts = price * bank.KNUTS_PER_SICKLE
    else:
        price_in_knuts = price
    
    # Create broom properties
    properties = {
        "wood": wood,
        "bristle": bristle,
        "length": length,
        "speed": speed
    }
    
    with bank.get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO shop_items 
                    (name, price, category, description, added_by, properties, required_role)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (name, 
                  price_in_knuts, 
                  "Brooms",
                  f"{length} inches, {wood} handle with {bristle}, {speed} speed",
                  str(interaction.user.id),
                  json.dumps(properties),
                  required_role))
        conn.commit()
    
    embed = Embed(
        title="✨ New Broom Added",
        description=f"Added **{name}** to the shop",
        color=bank.success_color
    )
    embed.add_field(
        name="Price",
        value=f"**{price}** {currency}\n({bank.format_currency(price_in_knuts)})",
        inline=False
    )
    embed.add_field(
        name="Properties",
        value=f"Wood: {wood}\n"
              f"Bristle: {bristle}\n"
              f"Length: {length} inches\n"
              f"Speed: {speed}",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

    # After successful broom creation, before sending response
    log_embed = Embed(
        title="🧹 New Broom Created",
        description=f"{interaction.user.mention} created a new broom",
        color=bank.info_color,
        timestamp=datetime.now()
    )
    log_embed.add_field(
        name="Broom Details",
        value=f"**{name}**\nPrice: {bank.format_currency(price_in_knuts)}",
        inline=False
    )
    log_embed.add_field(
        name="Properties",
        value=f"Wood: {wood}\n"
              f"Bristle: {bristle}\n"
              f"Length: {length} inches\n"
              f"Speed: {speed}",
        inline=False
    )
    log_embed.set_footer(text=f"Created by: {interaction.user.id}")
    
    # Send to log channel
    await bank.log_to_channel(bot, log_embed)

    # Update the log embed to include required role
    log_embed.add_field(
        name="Required Role",
        value=f"<@&{required_role}>" if required_role else "None",
        inline=False
    )

@bot.tree.command(name="destroy", description="Destroy your wand, broom, or accessories")
@app_commands.describe(
    item_type="Choose which type of item to destroy"
)
async def destroy(
    interaction: discord.Interaction,
    item_type: Literal["Wand", "Broom", "Accessories"]
):
    user_id = str(interaction.user.id)
    # Fix category name handling
    category = "Accessories" if item_type == "Accessories" else f"{item_type}s"
    
   
    
    # Get item details with modified query for accessories
    with bank.get_db_connection() as conn:
        c = conn.cursor()
        
        # Get the specific items we want, checking both active and removed items
        c.execute('''
            SELECT 
                COALESCE(s.name, r.name) as name,
                COALESCE(s.properties, r.properties) as properties,
                i.id,
                COALESCE(s.category, r.category) as category
            FROM inventory i
            LEFT JOIN shop_items s ON i.item_id = s.id AND i.is_removed_item = 0
            LEFT JOIN removed_shop_items r ON i.item_id = r.id AND i.is_removed_item = 1
            WHERE i.user_id = ? 
            AND LOWER(COALESCE(s.category, r.category)) = LOWER(?)
        ''', (user_id, category))
        
        items = c.fetchall()
    
    if not items:
        await interaction.response.send_message(
            f"You don't have any {item_type.lower()} to destroy! (Category: {category})",
            ephemeral=True
        )
        return

    # If it's a wand or broom (single item), proceed directly to confirmation
    if item_type in ["Wand", "Broom"]:
        name, properties, inventory_id, _ = items[0]
        
        # Create confirmation embed
        if properties:
            props = json.loads(properties)
            if category == "Wands":
                details = f"{props['length']} inches, {props['wood']}\n" \
                         f"{props['core']} core, {props['flexibility']}\n" \
                         f"Power: {props.get('power', 'Unknown')}"
            else:  # Brooms
                details = f"{props['length']} inches, {props['wood']} handle\n" \
                         f"{props['bristle']}, {props['speed']} speed"
        else:
            details = name
        
        embed = Embed(
            title=f"🔥 Destroy {item_type}?",
            description=f"Are you sure you want to destroy your {item_type.lower()}?\n\n" \
                       f"**{name}**\n" \
                       f"*{details}*",
            color=bank.error_color
        )
        
        # Create confirmation buttons
        class ConfirmButtons(View):
            def __init__(self, inventory_id: int):
                super().__init__(timeout=60)
                self.inventory_id = inventory_id
            
            @discord.ui.button(label="Destroy", style=discord.ButtonStyle.danger)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                with bank.get_db_connection() as conn:
                    c = conn.cursor()
                    c.execute('DELETE FROM inventory WHERE id = ?', (self.inventory_id,))
                    conn.commit()
                
                result_embed = Embed(
                    title=f"💥 {item_type} Destroyed",
                    description=f"Your {item_type.lower()} has been destroyed.",
                    color=bank.error_color
                )
                await interaction.response.edit_message(embed=result_embed, view=None)
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                cancel_embed = Embed(
                    title="❌ Cancelled",
                    description=f"Your {item_type.lower()} is safe.",
                    color=bank.info_color
                )
                await interaction.response.edit_message(embed=cancel_embed, view=None)
        
        await interaction.response.send_message(
            embed=embed,
            view=ConfirmButtons(inventory_id),
            ephemeral=True
        )
    
    else:  # For accessories, show selection menu first
        # Create item selection menu
        class AccessorySelect(Select):
            def __init__(self, items):
                options = []
                for name, properties, inventory_id, _ in items:
                    description = ""
                    if properties:
                        props = json.loads(properties)
                        description = f"{props['material']} {props['type']}, {props['enchantment']}"
                    
                    options.append(
                        SelectOption(
                            label=name[:100],  # Ensure label fits Discord limit
                            value=str(inventory_id),
                            description=description[:100]  # Discord limit
                        )
                    )
                
                super().__init__(
                    placeholder="Choose an accessory to destroy",
                    options=options,
                    min_values=1,
                    max_values=1
                )
            
            async def callback(self, interaction: discord.Interaction):
                selected_id = int(self.values[0])
                selected_item = next(item for item in items if item[2] == selected_id)
                name, properties, inventory_id, _ = selected_item
                
                # Create confirmation embed
                if properties:
                    props = json.loads(properties)
                    details = f"Material: {props['material']}\n" \
                             f"Type: {props['type']}\n" \
                             f"Enchantment: {props['enchantment']}"
                else:
                    details = name
                
                embed = Embed(
                    title="🔥 Destroy Accessory?",
                    description=f"Are you sure you want to destroy this accessory?\n\n" \
                               f"**{name}**\n" \
                               f"*{details}*",
                    color=bank.error_color
                )
                
                # Create confirmation buttons
                class ConfirmButtons(View):
                    def __init__(self, inventory_id: int):
                        super().__init__(timeout=60)
                        self.inventory_id = inventory_id
                    
                    @discord.ui.button(label="Destroy", style=discord.ButtonStyle.danger)
                    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                        with bank.get_db_connection() as conn:
                            c = conn.cursor()
                            c.execute('DELETE FROM inventory WHERE id = ?', (self.inventory_id,))
                            conn.commit()
                        
                        result_embed = Embed(
                            title="💥 Accessory Destroyed",
                            description=f"Your accessory has been destroyed.",
                            color=bank.error_color
                        )
                        await interaction.response.edit_message(embed=result_embed, view=None)
                    
                    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                        cancel_embed = Embed(
                            title="❌ Cancelled",
                            description="Your accessory is safe.",
                            color=bank.info_color
                        )
                        await interaction.response.edit_message(embed=cancel_embed, view=None)
                
                await interaction.response.edit_message(
                    embed=embed,
                    view=ConfirmButtons(inventory_id)
                )
        
        # Create initial view with accessory selection
        view = View()
        view.add_item(AccessorySelect(items))
        
        embed = Embed(
            title="🗑️ Destroy Accessory",
            description="Select an accessory to destroy:",
            color=bank.info_color
        )
        
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )


@bot.tree.command(name="remove_item", description="Remove an item from the shop (Shop Managers only)")
async def remove_item(interaction: discord.Interaction, category: str):
    # Check if user has shop manager role
    has_permission = False
    for role in interaction.user.roles:
        if role.id in bank.config['shop_manager_roles']:
            has_permission = True
            break
    
    if not has_permission and interaction.user.id != bot.owner_id:
        await interaction.response.send_message(
            "You don't have permission to remove shop items!",
            ephemeral=True
        )
        return
    
    with bank.get_db_connection() as conn:
        c = conn.cursor()
        # Get items from shop
        c.execute('''SELECT id, name, price, description 
                    FROM shop_items 
                    WHERE category = ?
                    ORDER BY name''', (category,))
        items = c.fetchall()
    
    if not items:
        await interaction.response.send_message(
            f"No items found in category '{category}'!",
            ephemeral=True
        )
        return
    
    # Create item selection menu
    class ItemSelect(Select):
        def __init__(self, items):
            options = []
            for item_id, name, price, description in items:
                # Create shorter price description
                galleons = price // bank.KNUTS_PER_GALLEON
                remaining = price % bank.KNUTS_PER_GALLEON
                sickles = remaining // bank.KNUTS_PER_SICKLE
                knuts = remaining % bank.KNUTS_PER_SICKLE
                
                price_text = []
                if galleons > 0:
                    price_text.append(f"{galleons}G")
                if sickles > 0:
                    price_text.append(f"{sickles}S")
                if knuts > 0:
                    price_text.append(f"{knuts}K")
                price_desc = " ".join(price_text) or "0K"
                
                options.append(
                    SelectOption(
                        label=name,
                        value=str(item_id),
                        description=price_desc
                    )
                )
            
            super().__init__(
                placeholder="Choose an item to remove from shop",
                options=options
            )
        
        async def callback(self, interaction: discord.Interaction):
            with bank.get_db_connection() as conn:
                c = conn.cursor()
                # Get item details
                c.execute('''SELECT id, name, price, description 
                            FROM shop_items 
                            WHERE id = ?''', (int(self.values[0]),))
                item = c.fetchone()
                
                if not item:
                    await interaction.response.send_message(
                        "Item not found! It may have been already removed.",
                        ephemeral=True
                    )
                    return
                
                item_id, name, price, description = item
                
                # Check how many players own this item
                c.execute('SELECT COUNT(*) FROM inventory WHERE item_id = ?', (item_id,))
                owned_count = c.fetchone()[0]
                
                # Create confirmation embed
                embed = Embed(
                    title="❌ Remove from Shop?",
                    description=f"Are you sure you want to remove **{name}** from the shop?\n\n"
                               f"**Category:** {category}\n"
                               f"**Price:** {bank.format_currency(price)}\n"
                               f"**Description:** {description or 'None'}\n"
                               f"**Currently owned by:** {owned_count} users\n\n"
                               "Note: Players who own this item will keep it in their inventory.",
                    color=bank.error_color
                )
                
                # Create confirmation buttons
                class ConfirmButtons(View):
                    def __init__(self):
                        super().__init__(timeout=60)
                    
                    @discord.ui.button(label="Remove", style=discord.ButtonStyle.danger)
                    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                        try:
                            with bank.get_db_connection() as conn:
                                c = conn.cursor()
                                try:
                                    # First get all item details
                                    c.execute('''SELECT * FROM shop_items WHERE id = ?''', (item_id,))
                                    item_data = c.fetchone()
                                    
                                    if not item_data:
                                        await interaction.response.edit_message(
                                            content="Item not found! It may have been already removed.",
                                            view=None
                                        )
                                        return

                                    # Move item to removed_shop_items
                                    c.execute('''INSERT INTO removed_shop_items 
                                               (id, name, price, category, description, properties, added_by)
                                               VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                            (item_data['id'], item_data['name'], item_data['price'],
                                             item_data['category'], item_data['description'],
                                             item_data['properties'], item_data['added_by']))

                                    # Update inventory records to mark them as removed
                                    c.execute('''UPDATE inventory 
                                               SET is_removed_item = 1 
                                               WHERE item_id = ?''', (item_id,))

                                    # Now delete from shop_items
                                    c.execute('DELETE FROM shop_items WHERE id = ?', (item_id,))

                                    # Create log embed
                                    log_embed = Embed(
                                        title="🗑️ Shop Item Removed",
                                        description=f"**{name}** was removed from the shop by {interaction.user.mention}",
                                        color=bank.info_color,
                                        timestamp=datetime.now()
                                    )
                                    log_embed.add_field(
                                        name="Item Details",
                                        value=f"Category: {category}\nPrice: {bank.format_currency(price)}",
                                        inline=False
                                    )
                                    log_embed.add_field(
                                        name="Current Owners",
                                        value=f"{owned_count} players keep their items",
                                        inline=False
                                    )
                                    log_embed.set_footer(text=f"Removed by: {interaction.user.id}")
                                    
                                    # Send to log channel
                                    await bank.log_to_channel(bot, log_embed)
                                    
                                    result_embed = Embed(
                                        title="✅ Item Removed from Shop",
                                        description=f"**{name}** has been removed from the shop.\n"
                                                   f"All {owned_count} current owners keep their items.",
                                        color=bank.success_color
                                    )
                                    await interaction.response.edit_message(
                                        embed=result_embed,
                                        view=None
                                    )
                                    
                                except Exception as e:
                                    print(f"Error removing item: {e}")
                                    await interaction.response.edit_message(
                                        content="An error occurred while removing the item.",
                                        view=None
                                    )
                        except Exception as e:
                            print(f"Error removing item: {e}")
                            await interaction.response.edit_message(
                                content="An error occurred while removing the item.",
                                view=None
                            )
                
                    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                        await interaction.response.edit_message(
                            content="Item removal cancelled.",
                            view=None
                        )
                
                await interaction.response.edit_message(
                    embed=embed,
                    view=ConfirmButtons()
                )
    
    # Create initial view with item selection
    view = View()
    view.add_item(ItemSelect(items))
    
    embed = Embed(
        title=f"🗑️ Remove Item from {category}",
        description="Select an item to remove from the shop:",
        color=bank.info_color
    )
    
    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )

@remove_item.autocomplete('category')
async def remove_category_autocomplete(interaction: discord.Interaction, current: str):
    with bank.get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT DISTINCT category FROM shop_items')
        categories = [row[0] for row in c.fetchall()]
    
    return [
        app_commands.Choice(name=cat, value=cat)
        for cat in categories
        if current.lower() in cat.lower()
    ][:25]

@bot.tree.command(name="craft_accessories", description="Create a custom accessory (Shop Managers only)")
@app_commands.describe(
    name="Name of the accessory",
    price="Amount to set as price",
    currency="Currency type (Galleons, Sickles, or Knuts)",
    material="Material of the accessory (e.g., Gold, Silver, Bronze)",
    type="Type of accessory (e.g., Necklace, Ring, Bracelet)",
    enchantment="Magical property of the accessory",
    description="Description of the accessory",
    required_role="Role ID required to purchase this accessory (optional)"
)
async def craft_accessories(
    interaction: discord.Interaction,
    name: str,
    price: int,
    currency: Literal["Galleons", "Sickles", "Knuts"],
    material: str,
    type: str,
    enchantment: str,
    description: str,
    required_role: Optional[str] = None
):
    # Check if user has shop manager role
    has_permission = False
    for role in interaction.user.roles:
        if role.id in bank.config['shop_manager_roles']:
            has_permission = True
            break
    
    if not has_permission and interaction.user.id != bot.owner_id:
        await interaction.response.send_message(
            "You don't have permission to craft accessories!",
            ephemeral=True
        )
        return
    
    # Convert to knuts
    if currency == "Galleons":
        price_in_knuts = price * bank.KNUTS_PER_GALLEON
    elif currency == "Sickles":
        price_in_knuts = price * bank.KNUTS_PER_SICKLE
    else:
        price_in_knuts = price
    
    # Create accessory properties
    properties = {
        "material": material,
        "type": type,
        "enchantment": enchantment
    }
    
    with bank.get_db_connection() as conn:
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO shop_items 
                        (name, price, category, description, properties, added_by, required_role)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (name, 
                      price_in_knuts, 
                      "Accessories",
                      description,
                      json.dumps(properties),
                      str(interaction.user.id),
                      required_role))
            
            conn.commit()
            
            # Create confirmation embed
            embed = Embed(
                title="✨ New Accessory Created",
                description=f"Added **{name}** to the shop",
                color=bank.success_color
            )
            
            embed.add_field(
                name="Price",
                value=bank.format_currency(price_in_knuts),
                inline=False
            )
            
            embed.add_field(
                name="Properties",
                value=f"Material: {material}\n"
                      f"Type: {type}\n"
                      f"Enchantment: {enchantment}",
                inline=False
            )
            
            if description:
                embed.add_field(
                    name="Description",
                    value=description,
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
            # After successful accessory creation, before sending response
            log_embed = Embed(
                title="✨ New Accessory Created",
                description=f"{interaction.user.mention} created a new accessory",
                color=bank.info_color,
                timestamp=datetime.now()
            )
            log_embed.add_field(
                name="Accessory Details",
                value=f"**{name}**\nPrice: {bank.format_currency(price_in_knuts)}",
                inline=False
            )
            log_embed.add_field(
                name="Properties",
                value=f"Material: {material}\n"
                      f"Type: {type}\n"
                      f"Enchantment: {enchantment}",
                inline=False
            )
            if description:
                log_embed.add_field(
                    name="Description",
                    value=description,
                    inline=False
                )
            log_embed.set_footer(text=f"Created by: {interaction.user.id}")
            
            # Send to log channel
            await bank.log_to_channel(bot, log_embed)
            
            # Update the log embed to include required role
            log_embed.add_field(
                name="Required Role",
                value=f"<@&{required_role}>" if required_role else "None",
                inline=False
            )
            
        except Exception as e:
            conn.rollback()
            print(f"Error creating accessory: {e}")
            await interaction.response.send_message(
                "An error occurred while creating the accessory.",
                ephemeral=True
            )
@bot.tree.command(name="leaderboard", description="Show various leaderboards")
async def leaderboard(interaction: discord.Interaction, category: Literal["wealth", "transactions", "income"]):
    # Check if user has banker role
    has_permission = False
    for role in interaction.user.roles:
        if role.id in bank.banker_roles:
            has_permission = True
            break
    
    if not has_permission and interaction.user.id != bot.owner_id:
        await interaction.response.send_message(
            "You don't have permission to use this command! Only Bank Masters can view leaderboards.",
            ephemeral=True
        )
        return

    with bank.get_db_connection() as conn:
        c = conn.cursor()
        
        if category == "wealth":
            c.execute('''
                SELECT username, (galleons * ? + sickles * ? + knuts) as total
                FROM users 
                ORDER BY total DESC LIMIT 10
            ''', (bank.KNUTS_PER_GALLEON, bank.KNUTS_PER_SICKLE))
            title = "🏆 Wealthiest Users"
        
        elif category == "transactions":
            c.execute('''
                SELECT u.username, COUNT(*) as count
                FROM transactions t
                JOIN users u ON t.user_id = u.user_id
                GROUP BY t.user_id
                ORDER BY count DESC LIMIT 10
            ''')
            title = "🔄 Most Active Users"
        
        else:  # income
            c.execute('''
                SELECT u.username, SUM(amount) as total
                FROM transactions t
                JOIN users u ON t.user_id = u.user_id
                WHERE type = 'income'
                GROUP BY t.user_id
                ORDER BY total DESC LIMIT 10
            ''')
            title = "💰 Highest Earners"
        
        results = c.fetchall()

    embed = Embed(title=title, color=bank.info_color)
    
    for i, (name, value) in enumerate(results, 1):
        if category == "transactions":
            embed.add_field(
                name=f"#{i} {name}",
                value=f"**{value}** transactions",
                inline=False
            )
        else:
            embed.add_field(
                name=f"#{i} {name}",
                value=bank.format_currency(value),
                inline=False
            )

    await interaction.response.send_message(embed=embed)  # Removed ephemeral=True to make it visible to all
@bot.tree.command(name="use", description="Use an item from your inventory")
async def use(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    # Get usable items from inventory (excluding main equipment)
    with bank.get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT i.id, 
                   COALESCE(s.name, r.name) as name,
                   COALESCE(s.description, r.description) as description,
                   COALESCE(s.category, r.category) as category,
                   COALESCE(s.properties, r.properties) as properties
            FROM inventory i
            LEFT JOIN shop_items s ON i.item_id = s.id AND i.is_removed_item = 0
            LEFT JOIN removed_shop_items r ON i.item_id = r.id AND i.is_removed_item = 1
            WHERE i.user_id = ? 
            AND COALESCE(s.category, r.category) NOT IN ('Wands', 'Brooms', 'Accessories')
        ''', (user_id,))
        
        items = c.fetchall()
    
    if not items:
        await interaction.response.send_message(
            "You don't have any usable items in your inventory!",
            ephemeral=True
        )
        return

    # Create item selection menu
    class ItemSelect(Select):
        def __init__(self, items):
            options = []
            for item_id, name, description, category, _ in items:
                options.append(
                    SelectOption(
                        label=name[:100],
                        value=str(item_id),
                        description=f"{category}: {description[:100] if description else 'No description'}"
                    )
                )
            
            super().__init__(
                placeholder="Choose an item to use",
                options=options,
                min_values=1,
                max_values=1
            )
        
        async def callback(self, interaction: discord.Interaction):
            selected_id = int(self.values[0])
            selected_item = next(item for item in items if item[0] == selected_id)
            item_id, name, description, category, properties = selected_item
            
            # Create confirmation embed
            embed = Embed(
                title="🎯 Use Item?",
                description=f"Are you sure you want to use **{name}**?\n\n" \
                           f"Category: {category}\n" \
                           f"*{description if description else 'No description'}*\n\n" \
                           "This item will be consumed upon use.",
                color=bank.info_color
            )
            
            # Create confirmation buttons
            class ConfirmButtons(View):
                def __init__(self):
                    super().__init__(timeout=60)
                
                @discord.ui.button(label="Use", style=discord.ButtonStyle.primary)
                async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                    try:
                        with bank.get_db_connection() as conn:
                            c = conn.cursor()
                            # Remove item from inventory
                            c.execute('DELETE FROM inventory WHERE id = ?', (item_id,))
                            conn.commit()
                        
                        # Create success embed
                        result_embed = Embed(
                            title="✨ Item Used",
                            description=f"You used your **{name}**!",
                            color=bank.success_color
                        )
                        
                        # Create log embed
                        log_embed = Embed(
                            title="🎯 Item Usage Log",
                            description=f"{interaction.user.mention} used an item",
                            color=bank.info_color,
                            timestamp=datetime.now()
                        )
                        log_embed.add_field(
                            name="Item Used",
                            value=f"**{name}**\nCategory: {category}",
                            inline=False
                        )
                        if description:
                            log_embed.add_field(
                                name="Description",
                                value=description,
                                inline=False
                            )
                        log_embed.set_footer(text=f"User ID: {interaction.user.id}")
                        
                        # Send to log channel
                        await bank.log_to_channel(bot, log_embed)
                        
                        await interaction.response.edit_message(
                            embed=result_embed,
                            view=None
                        )
                        
                    except Exception as e:
                        print(f"Error using item: {e}")
                        error_embed = Embed(
                            title="❌ Error",
                            description="An error occurred while using the item.",
                            color=bank.error_color
                        )
                        await interaction.response.edit_message(
                            embed=error_embed,
                            view=None
                        )
                
                @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                    cancel_embed = Embed(
                        title="❌ Cancelled",
                        description="Item use cancelled.",
                        color=bank.info_color
                    )
                    await interaction.response.edit_message(
                        embed=cancel_embed,
                        view=None
                    )
            
            await interaction.response.edit_message(
                embed=embed,
                view=ConfirmButtons()
            )
    
    # Create initial view with item selection
    view = View()
    view.add_item(ItemSelect(items))
    
    embed = Embed(
        title="🎯 Use Item",
        description="Select an item to use from your inventory:",
        color=bank.info_color
    )
    
    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )

# Load config
with open('config.json') as f:
    config = json.load(f)

# Replace the last line with:
bot.run(config['token'])

