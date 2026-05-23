import telebot
from telebot import types
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import os

TOKEN = "8721478017:AAHIDuAOV0TRUT7iJTdtxOUF18Zh-wupPwE"

bot = telebot.TeleBot(
    TOKEN,
    threaded=True,
    num_threads=5
)

ADMIN_IDS = [8364889419]

# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS countries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT UNIQUE,
    numbers TEXT DEFAULT ''
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service TEXT UNIQUE,
    numbers TEXT DEFAULT ''
)
""")

conn.commit()


# ================= WORKER =================
worker = ThreadPoolExecutor(max_workers=10)


# ================= STEP MEMORY =================
waiting_country = {}
waiting_service = {}
waiting_upload_number = {}
editing_country_id = {}
editing_service_id = {}

# New states for upload flow
upload_flow_country = {}
upload_flow_service = {}
upload_flow_numbers = {}


# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.row(
        types.KeyboardButton("☎️ GET NUMBER"),
        types.KeyboardButton("🟢 LIVE SYSTEM")
    )

    markup.row(
        types.KeyboardButton("👛 WALLET"),
        types.KeyboardButton("💵 WITHDRAW")
    )

    markup.row(
        types.KeyboardButton("🛠️ SUPPORT")
    )

    if message.from_user.id in ADMIN_IDS:
        markup.row(types.KeyboardButton("⚙️ ADMIN SETTINGS"))

    bot.send_message(message.chat.id, "✨ Bot Started", reply_markup=markup)


# ================= ADMIN PANEL =================
def admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton("➕ Add Country", callback_data="add_country"),
        types.InlineKeyboardButton("➕ Add Service", callback_data="add_service"),
        types.InlineKeyboardButton("🌍 Country Board", callback_data="country_board"),
        types.InlineKeyboardButton("⚙️ Service Board", callback_data="service_board"),
        types.InlineKeyboardButton("📡 OTP Provider", callback_data="otp_provider"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="broadcast"),
        types.InlineKeyboardButton("📡 Force Channel", callback_data="force_channel"),
        types.InlineKeyboardButton("⚙️ System Setting", callback_data="system_setting"),
        types.InlineKeyboardButton("🚫 Ban / Unban", callback_data="ban_unban"),
        types.InlineKeyboardButton("❌ Close", callback_data="close")
    )

    return markup


# ================= MESSAGE HANDLER =================
@bot.message_handler(func=lambda m: True)
def handle(m):

    uid = m.from_user.id
    text = m.text


    # ---------- USER ----------
    if text == "☎️ GET NUMBER":
        worker.submit(lambda: bot.send_message(m.chat.id, "📲 Processing..."))

    elif text == "🟢 LIVE SYSTEM":
        worker.submit(lambda: bot.send_message(m.chat.id, "✅ Online"))

    elif text == "👛 WALLET":
        worker.submit(lambda: bot.send_message(m.chat.id, "💰 Balance: $0"))

    elif text == "💵 WITHDRAW":
        worker.submit(lambda: bot.send_message(m.chat.id, "💸 Coming soon"))

    elif text == "🛠️ SUPPORT":
        worker.submit(lambda: bot.send_message(m.chat.id, "📩 @support"))


    # ---------- ADMIN OPEN ----------
    elif text == "⚙️ ADMIN SETTINGS":
        if uid in ADMIN_IDS:
            bot.send_message(
                m.chat.id,
                "🔐 ADMIN PANEL",
                reply_markup=admin_panel()
            )
        else:
            bot.send_message(m.chat.id, "⛔ Not admin")


    # ---------- ADD COUNTRY INPUT ----------
    if uid in waiting_country and isinstance(waiting_country[uid], bool):

        country = text

        try:
            cursor.execute("INSERT INTO countries (country, numbers) VALUES (?, ?)", (country, ''))
            conn.commit()
            bot.send_message(m.chat.id, f"✅ Country Saved: {country}")
        except:
            bot.send_message(m.chat.id, "⚠️ Already exists / error")

        waiting_country.pop(uid, None)
        return


    # ---------- EDIT COUNTRY INPUT ----------
    if uid in editing_country_id:
        country_id = editing_country_id[uid]
        new_country_name = text

        try:
            cursor.execute("UPDATE countries SET country = ? WHERE id = ?", (new_country_name, country_id))
            conn.commit()
            bot.send_message(m.chat.id, f"✅ Country Updated: {new_country_name}")
        except:
            bot.send_message(m.chat.id, "⚠️ Error updating country")

        editing_country_id.pop(uid, None)
        return


    # ---------- ADD SERVICE INPUT ----------
    if uid in waiting_service and isinstance(waiting_service[uid], bool):

        service = m.text.strip()

        try:
            cursor.execute("INSERT INTO services (service, numbers) VALUES (?, ?)", (service, ''))
            conn.commit()

            bot.send_message(m.chat.id, f"✅ Service Added: {service}")

        except:
            bot.send_message(m.chat.id, "⚠️ Already exists or error!")

        waiting_service.pop(uid, None)
        return


    # ---------- EDIT SERVICE INPUT ----------
    if uid in editing_service_id:
        service_id = editing_service_id[uid]
        new_service_name = m.text.strip()

        try:
            cursor.execute("UPDATE services SET service = ? WHERE id = ?", (new_service_name, service_id))
            conn.commit()
            bot.send_message(m.chat.id, f"✅ Service Updated: {new_service_name}")
        except:
            bot.send_message(m.chat.id, "⚠️ Error updating service")

        editing_service_id.pop(uid, None)
        return


    # ---------- UPLOAD NUMBERS (OLD METHOD - REMOVED) ----------
    # Removed old upload_number flow


# ================= FILE HANDLER FOR TXT UPLOAD =================
@bot.message_handler(content_types=['document'])
def handle_file(message):
    uid = message.from_user.id
    
    # Check if user is in upload flow
    if uid not in upload_flow_country or uid not in upload_flow_service:
        return
    
    # Check if file is txt
    file_info = bot.get_file(message.document.file_id)
    if not message.document.file_name.endswith('.txt'):
        bot.send_message(message.chat.id, "⚠️ শুধুমাত্র .txt ফাইল গ্রহণ করা হয়")
        return
    
    try:
        # Download file
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Read numbers from file
        numbers_text = downloaded_file.decode('utf-8')
        
        # Parse numbers (split by newline or comma)
        numbers_list = []
        for line in numbers_text.split('\n'):
            for num in line.split(','):
                num = num.strip()
                if num:
                    numbers_list.append(num)
        
        if not numbers_list:
            bot.send_message(message.chat.id, "⚠️ ফাইলে কোন নম্বর নেই")
            return
        
        # Store numbers in memory
        upload_flow_numbers[uid] = numbers_list
        
        # Get country and service details
        country_id = upload_flow_country[uid]
        service_id = upload_flow_service[uid]
        
        cursor.execute("SELECT country FROM countries WHERE id = ?", (country_id,))
        country_name = cursor.fetchone()[0]
        
        cursor.execute("SELECT service FROM services WHERE id = ?", (service_id,))
        service_name = cursor.fetchone()[0]
        
        # Create preview
        total_count = len(numbers_list)
        sample_numbers = numbers_list[:5]  # Show first 5
        
        preview_text = f"""
