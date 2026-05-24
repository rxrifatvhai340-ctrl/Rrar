import telebot
from telebot import types
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import threading

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
db_lock = threading.Lock()

# Create tables
def init_db():
    with db_lock:
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
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS numbers_upload (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_id INTEGER,
            service_id INTEGER,
            numbers TEXT,
            count INTEGER,
            used_count INTEGER DEFAULT 0,
            UNIQUE(country_id, service_id)
        )
        """)
        
        conn.commit()

init_db()

# ================= WORKER =================
worker = ThreadPoolExecutor(max_workers=10)

# ================= STEP MEMORY =================
waiting_country = {}
waiting_service = {}
editing_country_id = {}
editing_service_id = {}

# Upload flow states
upload_flow_country = {}
upload_flow_service = {}
upload_flow_numbers = {}

# Get number flow states
get_number_service = {}
get_number_country = {}
get_number_current = {}


# ================= START =================
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    markup.row(
        types.KeyboardButton("📱 GET NUMBER"),
        types.KeyboardButton("🟢 LIVE SYSTEM")
    )
    
    markup.row(
        types.KeyboardButton("💰 WALLET"),
        types.KeyboardButton("💵 WITHDRAW")
    )
    
    markup.row(
        types.KeyboardButton("🔧 SUPPORT")
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
    
    if text is None:
        return
    
    # ---------- USER ----------
    if text == "📱 GET NUMBER":
        with db_lock:
            cursor.execute("SELECT id, service FROM services")
            services = cursor.fetchall()
        
        if not services:
            bot.send_message(m.chat.id, "⚠️ No services available")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for service_id, service_name in services:
            # Check if service has any numbers
            with db_lock:
                cursor.execute("""
                    SELECT COUNT(*) FROM numbers_upload 
                    WHERE service_id = ? AND count > 0
                """, (service_id,))
                
                count = cursor.fetchone()[0]
            if count > 0:
                markup.add(types.InlineKeyboardButton(f"⚙️ {service_name}", callback_data=f"get_select_service_{service_id}"))
        
        if not markup.keyboard:
            bot.send_message(m.chat.id, "⚠️ No numbers available for any service")
            return
        
        bot.send_message(m.chat.id, "⚙️ Select Service:", reply_markup=markup)
        return
    
    elif text == "🟢 LIVE SYSTEM":
        worker.submit(lambda: bot.send_message(m.chat.id, "✅ Online"))
        return
    
    elif text == "💰 WALLET":
        worker.submit(lambda: bot.send_message(m.chat.id, "💳 Balance: $0"))
        return
    
    elif text == "💵 WITHDRAW":
        worker.submit(lambda: bot.send_message(m.chat.id, "💸 Coming soon"))
        return
    
    elif text == "🔧 SUPPORT":
        worker.submit(lambda: bot.send_message(m.chat.id, "📩 @support"))
        return
    
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
        return
    
    # ---------- ADD COUNTRY INPUT ----------
    if uid in waiting_country and isinstance(waiting_country[uid], bool):
        country = text.strip()
        
        if not country:
            bot.send_message(m.chat.id, "⚠️ Country name cannot be empty")
            return
        
        try:
            with db_lock:
                cursor.execute("INSERT INTO countries (country, numbers) VALUES (?, ?)", (country, ''))
                conn.commit()
            bot.send_message(m.chat.id, f"✅ Country Saved: {country}")
        except sqlite3.IntegrityError:
            bot.send_message(m.chat.id, "⚠️ Country already exists")
        except Exception as e:
            bot.send_message(m.chat.id, f"⚠️ Error: {str(e)}")
        
        waiting_country.pop(uid, None)
        return
    
    # ---------- EDIT COUNTRY INPUT ----------
    if uid in editing_country_id:
        country_id = editing_country_id[uid]
        new_country_name = text.strip()
        
        if not new_country_name:
            bot.send_message(m.chat.id, "⚠️ Country name cannot be empty")
            return
        
        try:
            with db_lock:
                cursor.execute("UPDATE countries SET country = ? WHERE id = ?", (new_country_name, country_id))
                conn.commit()
            bot.send_message(m.chat.id, f"✅ Country Updated: {new_country_name}")
        except sqlite3.IntegrityError:
            bot.send_message(m.chat.id, "⚠️ Country name already exists")
        except Exception as e:
            bot.send_message(m.chat.id, f"⚠️ Error: {str(e)}")
        
        editing_country_id.pop(uid, None)
        return
    
    # ---------- ADD SERVICE INPUT ----------
    if uid in waiting_service and isinstance(waiting_service[uid], bool):
        service = text.strip()
        
        if not service:
            bot.send_message(m.chat.id, "⚠️ Service name cannot be empty")
            return
        
        try:
            with db_lock:
                cursor.execute("INSERT INTO services (service, numbers) VALUES (?, ?)", (service, ''))
                conn.commit()
            bot.send_message(m.chat.id, f"✅ Service Added: {service}")
        except sqlite3.IntegrityError:
            bot.send_message(m.chat.id, "⚠️ Service already exists")
        except Exception as e:
            bot.send_message(m.chat.id, f"⚠️ Error: {str(e)}")
        
        waiting_service.pop(uid, None)
        return
    
    # ---------- EDIT SERVICE INPUT ----------
    if uid in editing_service_id:
        service_id = editing_service_id[uid]
        new_service_name = text.strip()
        
        if not new_service_name:
            bot.send_message(m.chat.id, "⚠️ Service name cannot be empty")
            return
        
        try:
            with db_lock:
                cursor.execute("UPDATE services SET service = ? WHERE id = ?", (new_service_name, service_id))
                conn.commit()
            bot.send_message(m.chat.id, f"✅ Service Updated: {new_service_name}")
        except sqlite3.IntegrityError:
            bot.send_message(m.chat.id, "⚠️ Service name already exists")
        except Exception as e:
            bot.send_message(m.chat.id, f"⚠️ Error: {str(e)}")
        
        editing_service_id.pop(uid, None)
        return


# ================= FILE HANDLER FOR TXT UPLOAD =================
@bot.message_handler(content_types=['document'])
def handle_file(message):
    uid = message.from_user.id
    
    # Check if user is in upload flow
    if uid not in upload_flow_country or uid not in upload_flow_service:
        return
    
    # Check if file is txt
    if not message.document.file_name.endswith('.txt'):
        bot.send_message(message.chat.id, "⚠️ Only .txt files accepted")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Read and parse numbers
        numbers_text = downloaded_file.decode('utf-8', errors='ignore')
        numbers_list = []
        
        for line in numbers_text.split('\n'):
            for num in line.split(','):
                num = num.strip()
                if num:
                    numbers_list.append(num)
        
        if not numbers_list:
            bot.send_message(message.chat.id, "⚠️ No numbers found in file")
            return
        
        upload_flow_numbers[uid] = numbers_list
        
        # Get country and service details
        country_id = upload_flow_country[uid]
        service_id = upload_flow_service[uid]
        
        with db_lock:
            cursor.execute("SELECT country FROM countries WHERE id = ?", (country_id,))
            country_result = cursor.fetchone()
            cursor.execute("SELECT service FROM services WHERE id = ?", (service_id,))
            service_result = cursor.fetchone()
        
        country_name = country_result[0] if country_result else "Unknown"
        service_name = service_result[0] if service_result else "Unknown"
        
        # Create preview
        total_count = len(numbers_list)
        sample_numbers = numbers_list[:5]
        
        preview_text = f"""📊 UPLOAD PREVIEW

