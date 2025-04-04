import requests
from bs4 import BeautifulSoup
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import re

BOT_TOKEN = "8110311373:AAHP9rp0bcOKUxfZAOCJvjuFHcJrKqo9hSc"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

CHANNEL_USERNAME = "@kalyaScripts"  # Your public channel username
PRIVATE_CHANNEL_LINK = "https://t.me/+iNXZ7iqwmLMyNDg1"  # Your private channel link
OWNER_USER_ID = "1721139930"  # Your user ID
OWNER_CHAT_ID = "1721139930"  # Your chat ID for payment verification
UPI_ID = "gadge7@fam"  # Your UPI ID

# Store crypto addresses
crypto_addresses = {
    'btc': '',
    'ltc': '',
    'usdt': ''
}

# Store temporary invite links
temp_invite_links = {}

# User data storage
user_data = {}  # Format: {user_id: {'points': 0, 'referred_by': None, 'binance_id': '', 'points_used': 0}}

# Payment verification tracking
payment_verification = {}

# Price lists
INDIAN_PRICES = {
    '1d': 100,
    '3d': 250,
    '7d': 450,
    '15d': 650,
    '1m': 1300,
    '2m': 1800,
    '1y': 3500,
    'forever': 10000
}

FOREIGN_PRICES = {
    '1d': 3,
    '3d': 5,
    '7d': 8,
    '15d': 10,
    '1m': 15,
    '2m': 20,
    '1y': 59,
    'forever': 69
}

# Point system
POINT_SYSTEM = {
    '1d': {'points': 30, 'keys': 1, 'max_uses': 1},
    '3d': {'points': 80, 'keys': 2, 'max_uses': 1},
    '7d': {'points': 120, 'keys': 1, 'max_uses': 1}
}

def create_temp_invite_link(user_id):
    CHANNEL_ID = -1002500617770
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/createChatInviteLink"
    data = {
        "chat_id": CHANNEL_ID,
        "expire_date": 0,  
        "member_limit": 1  
    }
    
    response = requests.post(url, json=data)
    result = response.json()
    
    if result.get("ok"):
        return result["result"]["invite_link"]
    else:
        return f"Error: {result}"


# ==================== CORE FUNCTIONS ====================

def check_channel_membership(user_id):
    """Check if user is member of public channel"""
    try:
        chat_member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking membership: {e}")
        return False