📊 <b>UPLOAD PREVIEW</b>

🌍 <b>Country:</b> {country_name}
⚙️ <b>Service:</b> {service_name}
📊 <b>Total Count:</b> {total_count}

📝 <b>Sample Numbers (First 5):</b>
"""
        for i, num in enumerate(sample_numbers, 1):
            preview_text += f"\n{i}. {num}"
        
        if total_count > 5:
            preview_text += f"\n... এবং আরও {total_count - 5}টি"
        
        # Show confirm buttons
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Confirm & Save", callback_data=f"confirm_upload_{country_id}_{service_id}"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")
        )
        
        bot.send_message(message.chat.id, preview_text, reply_markup=markup, parse_mode='HTML')
        
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ ফাইল পড়তে ত্রুটি: {str(e)}")


# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    uid = call.from_user.id

    if uid not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ No permission")
        return


    # ---------- ADD COUNTRY ----------
    if call.data == "add_country":
        waiting_country[uid] = True
        bot.send_message(call.message.chat.id,
            "🌍 Send country:\nExample: 🇲🇲 Myanmar"
        )


    # ---------- ADD SERVICE ----------
    elif call.data == "add_service":
        waiting_service[uid] = True
        bot.send_message(call.message.chat.id,
            "⚙️ Enter service name:\n\nExample: Facebook"
        )


    # ---------- COUNTRY BOARD ----------
    elif call.data == "country_board":

        cursor.execute("SELECT id, country FROM countries")
        rows = cursor.fetchall()

        if not rows:
            bot.send_message(call.message.chat.id, "📊 No countries")
            return

        markup = types.InlineKeyboardMarkup(row_width=1)

        for country_id, country_name in rows:
            markup.add(types.InlineKeyboardButton(f"🌍 {country_name}", callback_data=f"country_options_{country_id}"))

        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="admin_panel_back"))

        bot.send_message(call.message.chat.id, "🌍 COUNTRY LIST:", reply_markup=markup)


    # ---------- COUNTRY OPTIONS ----------
    elif call.data.startswith("country_options_"):
        country_id = int(call.data.split("_")[-1])
        cursor.execute("SELECT country FROM countries WHERE id = ?", (country_id,))
        country_name = cursor.fetchone()[0]

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✏️ Edit", callback_data=f"edit_country_{country_id}"),
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_country_{country_id}"),
            types.InlineKeyboardButton("📤 Upload Numbers", callback_data=f"upload_country_{country_id}"),
            types.InlineKeyboardButton("🔄 Clear Numbers", callback_data=f"clear_country_{country_id}"),
            types.InlineKeyboardButton("⬅️ Back", callback_data="country_board")
        )

        bot.edit_message_text(f"🌍 {country_name}\n\nSelect Action:", call.message.chat.id, call.message.message_id, reply_markup=markup)


    # ---------- DELETE COUNTRY ----------
    elif call.data.startswith("delete_country_"):
        country_id = int(call.data.split("_")[-1])
        try:
            cursor.execute("DELETE FROM countries WHERE id = ?", (country_id,))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ Country Deleted")
            bot.edit_message_text("✅ Country deleted!", call.message.chat.id, call.message.message_id)
        except:
            bot.answer_callback_query(call.id, "❌ Error")


    # ---------- EDIT COUNTRY ----------
    elif call.data.startswith("edit_country_"):
        country_id = int(call.data.split("_")[-1])
        editing_country_id[uid] = country_id
        bot.send_message(call.message.chat.id, "🌍 Send new country name:")


    # ---------- UPLOAD COUNTRY NUMBERS (NEW FLOW) ----------
    elif call.data.startswith("upload_country_"):
        country_id = int(call.data.split("_")[-1])
        upload_flow_country[uid] = country_id
        
        # Show service list
        cursor.execute("SELECT id, service FROM services")
        services = cursor.fetchall()
        
        if not services:
            bot.send_message(call.message.chat.id, "⚠️ প্রথমে সার্ভিস যোগ করুন")
            upload_flow_country.pop(uid, None)
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for service_id, service_name in services:
            markup.add(types.InlineKeyboardButton(f"⚙️ {service_name}", callback_data=f"select_service_for_upload_{service_id}"))
        
        bot.send_message(call.message.chat.id, "⚙️ সার্ভিস নির্বাচন করুন:", reply_markup=markup)


    # ---------- SELECT SERVICE FOR UPLOAD ----------
    elif call.data.startswith("select_service_for_upload_"):
        service_id = int(call.data.split("_")[-1])
        upload_flow_service[uid] = service_id
        
        bot.send_message(call.message.chat.id, "📄 এখন .txt ফাইল পাঠান\n\n📌 ফাইলে নম্বরগুলি এমনভাবে থাকতে হবে:\n- প্রতিটি লাইনে একটি নম্বর\n- অথবা কমা দিয়ে আলাদা করা")


    # ---------- CONFIRM AND SAVE UPLOAD ----------
    elif call.data.startswith("confirm_upload_"):
        parts = call.data.split("_")
        country_id = int(parts[2])
        service_id = int(parts[3])
        
        if uid not in upload_flow_numbers:
            bot.answer_callback_query(call.id, "⚠️ ত্রুটি")
            return
        
        numbers_list = upload_flow_numbers[uid]
        numbers_str = "\n".join(numbers_list)
        
        try:
            # Create combined key for this country-service pair
            combined_key = f"{country_id}_{service_id}"
            
            # Check if entry exists
            cursor.execute("SELECT id FROM numbers_upload WHERE country_id = ? AND service_id = ?", (country_id, service_id))
            existing = cursor.fetchone()
            
            # Create table if not exists
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS numbers_upload (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_id INTEGER,
                service_id INTEGER,
                numbers TEXT,
                count INTEGER,
                UNIQUE(country_id, service_id)
            )
            """)
            
            if existing:
                cursor.execute("UPDATE numbers_upload SET numbers = ?, count = ? WHERE country_id = ? AND service_id = ?", 
                             (numbers_str, len(numbers_list), country_id, service_id))
            else:
                cursor.execute("INSERT INTO numbers_upload (country_id, service_id, numbers, count) VALUES (?, ?, ?, ?)",
                             (country_id, service_id, numbers_str, len(numbers_list)))
            
            conn.commit()
            
            bot.edit_message_text(f"✅ সফলভাবে সংরক্ষিত!\n\n📊 মোট নম্বর: {len(numbers_list)}", 
                                 call.message.chat.id, call.message.message_id)
            
            # Clean up
            upload_flow_country.pop(uid, None)
            upload_flow_service.pop(uid, None)
            upload_flow_numbers.pop(uid, None)
            
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ ত্রুটি: {str(e)}")


    # ---------- CANCEL UPLOAD ----------
    elif call.data == "cancel_upload":
        upload_flow_country.pop(uid, None)
        upload_flow_service.pop(uid, None)
        upload_flow_numbers.pop(uid, None)
        bot.edit_message_text("❌ বাতিল করা হয়েছে", call.message.chat.id, call.message.message_id)


    # ---------- CLEAR COUNTRY NUMBERS ----------
    elif call.data.startswith("clear_country_"):
        country_id = int(call.data.split("_")[-1])
        try:
            cursor.execute("DELETE FROM numbers_upload WHERE country_id = ?", (country_id,))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ Numbers Cleared")
            bot.edit_message_text("✅ Numbers cleared!", call.message.chat.id, call.message.message_id)
        except:
            bot.answer_callback_query(call.id, "❌ Error")


    # ---------- SERVICE BOARD ----------
    elif call.data == "service_board":

        cursor.execute("SELECT id, service FROM services")
        rows = cursor.fetchall()

        if not rows:
            bot.send_message(call.message.chat.id, "⚙️ No services")
            return

        markup = types.InlineKeyboardMarkup(row_width=1)

        for service_id, service_name in rows:
            markup.add(types.InlineKeyboardButton(f"⚙️ {service_name}", callback_data=f"service_options_{service_id}"))

        markup.add(types.InlineKeyboardButton("⬅️ Back", callback_data="admin_panel_back"))

        bot.send_message(call.message.chat.id, "⚙️ SERVICE LIST:", reply_markup=markup)


    # ---------- SERVICE OPTIONS ----------
    elif call.data.startswith("service_options_"):
        service_id = int(call.data.split("_")[-1])
        cursor.execute("SELECT service FROM services WHERE id = ?", (service_id,))
        service_name = cursor.fetchone()[0]

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("✏️ Edit", callback_data=f"edit_service_{service_id}"),
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_service_{service_id}"),
            types.InlineKeyboardButton("📤 Upload Numbers", callback_data=f"upload_service_{service_id}"),
            types.InlineKeyboardButton("🔄 Clear Numbers", callback_data=f"clear_service_{service_id}"),
            types.InlineKeyboardButton("⬅️ Back", callback_data="service_board")
        )

        bot.edit_message_text(f"⚙️ {service_name}\n\nSelect Action:", call.message.chat.id, call.message.message_id, reply_markup=markup)


    # ---------- DELETE SERVICE ----------
    elif call.data.startswith("delete_service_"):
        service_id = int(call.data.split("_")[-1])
        try:
            cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ Service Deleted")
            bot.edit_message_text("✅ Service deleted!", call.message.chat.id, call.message.message_id)
        except:
            bot.answer_callback_query(call.id, "❌ Error")


    # ---------- EDIT SERVICE ----------
    elif call.data.startswith("edit_service_"):
        service_id = int(call.data.split("_")[-1])
        editing_service_id[uid] = service_id
        bot.send_message(call.message.chat.id, "⚙️ Send new service name:")


    # ---------- UPLOAD SERVICE NUMBERS (NEW FLOW) ----------
    elif call.data.startswith("upload_service_"):
        service_id = int(call.data.split("_")[-1])
        upload_flow_service[uid] = service_id
        
        # Show country list
        cursor.execute("SELECT id, country FROM countries")
        countries = cursor.fetchall()
        
        if not countries:
            bot.send_message(call.message.chat.id, "⚠️ প্রথমে দেশ যোগ করুন")
            upload_flow_service.pop(uid, None)
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for country_id, country_name in countries:
            markup.add(types.InlineKeyboardButton(f"🌍 {country_name}", callback_data=f"select_country_for_upload_{country_id}"))
        
        bot.send_message(call.message.chat.id, "🌍 দেশ নির্বাচন করুন:", reply_markup=markup)


    # ---------- SELECT COUNTRY FOR UPLOAD ----------
    elif call.data.startswith("select_country_for_upload_"):
        country_id = int(call.data.split("_")[-1])
        upload_flow_country[uid] = country_id
        
        bot.send_message(call.message.chat.id, "📄 এখন .txt ফাইল পাঠান\n\n📌 ফাইলে নম্বরগুলি এমনভাবে থাকতে হবে:\n- প্রতিটি লাইনে একটি নম্বর\n- অথবা কমা দিয়ে আলাদা করা")


    # ---------- CLEAR SERVICE NUMBERS ----------
    elif call.data.startswith("clear_service_"):
        service_id = int(call.data.split("_")[-1])
        try:
            cursor.execute("DELETE FROM numbers_upload WHERE service_id = ?", (service_id,))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ Numbers Cleared")
            bot.edit_message_text("✅ Numbers cleared!", call.message.chat.id, call.message.message_id)
        except:
            bot.answer_callback_query(call.id, "❌ Error")


    # ---------- OTP PROVIDER ----------
    elif call.data == "otp_provider":
        bot.send_message(call.message.chat.id, """📡 OTP PROVIDER

📲 SMS Provider
🟢 WhatsApp Provider
📧 Gmail Provider

⚙️ Admin Controlled""")


    elif call.data == "broadcast":
        bot.send_message(call.message.chat.id, "📢 Broadcast")

    elif call.data == "force_channel":
        bot.send_message(call.message.chat.id, "📡 Force Channel")

    elif call.data == "system_setting":
        bot.send_message(call.message.chat.id, "⚙️ System Setting")

    elif call.data == "ban_unban":
        bot.send_message(call.message.chat.id, "🚫 Ban / Unban")

    elif call.data == "admin_panel_back":
        bot.edit_message_text("🔐 ADMIN PANEL", call.message.chat.id, call.message.message_id, reply_markup=admin_panel())

    elif call.data == "close":
        bot.delete_message(call.message.chat.id, call.message.message_id)


# ================= RUN =================
print("🚀 FULL BOT RUNNING (COUNTRY + SERVICE + ADMIN + WORKER + NEW UPLOAD FLOW)")
bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