🌍 Country: {country_name}
⚙️ Service: {service_name}
📊 Total Count: {total_count}

📝 Sample Numbers (First 5):
"""
        for i, num in enumerate(sample_numbers, 1):
            preview_text += f"\n{i}. {num}"
        
        if total_count > 5:
            preview_text += f"\n... and {total_count - 5} more"
        
        # Show confirm buttons
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Confirm & Save", callback_data=f"confirm_upload_{country_id}_{service_id}"),
            types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")
        )
        
        bot.send_message(message.chat.id, preview_text, reply_markup=markup)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error reading file: {str(e)}")


# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id
    
    # ---------- GET NUMBER - SELECT SERVICE ----------
    if call.data.startswith("get_select_service_"):
        try:
            service_id = int(call.data.split("_")[-1])
            get_number_service[uid] = service_id
            
            # Get service name
            with db_lock:
                cursor.execute("SELECT service FROM services WHERE id = ?", (service_id,))
                service_result = cursor.fetchone()
                cursor.execute("""
                    SELECT DISTINCT c.id, c.country 
                    FROM countries c
                    JOIN numbers_upload n ON c.id = n.country_id
                    WHERE n.service_id = ? AND n.count > 0
                """, (service_id,))
                countries = cursor.fetchall()
            
            service_name = service_result[0] if service_result else "Unknown"
            
            if not countries:
                bot.answer_callback_query(call.id, "⚠️ No numbers available for this service")
                return
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            for country_id, country_name in countries:
                markup.add(types.InlineKeyboardButton(f"🌍 {country_name}", callback_data=f"get_select_country_{country_id}_{service_id}"))
            
            bot.edit_message_text("🌍 Select Country:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- GET NUMBER - SELECT COUNTRY & SHOW TABLE ----------
    elif call.data.startswith("get_select_country_"):
        try:
            parts = call.data.split("_")
            country_id = int(parts[3])
            service_id = int(parts[4])
            
            get_number_country[uid] = country_id
            get_number_service[uid] = service_id
            
            # Get the numbers for this country-service combo
            with db_lock:
                cursor.execute("""
                    SELECT c.country, s.service, n.numbers, n.used_count, n.count
                    FROM numbers_upload n
                    JOIN countries c ON n.country_id = c.id
                    JOIN services s ON n.service_id = s.id
                    WHERE n.country_id = ? AND n.service_id = ?
                """, (country_id, service_id))
                result = cursor.fetchone()
            
            if not result:
                bot.answer_callback_query(call.id, "⚠️ No numbers found")
                return
            
            country_name, service_name, numbers_str, used_count, total_count = result
            numbers_list = [n.strip() for n in numbers_str.split('\n') if n.strip()]
            
            if not numbers_list or used_count >= len(numbers_list):
                bot.send_message(call.message.chat.id, "⚠️ All numbers have been used for this country-service combo")
                return
            
            # Get next available number
            available_number = numbers_list[used_count]
            
            # Store current number
            get_number_current[uid] = (available_number, country_id, service_id, used_count, total_count, country_name, service_name)
            
            # Create table view
            table_text = f"""