def show_channel_join_alert(message):
    """Show alert to join channel"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
    markup.add(InlineKeyboardButton("✅ I've Joined", callback_data="verify_join"))
    
    if isinstance(message, telebot.types.CallbackQuery):
        try:
            bot.edit_message_text(
                chat_id=message.message.chat.id,
                message_id=message.message.message_id,
                text="⚠️ Please join our channel first to use this bot!",
                reply_markup=markup
            )
        except:
            bot.send_message(message.message.chat.id, "⚠️ Please join our channel first to use this bot!", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "⚠️ Please join our channel first to use this bot!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify_join_callback(call):
    """Verify user has joined channel"""
    try:
        if check_channel_membership(call.from_user.id):
            bot.answer_callback_query(call.id, "✅ Verification successful!")
            start(call)
        else:
            bot.answer_callback_query(call.id, "❌ You haven't joined the channel yet! Please join first.", show_alert=True)
            show_channel_join_alert(call)
    except Exception as e:
        print(f"Error in verify_join: {e}")
        bot.answer_callback_query(call.id, "❌ Error verifying. Please try again.", show_alert=True)

@bot.message_handler(commands=['setbinance'])
def set_binance_id(message):
    """Owner sets Binance ID for all users"""
    try:
        if str(message.from_user.id) != OWNER_USER_ID:
            bot.reply_to(message, "❌ Only owner can set Binance ID.")
            return
            
        if len(message.text.split()) < 2:
            bot.reply_to(message, "Usage: /setbinance <binance_id_for_all_users>")
            return
            
        global BINANCE_ID
        BINANCE_ID = message.text.split(maxsplit=1)[1]
        bot.reply_to(message, f"✅ Global Binance ID set! All users will see this payment option.")
        
    except Exception as e:
        print(f"Error setting Binance ID: {e}")
        bot.reply_to(message, "❌ Error setting Binance ID. Please try again.")
        
    

@bot.message_handler(commands=['add'])
def add_crypto_address(message):
    """Add crypto address (owner only)"""
    try:
        if str(message.from_user.id) != OWNER_USER_ID:
            bot.reply_to(message, "❌ Only owner can use this command.")
            return
            
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "Usage: /add <btc/ltc/usdt> <address>")
            return
            
        crypto = parts[1].lower()
        if crypto not in ['btc', 'ltc', 'usdt']:
            bot.reply_to(message, "❌ Invalid cryptocurrency. Use btc, ltc, or usdt")
            return
            
        crypto_addresses[crypto] = parts[2]
        bot.reply_to(message, f"✅ {crypto.upper()} address set: {parts[2]}")
        
    except Exception as e:
        print(f"Error adding crypto: {e}")
        bot.reply_to(message, "❌ Error setting address. Please try again.")

@bot.message_handler(commands=["start"])
def start(message):
    """Start command with referral handling"""
    try:
        user_id = str(message.from_user.id)
        
        if not check_channel_membership(user_id):
            show_channel_join_alert(message)
            return
            
        if user_id not in user_data:
            user_data[user_id] = {'points': 0, 'referred_by': None, 'binance_id': '', 'points_used': 0}
        
        # Handle referral
        if len(message.text.split()) > 1:
            referrer_id = message.text.split()[1]
            if (referrer_id != user_id and 
                referrer_id in user_data and 
                user_data[user_id]['referred_by'] is None):
                
                user_data[user_id]['referred_by'] = referrer_id
                user_data[referrer_id]['points'] += 1
                
                try:
                    user_info = bot.get_chat(referrer_id)
                    if not user_info.is_bot:
                        bot.send_message(
                            referrer_id,
                            f"🎉 New referral joined! You earned 1 point.\nTotal points: {user_data[referrer_id]['points']}"
                        )
                except Exception as e:
                    print(f"Non-critical error notifying referrer: {e}")
        
        # Welcome message
        msg = '''<b>Welcome!</b> Choose an option below:'''
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("Menu", callback_data="main_menu"))
        
        if isinstance(message, telebot.types.CallbackQuery):
            try:
                bot.edit_message_text(
                    chat_id=message.message.chat.id,
                    message_id=message.message.message_id,
                    text=msg,
                    reply_markup=markup
                )
            except:
                bot.send_message(message.from_user.id, msg, reply_markup=markup)
        else:
            bot.reply_to(message, msg, reply_markup=markup)
        
    except Exception as e:
        print(f"Error in start: {e}")
        if isinstance(message, telebot.types.CallbackQuery):
            bot.send_message(message.from_user.id, "❌ Error starting bot. Please try again.")
        else:
            bot.reply_to(message, "❌ Error starting bot. Please try again.")

@bot.message_handler(commands=['myreferrals'])
def check_referrals(message):
    """Check user's referral status"""
    try:
        user_id = str(message.from_user.id)
        if user_id not in user_data:
            user_data[user_id] = {'points': 0, 'referred_by': None, 'binance_id': '', 'points_used': 0}
        
        referrals = [uid for uid, data in user_data.items() if data.get('referred_by') == user_id]
        
        msg = f"""<b>Your Referral Status</b>
        
Total Referrals: {len(referrals)}
Your Points: {user_data[user_id]['points']}
Your Referral Link: https://t.me/{bot.get_me().username}?start={user_id}"""
        
        bot.reply_to(message, msg)
    except Exception as e:
        print(f"Error in check_referrals: {e}")
        bot.reply_to(message, "❌ Error showing referral info. Please try again.")

