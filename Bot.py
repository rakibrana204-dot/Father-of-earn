import telebot
from telebot import types
import datetime
import sqlite3
import time
import os
from flask import Flask, request

# ফ্লাস্ক অ্যাপ তৈরি
app = Flask('')

# রেন্ডারের Environment Variable থেকে সঠিক বানানে টোকেন রিড করা হচ্ছে
TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)

BOT_LAUNCH_DATE = datetime.datetime(2026, 6, 22)

# অ্যাডমিন ও কনফিগারেশন
ADMIN_ID = 671784196
ADMIN_USERNAME = "@rjrakib019"
ADMIN_PAYMENT_NUMBER = "01943937627"
GMAIL_PASSWORD_REQUIRED = "@rakib2041"
CHANNEL_LINK = "https://t.me/freeincomesite204"
MIN_WITHDRAW = 80.00

# মনিট্যাগ অ্যাড কনফিগারেশন
AD_LINK = "https://omg10.com/4/11190574"
AD_REWARD = 1.00 
DAILY_AD_LIMIT = 5

# Webhook রুট - যেখানে টেলিগ্রাম মেসেজ পাঠাবে
@app.route('/' + TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def home():
    return "বট সফলভাবে Webhook এর মাধ্যমে ২৪ ঘণ্টা সচল আছে!"

# মেইন মেনু কিবোর্ড জেনারেটর ফাংশন
def get_main_menu_markup(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_home = types.KeyboardButton("🏠 Home")
    btn_task = types.KeyboardButton("🎁 Daily Task")
    btn_ad = types.KeyboardButton("🖥 অ্যাড দেখে আয়")
    btn_wallet = types.KeyboardButton("💼 Wallet")
    btn_team = types.KeyboardButton("👥 Team")
    btn_profile = types.KeyboardButton("👤 Profile")
    markup.row(btn_home, btn_task)
    markup.row(btn_ad, btn_wallet)
    markup.row(btn_team, btn_profile)
    
    if user_id == ADMIN_ID:
        btn_admin = types.KeyboardButton("⚙️ Admin Panel")
        markup.row(btn_admin)
    return markup

# ক্যানসেল কিবোর্ড জেনারেটর ফাংশন
def get_cancel_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("❌ Cancel"))
    return markup

# ইনপুট ভ্যালিডেশন চেকার ফাংশন
def is_invalid_input(text):
    main_buttons = ["🏠 Home", "🎁 Daily Task", "🖥 অ্যাড দেখে আয়", "💼 Wallet", "👥 Team", "👤 Profile", "⚙️ Admin Panel", "❌ Cancel"]
    if text in main_buttons:
        return True
    return False

def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            balance REAL,
            status TEXT,
            referred_by INTEGER,
            last_daily_task TEXT,
            target_start_date TEXT,
            target_ref_count INTEGER DEFAULT 0,
            target_claimed INTEGER DEFAULT 0,
            last_ad_date TEXT,
            daily_ad_count INTEGER DEFAULT 0
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN last_ad_date TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN daily_ad_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
        
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gmail_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            gmail TEXT,
            password TEXT,
            status TEXT,
            submitted_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdraw_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            method TEXT,
            number TEXT,
            amount REAL,
            status TEXT,
            requested_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def check_user(user_id, name=None, referred_by=None):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance, status, target_start_date, last_ad_date, daily_ad_count FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    today_str = datetime.date.today().isoformat()
    
    if user is None:
        cursor.execute("INSERT INTO users (user_id, name, balance, status, referred_by, target_start_date, target_ref_count, target_claimed, last_ad_date, daily_ad_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (user_id, name if name else "User", 0.0, "active", referred_by, today_str, 0, 0, today_str, 0))
        conn.commit()
        
        if referred_by and referred_by != user_id:
            cursor.execute("UPDATE users SET balance = balance + 5.0 WHERE user_id = ?", (referred_by,))
            cursor.execute("SELECT target_start_date, target_claimed FROM users WHERE user_id = ?", (referred_by,))
            ref_parent = cursor.fetchone()
            if ref_parent:
                start_date_str, claimed = ref_parent[0], ref_parent[1]
                if start_date_str and claimed == 0:
                    start_date = datetime.date.fromisoformat(start_date_str)
                    if (datetime.date.today() - start_date).days <= 3:
                        cursor.execute("UPDATE users SET target_ref_count = target_ref_count + 1 WHERE user_id = ?", (referred_by,))
            conn.commit()
            try:
                bot.send_message(referred_by, f"🎉 আপনার রেফারেল লিংক ব্যবহার করে একজন নতুন মেম্বার জয়েন করেছে! আপনি পেয়েছেন ৳৫.০০।")
            except:
                pass
    else:
        last_ad_date = user[3]
        if last_ad_date != today_str:
            cursor.execute("UPDATE users SET last_ad_date = ?, daily_ad_count = 0 WHERE user_id = ?", (today_str, user_id))
            conn.commit()
            
    conn.close()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    referred_by = None
    parts = message.text.split()
    if len(parts) > 1:
        try:
            referred_by = int(parts[1])
        except ValueError:
            referred_by = None
            
    check_user(user_id, name, referred_by)
    
    welcome_text = (
        f"👋 স্বাগতম {name} আমাদের আর্নিং বটে!\n\n"
        f"এখানে আপনি রিয়েল জিমেইল সেল করে, বন্ধুদের রেফার করে এবং ডেইলি টাস্ক ও অ্যাড দেখে প্রতিদিন ভালো টাকা ইনকাম করতে পারবেন।\n\n"
        f"📢 আমাদের অফিশিয়াল চ্যানেলে অবশ্যই জয়েন থাকবেন: {CHANNEL_LINK}"
    )
    bot.send_message(user_id, welcome_text, reply_markup=get_main_menu_markup(user_id))

user_ad_sessions = {}

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    text = message.text
    check_user(user_id, message.from_user.first_name)
    
    if text == "🏠 Home":
        bot.send_message(user_id, "🏠 আপনি এখন মূল মেনুতে আছেন। নিচে থেকে আপনার পছন্দের অপশনটি বেছে নিন।", reply_markup=get_main_menu_markup(user_id))
        
    elif text == "🎁 Daily Task":
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT last_daily_task, target_start_date, target_ref_count, target_claimed FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        
        today_str = datetime.date.today().isoformat()
        last_daily = res[0]
        start_date_str = res[1]
        ref_count = res[2] if res[2] else 0
        claimed = res[3] if res[3] else 0
        
        if last_daily == today_str:
            daily_status = "❌ আজকে অলরেডি ক্লেইম করেছেন!"
        else:
            daily_status = "✅ ক্লেইম করার জন্য রেডি!"
            
        start_date = datetime.date.fromisoformat(start_date_str)
        days_passed = (datetime.date.today() - start_date).days
        days_left = 3 - days_passed
        
        target_status_text = ""
        show_claim_btn = False
        
        if claimed == 1:
            target_status_text = "🎯 টার্গেট বোনাস: ✅ সফলভাবে ক্লেইমড (৳২০ পেয়েছেন)!"
        elif days_left < 0:
            target_status_text = "🎯 টার্গেট বোনাস: ❌ সময় শেষ হয়ে গেছে! আপনি ৩ দিনে ১০ জন একটিভ রেফার করতে পারেননি।"
        else:
            progress_bar = "🟢" * min(ref_count, 10) + "⚪" * (10 - min(ref_count, 10))
            target_status_text = (
                f"🎯 **টার্গেট বোনাস (৳২০ চ্যালেঞ্জ)**\n"
                f"৩ দিনের মধ্যে ১০ জন একটিভ রেফার করুন এবং অতিরিক্ত ৳২০ বোনাস জিতে নিন!\n\n"
                f"⏱ সময় বাকি: {days_left} দিন\n"
                f"📊 আপনার রেফার প্রোগ্রেস: {ref_count}/১০\n"
                f"[{progress_bar}]\n"
            )
            if ref_count >= 10:
                show_claim_btn = True
                target_status_text += "\n🎉 অভিনন্দন! আপনার চ্যালেঞ্জ পূর্ণ হয়েছে। নিচে ক্লেইম করুন।"
            else:
                target_status_text += f"\n💡 আরও {10 - ref_count} জন রেফার প্রয়োজন।"
                
        conn.close()
        
        markup = types.InlineKeyboardMarkup()
        if last_daily != today_str:
            markup.add(types.InlineKeyboardButton("🎁 ডেইলি বোনাস ক্লেইম (৳১.০০)", callback_data="claim_daily_bonus"))
        if show_claim_btn:
            markup.add(types.InlineKeyboardButton("🎯 টার্গেট বোনাস ক্লেইম (৳২০.০০)", callback_data="claim_target_bonus"))
            
        task_msg = (
            f"📋 **আপনার আজকের টাস্ক লিস্ট**\n\n"
            f"১. সাধারণ ডেইলি বোনাস:\n{daily_status}\n\n"
            f"{target_status_text}"
        )
        bot.send_message(user_id, task_msg, reply_markup=markup, parse_mode="Markdown")

    elif text == "🖥 অ্যাড দেখে আয়":
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT daily_ad_count FROM users WHERE user_id = ?", (user_id,))
        daily_ad_count = cursor.fetchone()[0]
        conn.close()
        
        if daily_ad_count >= DAILY_AD_LIMIT:
            bot.send_message(user_id, f"❌ দুঃখিত! আপনার আজকের অ্যাড দেখার লিমিট শেষ। আগামীকাল আবার {DAILY_AD_LIMIT}টি অ্যাড দেখতে পারবেন।")
            return
            
        user_ad_sessions[user_id] = time.time()
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔗 অ্যাড ওপেন করুন", url=AD_LINK))
        markup.add(types.InlineKeyboardButton("✅ ভেরিফাই ও বোনাস নিন", callback_data="verify_ad"))
        
        ad_msg = (
            f"🖥 **অ্যাড দেখে টাকা ইনকাম করুন!**\n\n"
            f"আজকের বাকি লিমিট: {DAILY_AD_LIMIT - daily_ad_count}/{DAILY_AD_LIMIT} টি।\n"
            f"💰 প্রতি অ্যাডের রিওয়ার্ড: ৳{AD_REWARD:.2f}\n\n"
            f"⚠️ **নিয়ম:** নিচের লিংকে ক্লিক করে অ্যাডটি কমপক্ষে ১৫ সেকেন্ড মন দিয়ে স্ক্রোল করুন। তারপর এসে ভেরিফাই বাটনে চাপ দিন।"
        )
        bot.send_message(user_id, ad_msg, reply_markup=markup)
        
    elif text == "💼 Wallet":
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = cursor.fetchone()[0]
        conn.close()
        
        wallet_msg = (
            f"💼 **আপনার ওয়ালেট অ্যাকাউন্ট**\n\n"
            f"💵 বর্তমান ব্যালেন্স: ৳{balance:.2f}\n"
            f"🛑 সর্বনিম্ন উইথড্র: ৳{MIN_WITHDRAW:.2f}\n\n"
            f"জিমেইল সেল করতে বা ব্যালেন্স তুলতে নিচের বাটন ব্যবহার করুন।"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📧 জিমেইল সেল করুন", callback_data="submit_gmail"))
        markup.add(types.InlineKeyboardButton("💸 টাকা তুলুন (Withdraw)", callback_data="withdraw_money"))
        bot.send_message(user_id, wallet_msg, reply_markup=markup)
        
    elif text == "👥 Team":
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        total_refs = cursor.fetchone()[0]
        conn.close()
        
        team_msg = (
            f"👥 **আপনার রেফারেল টিম**\n\n"
            f"📊 মোট সফল রেফার: {total_refs} জন\n"
            f"💰 প্রতি সফল রেফারে পাবেন: ৳৫.০০\n\n"
            f"🔗 আপনার রেফারেল লিংক:\n`{ref_link}`\n\n"
            f"💡 লিংকটি কপি করে আপনার বন্ধুদের সাথে শেয়ার করুন!"
        )
        bot.send_message(user_id, team_msg, parse_mode="Markdown")
        
    elif text == "👤 Profile":
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, balance, status FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        
        profile_msg = (
            f"👤 **ইউজার প্রোফাইল**\n\n"
            f"🆔 ইউজার আইডি: `{user_id}`\n"
            f"👤 নাম: {res[0]}\n"
            f"💵 মোট ব্যালেন্স: ৳{res[1]:.2f}\n"
            f"⚡ অ্যাকাউন্ট স্ট্যাটাস: {res[2].upper()}\n"
        )
        bot.send_message(user_id, profile_msg, parse_mode="Markdown")
        
    elif text == "⚙️ Admin Panel" and user_id == ADMIN_ID:
        admin_msg = "⚙️ **অ্যাডমিন ড্যাশবোর্ড**\n\nএখানে আপনি পেন্ডিং জিমেইল এবং উইথড্র রিকোয়েস্ট ম্যানেজ করতে পারবেন।"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📧 পেন্ডিং জিমেইল লিস্ট", callback_data="admin_pending_gmail"))
        markup.add(types.InlineKeyboardButton("💸 পেন্ডিং উইথড্র লিস্ট", callback_data="admin_pending_withdraw"))
        bot.send_message(user_id, admin_msg, reply_markup=markup)
        
    else:
        bot.send_message(user_id, "❌ আমি দুঃখিত, ইনপুটটি বুঝতে পারিনি। দয়া করে নিচের বাটনগুলো ব্যবহার করুন।", reply_markup=get_main_menu_markup(user_id))

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    check_user(user_id, call.from_user.first_name)
    
    if call.data == "claim_daily_bonus":
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT last_daily_task FROM users WHERE user_id = ?", (user_id,))
        last_daily = cursor.fetchone()[0]
        
        today_str = datetime.date.today().isoformat()
        if last_daily == today_str:
            bot.answer_callback_query(call.id, "❌ আপনি আজ অলরেডি বোনাস নিয়েছেন!", show_alert=True)
            conn.close()
        else:
            cursor.execute("UPDATE users SET balance = balance + 1.0, last_daily_task = ? WHERE user_id = ?", (today_str, user_id))
            conn.commit()
            conn.close()
            bot.answer_callback_query(call.id, "🎉 অভিনন্দন! ৳১.০০ আপনার ব্যালেন্সে যোগ হয়েছে।")
            bot.edit_message_text("✅ আজকের ডেইলি বোনাস সফলভাবে ক্লেইমড হয়েছে!", chat_id=user_id, message_id=call.message.message_id)
            
    elif call.data == "claim_target_bonus":
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT target_start_date, target_ref_count, target_claimed FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        
        start_date_str, ref_count, claimed = res[0], res[1], res[2]
        start_date = datetime.date.fromisoformat(start_date_str)
        days_passed = (datetime.date.today() - start_date).days
        
        if claimed == 1:
            bot.answer_callback_query(call.id, "❌ আপনি অলরেডি এই বোনাস ক্লেইম করেছেন!", show_alert=True)
        elif days_passed > 3:
            bot.answer_callback_query(call.id, "❌ দুঃখিত! ৩ দিনের সময় পার হয়ে গেছে।", show_alert=True)
        elif ref_count < 10:
            bot.answer_callback_query(call.id, f"❌ আপনার এখনো {10 - ref_count}টি রেফার প্রয়োজন!", show_alert=True)
        else:
            cursor.execute("UPDATE users SET balance = balance + 20.0, target_claimed = 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            bot.answer_callback_query(call.id, "🎉 অভিনন্দন! টার্গেট বোনাস ৳২০.০০ ক্লেইম হয়েছে।", show_alert=True)
            bot.edit_message_text("✅ টার্গেট চ্যালেঞ্জ সফল! ৳২০.০০ আপনার মূল ব্যালেন্সে যুক্ত করা হয়েছে।", chat_id=user_id, message_id=call.message.message_id)
        conn.close()

    elif call.data == "verify_ad":
        if user_id not in user_ad_sessions:
            bot.answer_callback_query(call.id, "⚠️ দয়া করে প্রথমে 'অ্যাড ওপেন করুন' বাটনে ক্লিক করুন।", show_alert=True)
            return
            
        elapsed_time = time.time() - user_ad_sessions[user_id]
        if elapsed_time < 15:
            remaining = 15 - int(elapsed_time)
            bot.answer_callback_query(call.id, f"🛑 জলদি করবেন না! বোনাস পেতে অ্যাডটি আরও {remaining} সেকেন্ড স্ক্রোল করুন।", show_alert=True)
            return
            
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT daily_ad_count FROM users WHERE user_id = ?", (user_id,))
        daily_ad_count = cursor.fetchone()[0]
        
        if daily_ad_count >= DAILY_AD_LIMIT:
            bot.answer_callback_query(call.id, "❌ আজকের অ্যাড লিমিট শেষ!", show_alert=True)
            conn.close()
            return
            
        cursor.execute("UPDATE users SET balance = balance + ?, daily_ad_count = daily_ad_count + 1 WHERE user_id = ?", (AD_REWARD, user_id))
        conn.commit()
        conn.close()
        
        del user_ad_sessions[user_id]
        
        bot.answer_callback_query(call.id, f"🎉 ভেরিফিকেশন সফল! ৳{AD_REWARD:.2f} আপনার ব্যালেন্সে যোগ হয়েছে।", show_alert=True)
        bot.edit_message_text(f"✅ অ্যাড দেখা সফল হয়েছে! আপনার একাউন্টে ৳{AD_REWARD:.2f} যোগ করা হয়েছে।", chat_id=user_id, message_id=call.message.message_id)

    elif call.data == "submit_gmail":
        msg = bot.send_message(user_id, "📧 আপনার ফ্রেশ জিমেইলটি টাইপ করে পাঠান:\n\n(অথবা বাতিল করতে নিচের বাটন চাপুন)", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(msg, process_gmail_input)
        
    elif call.data == "withdraw_money":
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = cursor.fetchone()[0]
        conn.close()
        
        if balance < MIN_WITHDRAW:
            bot.answer_callback_query(call.id, f"❌ দুঃখিত! টাকা তোলার জন্য আপনার একাউন্টে কমপক্ষে ৳{MIN_WITHDRAW:.2f} থাকতে হবে।", show_alert=True)
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📱 বিকাশ (Bkash)", callback_data="w_Bkash"))
            markup.add(types.InlineKeyboardButton("📱 নগদ (Nagad)", callback_data="w_Nagad"))
            bot.edit_message_text("📱 কোন মেথডের মাধ্যমে টাকা তুলতে চান সিলেক্ট করুন:", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)

    elif call.data.startswith("w_"):
        method = call.data.split("_")[1]
        msg = bot.send_message(user_id, f"🔢 আপনার {method} পার্সোনাল নাম্বারটি টাইপ করুন:\n\n(অথবা বাতিল করতে নিচের বাটন চাপুন)", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(msg, process_withdraw_number, method)
        
    elif call.data == "admin_pending_gmail" and user_id == ADMIN_ID:
        show_admin_gmail_list(user_id)
    elif call.data == "admin_pending_withdraw" and user_id == ADMIN_ID:
        show_admin_withdraw_list(user_id)
    elif call.data.startswith("approve_g_") and user_id == ADMIN_ID:
        sub_id = int(call.data.split("_")[2])
        manage_gmail(sub_id, "approved", call.message.message_id)
    elif call.data.startswith("reject_g_") and user_id == ADMIN_ID:
        sub_id = int(call.data.split("_")[2])
        manage_gmail(sub_id, "rejected", call.message.message_id)
    elif call.data.startswith("approve_w_") and user_id == ADMIN_ID:
        req_id = int(call.data.split("_")[2])
        manage_withdraw(req_id, "approved", call.message.message_id)
    elif call.data.startswith("reject_w_") and user_id == ADMIN_ID:
        req_id = int(call.data.split("_")[2])
        manage_withdraw(req_id, "rejected", call.message.message_id)

def process_gmail_input(message):
    user_id = message.from_user.id
    gmail = message.text
    
    if gmail == "❌ Cancel":
        bot.send_message(user_id, "❌ জিমেইল সাবমিশন বাতিল করা হয়েছে।", reply_markup=get_main_menu_markup(user_id))
        return
    if is_invalid_input(gmail):
        bot.send_message(user_id, "⚠️ অবৈধ ইনপুট! প্রসেস বাতিল করে আপনাকে মূল মেনুতে পাঠানো হলো।", reply_markup=get_main_menu_markup(user_id))
        return
        
    if "@" not in gmail or "." not in gmail:
        msg = bot.send_message(user_id, "❌ ভুল জিমেইল ফরম্যাট! দয়া করে সঠিক জিমেইল অ্যাড্রেসটি আবার লিখুন:", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(msg, process_gmail_input)
        return
        
    msg = bot.send_message(user_id, f"🔑 এবার আপনার জিমেইলের পাসওয়ার্ড এবং রিকভারিটি লিখুন:\n\n⚠️ সিকিউরিটি অ্যালার্ট: পাসওয়ার্ডের শুরুতে অবশ্যই `{GMAIL_PASSWORD_REQUIRED}` কোডটি টাইপ করে স্পেস দিয়ে তারপর পাসওয়ার্ড লিখবেন।\n\nউদাহরণ: `{GMAIL_PASSWORD_REQUIRED} mypass123`", reply_markup=get_cancel_markup(), parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_password_input, gmail)

def process_password_input(message, gmail):
    user_id = message.from_user.id
    password_text = message.text
    
    if password_text == "❌ Cancel":
        bot.send_message(user_id, "❌ প্রসেস বাতিল করা হয়েছে।", reply_markup=get_main_menu_markup(user_id))
        return
    if is_invalid_input(password_text):
        bot.send_message(user_id, "⚠️ অবৈধ ইনপুট! প্রসেস বাতিল করে আপনাকে মূল মেনুতে পাঠানো হলো।", reply_markup=get_main_menu_markup(user_id))
        return
        
    if not password_text.startswith(GMAIL_PASSWORD_REQUIRED):
        msg = bot.send_message(user_id, f"❌ সিকিউরিটি কোড মেলেনি! পাসওয়ার্ডের শুরুতে অবশ্যই `{GMAIL_PASSWORD_REQUIRED}` কোডটি বসিয়ে আবার চেষ্টা করুন:", reply_markup=get_cancel_markup(), parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_password_input, gmail)
        return
        
    actual_password = password_text.replace(GMAIL_PASSWORD_REQUIRED, "").strip()
    if not actual_password:
        msg = bot.send_message(user_id, "❌ পাসওয়ার্ডের ঘর ফাঁকা রাখা যাবে না! সঠিক নিয়মে আবার ইনপুট দিন:", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(msg, process_password_input, gmail)
        return
        
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO gmail_submissions (user_id, gmail, password, status, submitted_at) VALUES (?, ?, ?, ?, ?)",
                   (user_id, gmail, actual_password, "pending", now))
    conn.commit()
    conn.close()
    
    bot.send_message(user_id, "✅ আপনার জিমেইল সফলভাবে সাবমিট হয়েছে! অ্যাডমিন এটি চেক করে ১-১২ ঘণ্টার মধ্যে অ্যাপ্রুভ করে ব্যালেন্স যোগ করে দেবে। ধন্যবাদ।", reply_markup=get_main_menu_markup(user_id))
    try:
        bot.send_message(ADMIN_ID, f"📢 নতুন জিমেইল রিকোয়েস্ট এসেছে!\nইউজার আইডি: `{user_id}`\nজিমেইল: {gmail}", parse_mode="Markdown")
    except:
        pass

def process_withdraw_number(message, method):
    user_id = message.from_user.id
    number = message.text
    
    if number == "❌ Cancel":
        bot.send_message(user_id, "❌ টাকা তোলার রিকোয়েস্ট বাতিল করা হয়েছে।", reply_markup=get_main_menu_markup(user_id))
        return
    if is_invalid_input(number):
        bot.send_message(user_id, "⚠️ অবৈধ ইনপুট! প্রসেস বাতিল করে আপনাকে মূল মেনুতে পাঠানো হলো।", reply_markup=get_main_menu_markup(user_id))
        return
        
    if len(number) < 11 or not number.isdigit():
        msg = bot.send_message(user_id, "❌ ভুল নাম্বার! দয়া করে আপনার ১১ ডিজিটের সঠিক মোবাইল নাম্বারটি দিন:", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(msg, process_withdraw_number, method)
        return
        
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    conn.close()
    
    msg = bot.send_message(user_id, f"💵 কত টাকা তুলতে চান তা সংখ্যায় লিখুন:\n(আপনার ওয়ালেট ব্যালেন্স: ৳{balance:.2f})", reply_markup=get_cancel_markup())
    bot.register_next_step_handler(msg, process_withdraw_amount, method, number, balance)

def process_withdraw_amount(message, method, number, balance):
    user_id = message.from_user.id
    amount_text = message.text
    
    if amount_text == "❌ Cancel":
        bot.send_message(user_id, "❌ প্রসেস বাতিল করা হয়েছে।", reply_markup=get_main_menu_markup(user_id))
        return
    if is_invalid_input(amount_text):
        bot.send_message(user_id, "⚠️ অবৈধ ইনপুট! প্রসেস বাতিল করে আপনাকে মূল মেনুতে পাঠানো হলো।", reply_markup=get_main_menu_markup(user_id))
        return
        
    try:
        amount = float(amount_text)
    except ValueError:
        msg = bot.send_message(user_id, "❌ ভুল ইনপুট! দয়া করে শুধুমাত্র সংখ্যায় টাকার পরিমাণটি লিখুন:", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(msg, process_withdraw_amount, method, number, balance)
        return
        
    if amount < MIN_WITHDRAW:
        msg = bot.send_message(user_id, f"❌ সর্বনিম্ন উইথড্র লিমিট ৳{MIN_WITHDRAW:.2f}! এর বেশি পরিমাণ ইনপুট দিন:", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(msg, process_withdraw_amount, method, number, balance)
        return
        
    if amount > balance:
        msg = bot.send_message(user_id, f"❌ পর্যাপ্ত ব্যালেন্স নেই! আপনার একাউনটি আছে ৳{balance:.2f}। আবার সঠিক অ্যামাউন্ট লিখুন:", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(msg, process_withdraw_amount, method, number, balance)
        return
        
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
    cursor.execute("INSERT INTO withdraw_requests (user_id, method, number, amount, status, requested_at) VALUES (?, ?, ?, ?, ?, ?)",
                   (user_id, method, number, amount, "pending", now))
    conn.commit()
    conn.close()
    
    bot.send_message(user_id, f"✅ আপনার ৳{amount:.2f} উইথড্র রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে। ২৪ ঘণ্টার মধ্যে আপনার {method} নাম্বারে টাকা পৌঁছে যাবে।", reply_markup=get_main_menu_markup(user_id))
    try:
        bot.send_message(ADMIN_ID, f"💸 নতুন উইথড্র রিকোয়েস্ট এসেছে!\nমেথড: {method}\nনাম্বার: {number}\nপরিমাণ: ৳{amount:.2f}")
    except:
        pass

def show_admin_gmail_list(admin_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, gmail, password FROM gmail_submissions WHERE status = 'pending' LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        bot.send_message(admin_id, "🎉 বর্তমানে কোনো পেন্ডিং জিমেইল রিকোয়েস্ট নেই!")
        return
        
    for row in rows:
        sub_id, u_id, g_mail, g_pass = row[0], row[1], row[2], row[3]
        text = f"📧 **জিমেইল রিকোয়েস্ট**\n\n🆔 ইউজার আইডি: `{u_id}`\n📩 জিমেইল: `{g_mail}`\n🔑 পাসওয়ার্ড: `{g_pass}`"
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Approve (৳১০)", callback_data=f"approve_g_{sub_id}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_g_{sub_id}")
        )
        bot.send_message(admin_id, text, reply_markup=markup, parse_mode="Markdown")

def show_admin_withdraw_list(admin_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, method, number, amount FROM withdraw_requests WHERE status = 'pending' LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        bot.send_message(admin_id, "🎉 বর্তমানে কোনো পেন্ডিং উইথড্র রিকোয়েস্ট নেই!")
        return
        
    for row in rows:
        req_id, u_id, method, num, amt = row[0], row[1], row[2], row[3], row[4]
        text = f"💸 **উইথড্র রিকোয়েস্ট**\n\n🆔 ইউজার আইডি: `{u_id}`\n📱 মেথড: {method}\n🔢 নাম্বার: `{num}`\n💵 অ্যামাউন্ট: ৳{amt:.2f}"
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Paid", callback_data=f"approve_w_{req_id}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_w_{req_id}")
        )
        bot.send_message(admin_id, text, reply_markup=markup, parse_mode="Markdown")

def manage_gmail(sub_id, action, msg_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, gmail FROM gmail_submissions WHERE id = ?", (sub_id,))
    res = cursor.fetchone()
    
    if res:
        u_id, g_mail = res[0], res[1]
        if action == "approved":
            cursor.execute("UPDATE gmail_submissions SET status = 'approved' WHERE id = ?", (sub_id,))
            cursor.execute("UPDATE users SET balance = balance + 10.0 WHERE user_id = ?", (u_id,))
            conn.commit()
            bot.edit_message_text(f"✅ জিমেইল ({g_mail}) অ্যাপ্রুভ করা হয়েছে এবং ইউজারকে ৳১০ দেওয়া হয়েছে।", chat_id=ADMIN_ID, message_id=msg_id)
            try:
                bot.send_message(u_id, f"🎉 অভিনন্দন! আপনার সাবমিট করা জিমেইলটি ({g_mail}) অ্যাডমিন অ্যাপ্রুভ করেছে। আপনার ব্যালেন্সে ৳১০.০০ যোগ করা হয়েছে।")
            except:
                pass
        else:
            cursor.execute("UPDATE gmail_submissions SET status = 'rejected' WHERE id = ?", (sub_id,))
            conn.commit()
            bot.edit_message_text(f"❌ জিমেইল ({g_mail}) রিজেক্ট করা হয়েছে।", chat_id=ADMIN_ID, message_id=msg_id)
            try:
                bot.send_message(u_id, f"❌ দুঃখিত! আপনার সাবমিট করা জিমেইলটি ({g_mail}) সঠিক না হওয়ায় অ্যাডমিন সেটি রিজেক্ট করেছে। দয়া করে সঠিক জিমেইল সাবমিট করুন।")
            except:
                pass
    conn.close()

def manage_withdraw(req_id, action, msg_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, method, number, amount FROM withdraw_requests WHERE id = ?", (req_id,))
    res = cursor.fetchone()
    
    if res:
        u_id, method, num, amt = res[0], res[1], res[2], res[3]
        if action == "approved":
            cursor.execute("UPDATE withdraw_requests SET status = 'approved' WHERE id = ?", (req_id,))
            conn.commit()
            bot.edit_message_text(f"✅ {method} রিকোয়েস্ট (৳{amt:.2f} -> {num}) পেইড হিসেবেমার্ক করা হয়েছে।", chat_id=ADMIN_ID, message_id=msg_id)
            try:
                bot.send_message(u_id, f"💸 অভিনন্দন! আপনার ৳{amt:.2f} উইথড্র রিকোয়েস্টটি সফলভাবে সম্পূর্ণ হয়েছে এবং আপনার {method} নাম্বারে টাকা পাঠিয়ে দেওয়া হয়েছে।")
            except:
                pass
        else:
            cursor.execute("UPDATE withdraw_requests SET status = 'rejected' WHERE id = ?", (req_id,))
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, u_id))
            conn.commit()
            bot.edit_message_text(f"❌ {method} রিকোয়েস্ট (৳{amt:.2f} -> {num}) রিজেক্ট করা হয়েছে এবং ব্যালেন্স ফেরত দেওয়া হয়েছে।", chat_id=ADMIN_ID, message_id=msg_id)
            try:
                bot.send_message(u_id, f"❌ দুঃখিত! আপনার ৳{amt:.2f} উইথড্র রিকোয়েস্টটি রিজেক্ট করা হয়েছে এবং কেটে নেওয়া টাকা আপনার ওয়ালেটে ফেরত দেওয়া হয়েছে। যোগাযোগের জন্য অ্যাডমিনকে নক দিন।")
            except:
                pass
    conn.close()

if __name__ == "__main__":
    init_db()
    
    # রেন্ডার লাইভ হওয়ার পর অটোমেটিক রেন্ডারের লিংকের সাথে Webhook সেটআপ করে দেবে
    bot.remove_webhook()
    time.sleep(1)
    
    # আপনার রেন্ডার অ্যাপের ডোমেন লিংক এখানে দেওয়া হলো
    RENDER_APP_URL = "https://father-of-earn.onrender.com/"
    bot.set_webhook(url=RENDER_APP_URL + TOKEN)
    
    # ফ্লাস্ক সার্ভার চালু হচ্ছে (রেন্ডার পোর্ট ৮MD০ রিড করবে)
    app.run(host='0.0.0.0', port=8080)