┌─────────────────────────────────┐
│  🌍 Country: {country_name}
│  ⚙️ Service: {service_name}
│  📱 Number: `{available_number}`
│  📊 Progress: {used_count + 1}/{total_count}
└─────────────────────────────────┘"""
            
            # Button to get number with copy feature
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("📋 Copy Number", callback_data=f"copy_number_{country_id}_{service_id}"))
            markup.row(
                types.InlineKeyboardButton("🔄 Change Number", callback_data=f"change_number_{country_id}_{service_id}"),
                types.InlineKeyboardButton("🌍 Change Country", callback_data=f"back_to_country_{service_id}")
            )
            markup.add(types.InlineKeyboardButton("⬅️ Back to Service List", callback_data="back_to_service_list"))
            
            bot.send_message(call.message.chat.id, table_text, reply_markup=markup, parse_mode='Markdown')
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- COPY NUMBER ----------
    elif call.data.startswith("copy_number_"):
        try:
            parts = call.data.split("_")
            country_id = int(parts[2])
            service_id = int(parts[3])
            
            if uid not in get_number_current:
                bot.answer_callback_query(call.id, "⚠️ Error")
                return
            
            available_number, _, _, used_count, total_count, _, _ = get_number_current[uid]
            
            # Update used count
            new_used_count = used_count + 1
            with db_lock:
                cursor.execute("""
                    UPDATE numbers_upload 
                    SET used_count = ? 
                    WHERE country_id = ? AND service_id = ?
                """, (new_used_count, country_id, service_id))
                conn.commit()
            
            # Copy to clipboard message
            copy_msg = f"""✅ NUMBER COPIED!

📱 Number: `{available_number}`