@bot.message_handler(commands=['referral'])
def referral_command(message):
    """Show referral information"""
    try:
        user_id = str(message.from_user.id)
        
        if not check_channel_membership(message.from_user.id):
            show_channel_join_alert(message)
            return
        
        if user_id not in user_data:
            user_data[user_id] = {'points': 0, 'referred_by': None, 'binance_id': '', 'points_used': 0}
        
        referral_link = f"https://t.me/{bot.get_me().username}?start={user_id}"
        
        msg = f"""<b>Your Referral Information</b>

🔗 Your referral link:
<code>{referral_link}</code>

👥 Total referrals: {len([u for u in user_data.values() if u.get('referred_by') == user_id])}
⭐ Your points: {user_data[user_id]['points']}
📊 Points used: {user_data[user_id]['points_used']}"""
        
        bot.reply_to(message, msg)
    except Exception as e:
        print(f"Error in referral: {e}")
        bot.reply_to(message, "❌ Error showing referral info. Please try again.")

def generate_key(expiry_option):
    """Generate key from external service"""
    option_mapping = {
        "1d": "1 day",
        "3d": "3 day",
        "7d": "7 day",
        "15d": "15 day",
        "1m": "1 month",
        "2m": "2 month",
        "1y": "1 year",
        "forever": "10 year"
    }
    
    b = option_mapping.get(expiry_option, "1 day")
    
    url = "https://teamvegas.in/ressellerpanel.php"
    params = {'keysesid': "Abhinaw75517"}
    payload = {'expirationOption': b, 'createKey': ""}
    
    headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36",
    }

    try:
        response = requests.post(url, params=params, data=payload, headers=headers)
        time.sleep(3)
        response = requests.get(url, params=params, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        buttons = soup.find_all('button', onclick=True)
        
        if not buttons:
            return None
        
        last_button = buttons[-1]
        onclick = last_button['onclick']
        key_value = onclick.split("'")[1]
        
        return key_value
    except Exception as e:
        print(f"Error generating key: {e}")
        return None

# ==================== PAYMENT FLOW ====================

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def main_menu(call):
    """Show main menu"""
    try:
        menu_text = """<b>Main Menu</b>
        
Please select an option:"""
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("Purchase", callback_data='purchase'),
            InlineKeyboardButton("Contact Owner", callback_data='contact')
        )
        markup.row(InlineKeyboardButton("Referral Program", callback_data='referral'))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=menu_text,
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error in main_menu: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "purchase")
def show_plans(call):
    """Show subscription plans"""
    try:
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("1 Day", callback_data='plan_1d'),
            InlineKeyboardButton("3 Day", callback_data='plan_3d'),
            InlineKeyboardButton("7 Day", callback_data='plan_7d')
        )
        markup.row(
            InlineKeyboardButton("15 Days", callback_data='plan_15d'),
            InlineKeyboardButton("1 Month", callback_data='plan_1m'),
            InlineKeyboardButton("2 Months", callback_data='plan_2m')
        )
        markup.row(
            InlineKeyboardButton("1 Year", callback_data='plan_1y'),
            InlineKeyboardButton("Forever", callback_data='plan_forever')
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text='Choose a subscription plan:',
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error showing plans: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('plan_'))
def show_plan_details(call):
    """Show details for specific plan"""
    try:
        duration = call.data.split('_')[1]
        user_id = str(call.from_user.id)
        inr_price = INDIAN_PRICES.get(duration, 0)
        foreign_price = FOREIGN_PRICES.get(duration, 0)
        points_info = POINT_SYSTEM.get(duration, {})
        
        duration_text = {
            '1d': '1 Day',
            '3d': '3 Days',
            '7d': '7 Days',
            '15d': '15 Days',
            '1m': '1 Month',
            '2m': '2 Months',
            '1y': '1 Year',
            'forever': 'Forever'
        }.get(duration, duration)
        
        msg = f"""<b>{duration_text} Subscription</b>

🇮🇳 Indian Price: ₹{inr_price}
🌍 Foreign Price: ${foreign_price}"""

        if points_info:
            user_points = user_data.get(user_id, {}).get('points', 0)
            msg += f"\n⭐ Points: {points_info['points']} (Get {points_info['keys']} key{'s' if points_info['keys'] > 1 else ''})"
            msg += f"\n💎 Your points: {user_points}"
            if user_points >= points_info['points']:
                msg += "\n✅ You can redeem with points!"
            else:
                msg += "\n❌ Not enough points for this plan"

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("Buy Now", callback_data=f'buy_{duration}'))
        markup.row(InlineKeyboardButton("Back", callback_data='purchase'))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=msg,
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error showing plan details: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy(call):
    """Handle buy button click"""
    try:
        duration = call.data.split('_')[1]
        show_payment_options(call, duration)
    except Exception as e:
        print(f"Error in buy handler: {e}")