📊 Progress: {new_used_count}/{total_count}"""
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🔄 Change Number", callback_data=f"change_number_{country_id}_{service_id}"),
                types.InlineKeyboardButton("🌍 Change Country", callback_data=f"back_to_country_{service_id}")
            )
            markup.add(types.InlineKeyboardButton("⬅️ Back to Service List", callback_data="back_to_service_list"))
            
            bot.send_message(call.message.chat.id, copy_msg, reply_markup=markup, parse_mode='Markdown')
            bot.answer_callback_query(call.id, f"✅ {available_number} copied!")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- CHANGE NUMBER ----------
    elif call.data.startswith("change_number_"):
        try:
            parts = call.data.split("_")
            country_id = int(parts[2])
            service_id = int(parts[3])
            
            # Get the numbers for this country-service combo
            with db_lock:
                cursor.execute("""
                    SELECT c.country, s.service, n.numbers, n.used_count, n.count
                    FROM numbers_upload n
                    JOIN countries c ON n.country_id = c.id
                    JOIN services s ON n.service_id = s.id
                    WHERE n.country_id = ? AND n.service_id = ?
                """, (country_id, service_id))
                result = cursor.fetchone()
            
            if not result:
                bot.answer_callback_query(call.id, "⚠️ No numbers found")
                return
            
            country_name, service_name, numbers_str, used_count, total_count = result
            numbers_list = [n.strip() for n in numbers_str.split('\n') if n.strip()]
            
            if used_count >= len(numbers_list):
                bot.send_message(call.message.chat.id, "⚠️ All numbers have been used!")
                return
            
            # Get next available number
            available_number = numbers_list[used_count]
            
            # Store current number
            get_number_current[uid] = (available_number, country_id, service_id, used_count, total_count, country_name, service_name)
            
            # Create table view
            table_text = f"""