def show_payment_options(call, duration):
    """Show payment options for selected plan"""
    try:
        user_id = str(call.from_user.id)
        markup = InlineKeyboardMarkup()
        
        # Always show these
        markup.row(
            InlineKeyboardButton("Pay with INR", callback_data=f'inr_{duration}'),
            InlineKeyboardButton("Pay with Crypto", callback_data=f'crypto_{duration}')
        )
        
        # Show Binance if owner has set it (visible to all users)
        if BINANCE_ID:
            markup.row(InlineKeyboardButton("Pay with Binance", callback_data=f'binance_{duration}'))
        
        # Show points option if available
        points_info = POINT_SYSTEM.get(duration, {})
        if points_info and user_data.get(user_id, {}).get('points', 0) >= points_info['points']:
            markup.row(InlineKeyboardButton(f"Use Points ({points_info['points']})", callback_data=f'points_{duration}'))
        
        markup.row(InlineKeyboardButton("Back", callback_data=f'plan_{duration}'))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Select payment method:",
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error showing payment options: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('inr_'))
def show_upi_payment(call):
    """Show UPI payment instructions"""
    try:
        duration = call.data.split('_')[1]
        user_id = str(call.from_user.id)
        
        duration_text = {
            '1d': '1 Day',
            '3d': '3 Days',
            '7d': '7 Days',
            '15d': '15 Days',
            '1m': '1 Month',
            '2m': '2 Months',
            '1y': '1 Year',
            'forever': 'Forever'
        }.get(duration, duration)
        
        payment_verification[user_id] = {
            'duration': duration,
            'payment_method': 'upi'
        }
        
        msg = f"""<b>UPI Payment Instructions</b>

For <b>{duration_text}</b> subscription
Send payment to this UPI ID:
<code>{UPI_ID}</code>

Amount: ₹{INDIAN_PRICES.get(duration, 0)}

After payment, click "Payment Done" below and send the payment screenshot."""
        
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("Payment Done", callback_data=f'payment_done_upi_{duration}'))
        markup.row(InlineKeyboardButton("Back", callback_data=f'buy_{duration}'))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=msg,
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error showing UPI payment: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('crypto_'))
def show_crypto_options(call):
    """Show cryptocurrency options"""
    try:
        duration = call.data.split('_')[1]
        
        markup = InlineKeyboardMarkup()
        
        if crypto_addresses['btc']:
            markup.row(InlineKeyboardButton("BTC", callback_data=f'pay_btc_{duration}'))
        if crypto_addresses['ltc']:
            markup.row(InlineKeyboardButton("LTC", callback_data=f'pay_ltc_{duration}'))
        if crypto_addresses['usdt']:
            markup.row(InlineKeyboardButton("USDT", callback_data=f'pay_usdt_{duration}'))
        
        markup.row(InlineKeyboardButton("Back", callback_data=f'buy_{duration}'))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="<b>Select Cryptocurrency:</b>",
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error showing crypto options: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_'))
def show_crypto_address(call):
    """Show crypto payment address"""
    try:
        parts = call.data.split('_')
        crypto = parts[1]
        duration = parts[2]
        user_id = str(call.from_user.id)
        
        address = crypto_addresses.get(crypto, '')
        if not address:
            bot.answer_callback_query(call.id, "Payment option not available. Please try another.", show_alert=True)
            return
        
        crypto_name = crypto.upper()
        duration_text = {
            '1d': '1 Day',
            '3d': '3 Days',
            '7d': '7 Days',
            '15d': '15 Days',
            '1m': '1 Month',
            '2m': '2 Months',
            '1y': '1 Year',
            'forever': 'Forever'
        }.get(duration, duration)
        
        payment_verification[user_id] = {
            'duration': duration,
            'payment_method': crypto,
            'address': address
        }
        
        msg = f"""<b>{crypto_name} Payment Instructions</b>

For <b>{duration_text}</b> subscription
Send payment to this address:
<code>{address}</code>

Amount: ${FOREIGN_PRICES.get(duration, 0)} {crypto_name}

After payment, click "Payment Done" below and send the transaction screenshot."""
        
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("Payment Done", callback_data=f'payment_done_{crypto}_{duration}'))
        markup.row(InlineKeyboardButton("Back", callback_data=f'crypto_{duration}'))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=msg,
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error showing crypto address: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('binance_'))
def show_binance_payment(call):
    """Show Binance payment instructions"""
    try:
        duration = call.data.split('_')[1]
        user_id = str(call.from_user.id)
        
        if not BINANCE_ID:
            bot.answer_callback_query(call.id, "Binance payment not currently available.", show_alert=True)
            return
        
        duration_text = {
            '1d': '1 Day',
            '3d': '3 Days',
            '7d': '7 Days',
            '15d': '15 Days',
            '1m': '1 Month',
            '2m': '2 Months',
            '1y': '1 Year',
            'forever': 'Forever'
        }.get(duration, duration)
        
        payment_verification[user_id] = {
            'duration': duration,
            'payment_method': 'binance'
        }
        
        msg = f"""<b>Binance Payment Instructions</b>

For <b>{duration_text}</b> subscription
Send payment to Binance ID:
<code>{BINANCE_ID}</code>

Amount: ${FOREIGN_PRICES.get(duration, 0)}

Click "Confirm Payment" below to proceed."""
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("Confirm Payment", callback_data=f'confirm_binance_{duration}'),
            InlineKeyboardButton("Cancel", callback_data=f'buy_{duration}')
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=msg,
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error showing Binance payment: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('points_'))
def process_points_payment(call):
    """Process payment using points"""
    try:
        duration = call.data.split('_')[1]
        user_id = str(call.from_user.id)
        points_info = POINT_SYSTEM.get(duration, {})
        
        if not points_info:
            bot.answer_callback_query(call.id, "This plan cannot be purchased with points.", show_alert=True)
            return
        
        user_points = user_data.get(user_id, {}).get('points', 0)
        points_required = points_info['points']
        
        if user_points < points_required:
            bot.answer_callback_query(call.id, f"You need {points_required} points but only have {user_points}.", show_alert=True)
            return
        
        # Check if user has already used points for this duration
        points_used = user_data.get(user_id, {}).get('points_used', 0)
        if points_used >= points_required * points_info['max_uses']:
            bot.answer_callback_query(call.id, "You've reached the maximum uses for points on this plan.", show_alert=True)
            return
        
        # Deduct points
        user_data[user_id]['points'] -= points_required
        user_data[user_id]['points_used'] += points_required
        
        # Generate key(s)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="⏳ Generating your key(s)..."
        )
        
        keys = []
        for _ in range(points_info['keys']):
            key = generate_key(duration)
            if key:
                keys.append(key)
        
        duration_text = {
            '1d': '1 Day',
            '3d': '3 Days',
            '7d': '7 Days',
            '15d': '15 Days',
            '1m': '1 Month',
            '2m': '2 Months',
            '1y': '1 Year',
            'forever': 'Forever'
        }.get(duration, duration)
        
        if keys:
            # Create temporary invite link
            temp_link = create_temp_invite_link(user_id)
            
            keys_text = "\n".join([f"<code>{key}</code>" for key in keys])
            success_msg = f"""<b>✅ Your Key{'s' if len(keys) > 1 else ''} Has Been Generated!</b>

<b>Subscription:</b> {duration_text}
<b>Key{'s' if len(keys) > 1 else ''}:</b> 
{keys_text}

🔒 Access your private content here: {temp_link}
⚠️ This link will expire after use

Points used: {points_required}
Remaining points: {user_data[user_id]['points']}"""
            
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("Purchase Again", callback_data='purchase'),
                InlineKeyboardButton("Contact Owner", callback_data='contact')
            )
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=success_msg,
                reply_markup=markup
            )
        else:
            # Refund points if key generation failed
            user_data[user_id]['points'] += points_required
            user_data[user_id]['points_used'] -= points_required
            
            error_msg = """<b>❌ Error Generating Key</b>

Failed to generate key. Your points have been refunded.
Please try again later or contact owner."""
            
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("Try Again", callback_data=f'points_{duration}'))
            markup.row(InlineKeyboardButton("Back to Menu", callback_data='main_menu'))
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=error_msg,
                reply_markup=markup
            )
    except Exception as e:
        print(f"Error processing points payment: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('payment_done_'))
def handle_payment_done(call):
    """Handle payment done callback"""
    try:
        parts = call.data.split('_')
        if len(parts) == 4:  # crypto payment
            crypto = parts[2]
            duration = parts[3]
        else:  # upi payment
            crypto = 'upi'
            duration = parts[2]
        
        msg = bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Please send the payment screenshot as an image (not as a file)."
        )
        
        bot.register_next_step_handler(msg, handle_payment_screenshot, str(call.from_user.id), crypto, duration)
    except Exception as e:
        print(f"Error in payment_done: {e}")