┌─────────────────────────────────┐
│  🌍 Country: {country_name}
│  ⚙️ Service: {service_name}
│  📱 Number: `{available_number}`
│  📊 Progress: {used_count + 1}/{total_count}
└─────────────────────────────────┘"""
            
            # Button to get number with copy feature
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("📋 Copy Number", callback_data=f"copy_number_{country_id}_{service_id}"))
            markup.row(
                types.InlineKeyboardButton("🔄 Change Number", callback_data=f"change_number_{country_id}_{service_id}"),
                types.InlineKeyboardButton("🌍 Change Country", callback_data=f"back_to_country_{service_id}")
            )
            markup.add(types.InlineKeyboardButton("⬅️ Back to Service List", callback_data="back_to_service_list"))
            
            bot.edit_message_text(table_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='Markdown')
            bot.answer_callback_query(call.id, "✅ Number changed!")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- BACK TO COUNTRY LIST ----------
    elif call.data.startswith("back_to_country_"):
        try:
            service_id = int(call.data.split("_")[-1])
            
            # Show countries that have numbers for this service
            with db_lock:
                cursor.execute("""
                    SELECT DISTINCT c.id, c.country 
                    FROM countries c
                    JOIN numbers_upload n ON c.id = n.country_id
                    WHERE n.service_id = ? AND n.count > 0
                """, (service_id,))
                countries = cursor.fetchall()
            
            if not countries:
                bot.answer_callback_query(call.id, "⚠️ No countries available")
                return
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            for country_id, country_name in countries:
                markup.add(types.InlineKeyboardButton(f"🌍 {country_name}", callback_data=f"get_select_country_{country_id}_{service_id}"))
            
            markup.add(types.InlineKeyboardButton("⬅️ Back to Service List", callback_data="back_to_service_list"))
            
            bot.edit_message_text("🌍 Select Country:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- BACK TO SERVICE LIST ----------
    elif call.data == "back_to_service_list":
        try:
            with db_lock:
                cursor.execute("SELECT id, service FROM services")
                services = cursor.fetchall()
            
            if not services:
                bot.send_message(call.message.chat.id, "⚠️ No services available")
                return
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            for service_id, service_name in services:
                with db_lock:
                    cursor.execute("""
                        SELECT COUNT(*) FROM numbers_upload 
                        WHERE service_id = ? AND count > 0
                    """, (service_id,))
                    count = cursor.fetchone()[0]
                
                if count > 0:
                    markup.add(types.InlineKeyboardButton(f"⚙️ {service_name}", callback_data=f"get_select_service_{service_id}"))
            
            bot.edit_message_text("⚙️ Select Service:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # Admin section - check permission
    if uid not in ADMIN_IDS and not call.data.startswith("get_") and not call.data.startswith("copy_") and not call.data.startswith("change_") and not call.data.startswith("back_"):
        bot.answer_callback_query(call.id, "⛔ No permission")
        return
    
    # ---------- ADD COUNTRY ----------
    if call.data == "add_country":
        waiting_country[uid] = True
        bot.send_message(call.message.chat.id, "🌍 Send country name:\nExample: Myanmar")
    
    # ---------- ADD SERVICE ----------
    elif call.data == "add_service":
        waiting_service[uid] = True
        bot.send_message(call.message.chat.id, "⚙️ Enter service name:\n\nExample: Facebook")
    
    # ---------- COUNTRY BOARD ----------
    elif call.data == "country_board":
        with db_lock:
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
        try:
            country_id = int(call.data.split("_")[-1])
            with db_lock:
                cursor.execute("SELECT country FROM countries WHERE id = ?", (country_id,))
                result = cursor.fetchone()
            
            if not result:
                bot.answer_callback_query(call.id, "Country not found")
                return
            
            country_name = result[0]
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("✏️ Edit", callback_data=f"edit_country_{country_id}"),
                types.InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_country_{country_id}"),
                types.InlineKeyboardButton("📤 Upload Numbers", callback_data=f"upload_country_{country_id}"),
                types.InlineKeyboardButton("🔄 Clear Numbers", callback_data=f"clear_country_{country_id}"),
                types.InlineKeyboardButton("⬅️ Back", callback_data="country_board")
            )
            
            bot.edit_message_text(f"🌍 {country_name}\n\nSelect Action:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- DELETE COUNTRY ----------
    elif call.data.startswith("delete_country_"):
        try:
            country_id = int(call.data.split("_")[-1])
            with db_lock:
                cursor.execute("DELETE FROM countries WHERE id = ?", (country_id,))
                cursor.execute("DELETE FROM numbers_upload WHERE country_id = ?", (country_id,))
                conn.commit()
            bot.answer_callback_query(call.id, "✅ Country Deleted")
            bot.edit_message_text("✅ Country deleted!", call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")
    
    # ---------- EDIT COUNTRY ----------
    elif call.data.startswith("edit_country_"):
        try:
            country_id = int(call.data.split("_")[-1])
            editing_country_id[uid] = country_id
            bot.send_message(call.message.chat.id, "🌍 Send new country name:")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- UPLOAD COUNTRY NUMBERS ----------
    elif call.data.startswith("upload_country_"):
        try:
            country_id = int(call.data.split("_")[-1])
            upload_flow_country[uid] = country_id
            
            with db_lock:
                cursor.execute("SELECT id, service FROM services")
                services = cursor.fetchall()
            
            if not services:
                bot.send_message(call.message.chat.id, "⚠️ Add services first")
                upload_flow_country.pop(uid, None)
                return
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            for service_id, service_name in services:
                markup.add(types.InlineKeyboardButton(f"⚙️ {service_name}", callback_data=f"select_service_for_upload_{service_id}"))
            
            bot.send_message(call.message.chat.id, "⚙️ Select Service:", reply_markup=markup)
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- SELECT SERVICE FOR UPLOAD ----------
    elif call.data.startswith("select_service_for_upload_"):
        try:
            service_id = int(call.data.split("_")[-1])
            upload_flow_service[uid] = service_id
            bot.send_message(call.message.chat.id, "📄 Send .txt file\n\nNumbers format:\n- One per line\n- Or comma separated")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- CONFIRM AND SAVE UPLOAD ----------
    elif call.data.startswith("confirm_upload_"):
        try:
            parts = call.data.split("_")
            country_id = int(parts[2])
            service_id = int(parts[3])
            
            if uid not in upload_flow_numbers:
                bot.answer_callback_query(call.id, "⚠️ Error")
                return
            
            numbers_list = upload_flow_numbers[uid]
            numbers_str = "\n".join(numbers_list)
            
            with db_lock:
                cursor.execute("SELECT id FROM numbers_upload WHERE country_id = ? AND service_id = ?", (country_id, service_id))
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute("UPDATE numbers_upload SET numbers = ?, count = ?, used_count = 0 WHERE country_id = ? AND service_id = ?", 
                                 (numbers_str, len(numbers_list), country_id, service_id))
                else:
                    cursor.execute("INSERT INTO numbers_upload (country_id, service_id, numbers, count, used_count) VALUES (?, ?, ?, ?, ?)",
                                 (country_id, service_id, numbers_str, len(numbers_list), 0))
                
                conn.commit()
            
            bot.edit_message_text(f"✅ Saved Successfully!\n\n📊 Total: {len(numbers_list)} numbers", 
                                 call.message.chat.id, call.message.message_id)
            
            upload_flow_country.pop(uid, None)
            upload_flow_service.pop(uid, None)
            upload_flow_numbers.pop(uid, None)
            
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")
    
    # ---------- CANCEL UPLOAD ----------
    elif call.data == "cancel_upload":
        try:
            upload_flow_country.pop(uid, None)
            upload_flow_service.pop(uid, None)
            upload_flow_numbers.pop(uid, None)
            bot.edit_message_text("❌ Cancelled", call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- CLEAR COUNTRY NUMBERS ----------
    elif call.data.startswith("clear_country_"):
        try:
            country_id = int(call.data.split("_")[-1])
            with db_lock:
                cursor.execute("DELETE FROM numbers_upload WHERE country_id = ?", (country_id,))
                conn.commit()
            bot.answer_callback_query(call.id, "✅ Cleared")
            bot.edit_message_text("✅ Numbers cleared!", call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")
    
    # ---------- SERVICE BOARD ----------
    elif call.data == "service_board":
        with db_lock:
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
        try:
            service_id = int(call.data.split("_")[-1])
            with db_lock:
                cursor.execute("SELECT service FROM services WHERE id = ?", (service_id,))
                result = cursor.fetchone()
            
            if not result:
                bot.answer_callback_query(call.id, "Service not found")
                return
            
            service_name = result[0]
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("✏️ Edit", callback_data=f"edit_service_{service_id}"),
                types.InlineKeyboardButton("🗑️ Delete", callback_data=f"delete_service_{service_id}"),
                types.InlineKeyboardButton("📤 Upload Numbers", callback_data=f"upload_service_{service_id}"),
                types.InlineKeyboardButton("🔄 Clear Numbers", callback_data=f"clear_service_{service_id}"),
                types.InlineKeyboardButton("⬅️ Back", callback_data="service_board")
            )
            
            bot.edit_message_text(f"⚙️ {service_name}\n\nSelect Action:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- DELETE SERVICE ----------
    elif call.data.startswith("delete_service_"):
        try:
            service_id = int(call.data.split("_")[-1])
            with db_lock:
                cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
                cursor.execute("DELETE FROM numbers_upload WHERE service_id = ?", (service_id,))
                conn.commit()
            bot.answer_callback_query(call.id, "✅ Service Deleted")
            bot.edit_message_text("✅ Service deleted!", call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")
    
    # ---------- EDIT SERVICE ----------
    elif call.data.startswith("edit_service_"):
        try:
            service_id = int(call.data.split("_")[-1])
            editing_service_id[uid] = service_id
            bot.send_message(call.message.chat.id, "⚙️ Send new service name:")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- UPLOAD SERVICE NUMBERS ----------
    elif call.data.startswith("upload_service_"):
        try:
            service_id = int(call.data.split("_")[-1])
            upload_flow_service[uid] = service_id
            
            with db_lock:
                cursor.execute("SELECT id, country FROM countries")
                countries = cursor.fetchall()
            
            if not countries:
                bot.send_message(call.message.chat.id, "⚠️ Add countries first")
                upload_flow_service.pop(uid, None)
                return
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            for country_id, country_name in countries:
                markup.add(types.InlineKeyboardButton(f"🌍 {country_name}", callback_data=f"select_country_for_upload_{country_id}"))
            
            bot.send_message(call.message.chat.id, "🌍 Select Country:", reply_markup=markup)
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- SELECT COUNTRY FOR UPLOAD ----------
    elif call.data.startswith("select_country_for_upload_"):
        try:
            country_id = int(call.data.split("_")[-1])
            upload_flow_country[uid] = country_id
            bot.send_message(call.message.chat.id, "📄 Send .txt file\n\nNumbers format:\n- One per line\n- Or comma separated")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Error: {str(e)}")
    
    # ---------- CLEAR SERVICE NUMBERS ----------
    elif call.data.startswith("clear_service_"):
        try:
            service_id = int(call.data.split("_")[-1])
            with db_lock:
                cursor.execute("DELETE FROM numbers_upload WHERE service_id = ?", (service_id,))
                conn.commit()
            bot.answer_callback_query(call.id, "✅ Cleared")
            bot.edit_message_text("✅ Numbers cleared!", call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Error: {str(e)}")
    
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
print("🚀 BOT RUNNING - FULL FEATURED GET NUMBER SYSTEM ACTIVE")
bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