def handle_payment_screenshot(message, user_id, crypto, duration):
    """Handle payment screenshot submission"""
    try:
        if not message.photo:
            msg = bot.send_message(message.chat.id, "Please send the screenshot as an image (not as a file or text).")
            bot.register_next_step_handler(msg, handle_payment_screenshot, user_id, crypto, duration)
            return
        
        payment_verification[user_id]['screenshot'] = message.photo[-1].file_id
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("Payment Received", callback_data=f'confirm_payment_{user_id}'),
            InlineKeyboardButton("Cancel", callback_data=f'cancel_payment_{user_id}')
        )
        
        # Send to owner for verification
        bot.send_photo(
            chat_id=OWNER_CHAT_ID,
            photo=message.photo[-1].file_id,
            caption=f"Payment verification from user {message.from_user.id}\n\n"
                   f"Method: {crypto.upper()}\n"
                   f"Duration: {duration}\n"
                   f"User ID: {user_id}",
            reply_markup=markup
        )
        
        bot.send_message(
            message.chat.id,
            "Your payment screenshot has been sent for verification. Please wait for confirmation.",
            reply_markup=InlineKeyboardMarkup().row(
                InlineKeyboardButton("Back to Menu", callback_data='main_menu')
            )
        )
    except Exception as e:
        print(f"Error handling screenshot: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_binance_'))
def confirm_binance_payment(call):
    """Confirm Binance payment"""
    try:
        duration = call.data.split('_')[2]
        user_id = str(call.from_user.id)
        
        # Store payment info for verification
        payment_verification[user_id] = {
            'duration': duration,
            'payment_method': 'binance',
            'binance_id': user_data.get(user_id, {}).get('binance_id', '')
        }
        
        # Request screenshot
        msg = bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Please send screenshot of your Binance payment as an image (not as a file)."
        )
        
        bot.register_next_step_handler(msg, handle_binance_screenshot, user_id, duration)
    except Exception as e:
        print(f"Error in confirm_binance_payment: {e}")

def handle_binance_screenshot(message, user_id, duration):
    """Handle Binance screenshot submission"""
    try:
        if not message.photo:
            msg = bot.send_message(message.chat.id, "Please send the screenshot as an image (not as a file or text).")
            bot.register_next_step_handler(msg, handle_binance_screenshot, user_id, duration)
            return
        
        # Store screenshot and send to owner
        payment_verification[user_id]['screenshot'] = message.photo[-1].file_id
        
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("Payment Received", callback_data=f'confirm_payment_{user_id}'),
            InlineKeyboardButton("Cancel", callback_data=f'cancel_payment_{user_id}')
        )
        
        # Send to owner for verification
        bot.send_photo(
            chat_id=OWNER_CHAT_ID,
            photo=message.photo[-1].file_id,
            caption=f"Binance payment verification from user {message.from_user.id}\n\n"
                   f"Duration: {duration}\n"
                   f"Binance ID: {payment_verification[user_id]['binance_id']}",
            reply_markup=markup
        )
        
        bot.send_message(
            message.chat.id,
            "Your Binance payment screenshot has been sent for verification. Please wait for confirmation.",
            reply_markup=InlineKeyboardMarkup().row(
                InlineKeyboardButton("Back to Menu", callback_data='main_menu')
            )
        )
    except Exception as e:
        print(f"Error handling Binance screenshot: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_payment_'))
def confirm_payment(call):
    """Confirm payment and deliver key"""
    try:
        user_id = call.data.split('_')[2]
        user_info = payment_verification.get(user_id, {})
        
        if not user_info:
            bot.answer_callback_query(call.id, "User data not found!", show_alert=True)
            return
        
        bot.send_message(
            user_id,
            "✅ Payment received! Please wait while we generate your key..."
        )
        
        key = generate_key(user_info['duration'])
        duration_text = {
            '1d': '1 Day',
            '3d': '3 Days',
            '7d': '7 Days',
            '15d': '15 Days',
            '1m': '1 Month',
            '2m': '2 Months',
            '1y': '1 Year',
            'forever': 'Forever'
        }.get(user_info['duration'], user_info['duration'])
        
        if key:
            # Create temporary invite link
            temp_link = create_temp_invite_link(user_id)
            
            success_msg = f"""<b>✅ Your Key Has Been Generated!</b>

<b>Subscription:</b> {duration_text}
<b>Key:</b> <code>{key}</code>

🔒 Access your private content here: {temp_link}
⚠️ This link will expire after use

Thank you for your purchase!"""
            
            markup = InlineKeyboardMarkup()
            markup.row(
                InlineKeyboardButton("Purchase Again", callback_data='purchase'),
                InlineKeyboardButton("Contact Owner", callback_data='contact')
            )
            
            bot.send_message(
                user_id,
                success_msg,
                reply_markup=markup
            )
            
            bot.answer_callback_query(
                call.id,
                f"Key sent to user {user_id}",
                show_alert=True
            )
            
            # Update referral points if applicable
            referring_user = user_data.get(user_id, {}).get('referred_by')
            if referring_user and referring_user in user_data:
                user_data[referring_user]['points'] += 1
                bot.send_message(
                    referring_user,
                    f"🎉 You earned 1 point for your referral! Total points: {user_data[referring_user]['points']}"
                )
            
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=f"✅ Payment confirmed for user {user_id}\n\nKey delivered: {key}\nPrivate link: {temp_link}"
            )
        else:
            bot.send_message(
                user_id,
                "❌ Error generating your key. Please contact owner @KALYATOOFAN_BOT"
            )
            bot.answer_callback_query(
                call.id,
                "Failed to generate key!",
                show_alert=True
            )
    except Exception as e:
        print(f"Error confirming payment: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_payment_'))
def cancel_payment(call):
    """Cancel payment verification"""
    try:
        user_id = call.data.split('_')[2]
        bot.send_message(
            user_id,
            "❌ Payment verification failed. Please contact owner @KALYATOOFAN_BOT if you believe this is an error."
        )
        bot.answer_callback_query(
            call.id,
            f"Payment cancelled for user {user_id}",
            show_alert=True
        )
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=f"❌ Payment cancelled for user {user_id}"
        )
    except Exception as e:
        print(f"Error cancelling payment: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "contact")
def contact_owner(call):
    """Show contact information"""
    try:
        contact_text = """<b>Contact Information</b>
        
For any questions or support, please contact:
@KALYATOOFAN_BOT"""
        
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("Back to Menu", callback_data='main_menu'))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=contact_text,
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error showing contact info: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "referral")
def show_referral(call):
    """Show referral information"""
    try:
        referral_command(call.message)
    except Exception as e:
        print(f"Error showing referral: {e}")

print("Bot is running...")
bot.infinity_polling()
