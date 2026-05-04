import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

load_dotenv()
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    with get_conn() as conn, conn.cursor() as cur:
        with open("schema.sql", "r") as f:
            cur.execute(f.read())
        conn.commit()

ADD_NAME, ADD_PHONE, ADD_PRICING, ADD_RATE, LESSON_HOURS, LESSON_NOTE = range(6)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Tilføj kunde", callback_data="add_customer")],
        [InlineKeyboardButton("📋 Vis kunder", callback_data="list_customers")],
        [InlineKeyboardButton("📝 Ny lektion", callback_data="new_lesson")],
        [InlineKeyboardButton("📅 Månedsafslutning", callback_data="month_close")],
    ]
    await update.message.reply_text("Vælg handling:", reply_markup=InlineKeyboardMarkup(keyboard))

async def add_customer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Hvad hedder kunden?")
    return ADD_NAME

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Telefonnummer (skriv - for at springe over):")
    return ADD_PHONE

async def add_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    context.user_data["phone"] = None if phone == "-" else phone
    keyboard = [[InlineKeyboardButton("Timepris", callback_data="type_hourly"), InlineKeyboardButton("Fast måned", callback_data="type_monthly")]]
    await update.message.reply_text("Betalingstype? (tryk på knap, eller skriv 'time' / 'fast')", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADD_PRICING

async def add_pricing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        data = query.data
        msg = query.message
    else:
        data = update.message.text.lower()
        msg = update.message
        if "time" in data:
            data = "type_hourly"
        elif "fast" in data or "måned" in data:
            data = "type_monthly"
        else:
            await msg.reply_text("Tryk på knappen, eller skriv 'time' eller 'fast'")
            return ADD_PRICING

    ptype = "hourly" if "hourly" in data else "monthly"
    context.user_data["pricing_type"] = ptype
    if ptype == "hourly":
        await msg.reply_text("Timepris i kr (fx 250 eller 200):")
    else:
        await msg.reply_text("Fast pris pr. måned i kr (fx 800):")
    return ADD_RATE

async def add_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rate = int(update.message.text)
    except:
        rate = 0
    ptype = context.user_data["pricing_type"]
    hourly = rate if ptype == "hourly" else 0
    monthly = rate if ptype == "monthly" else 0
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO customers (name, phone, pricing_type, hourly_rate, monthly_price) VALUES (%s,%s,%s)",
                    (context.user_data["name"], context.user_data["phone"], ptype, hourly, monthly))
        conn.commit()
    await update.message.reply_text(f"Kunde {context.user_data['name']} oprettet som {ptype} ✅")
    return ConversationHandler.END

async def list_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT name, pricing_type, hourly_rate, monthly_price FROM customers ORDER BY name")
        rows = cur.fetchall()
    if not rows:
        await query.message.reply_text("Ingen kunder endnu.")
        return
    lines = []
    for r in rows:
        if r["pricing_type"] == "hourly":
            lines.append(f"{r['name']} – {r['hourly_rate']} kr/t")
        else:
            lines.append(f"{r['name']} – {r['monthly_price']} kr/md")
    await query.message.reply_text("Kunder:\n" + "\n".join(lines))

async def new_lesson_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name FROM customers ORDER BY name")
        customers = cur.fetchall()
    if not customers:
        await query.message.reply_text("Tilføj en kunde først.")
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(c["name"], callback_data=f"lesson_{c['id']}")] for c in customers]
    await query.message.reply_text("Vælg kunde:", reply_markup=InlineKeyboardMarkup(keyboard))
    return LESSON_HOURS

async def lesson_choose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cust_id = int(query.data.split("_")[1])
    context.user_data["cust_id"] = cust_id
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT pricing_type, hourly_rate FROM customers WHERE id=%s", (cust_id,))
        cust = cur.fetchone()
    context.user_data["pricing"] = cust
    if cust["pricing_type"] == "hourly":
        await query.message.reply_text(f"Timepris er {cust['hourly_rate']} kr. Hvor mange timer? (fx 1 eller 1.5)")
        return LESSON_HOURS
    else:
        context.user_data["hours"] = None
        context.user_data["amount"] = 0
        await query.message.reply_text("Fast-pris kunde – skriv note for lektionen (eller -):")
        return LESSON_NOTE

async def lesson_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        hours = float(update.message.text.replace(",", "."))
    except:
        await update.message.reply_text("Skriv tal, fx 1.5")
        return LESSON_HOURS
    rate = context.user_data["pricing"]["hourly_rate"]
    amount = int(hours * rate)
    context.user_data["hours"] = hours
    context.user_data["amount"] = amount
    await update.message.reply_text(f"{hours} time = {amount} kr. Note? (eller -)")
    return LESSON_NOTE

async def lesson_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text
    if note == "-": note = None
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO lessons (customer_id, amount, note, hours) VALUES (%s,%s,%s,%s)",
                    (context.user_data["cust_id"], context.user_data["amount"], note, context.user_data.get("hours")))
        conn.commit()
    await update.message.reply_text("Lektion gemt ✅")
    return ConversationHandler.END

async def month_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name, pricing_type, hourly_rate, monthly_price FROM customers")
        customers = cur.fetchall()
    for c in customers:
        if c["pricing_type"] == "hourly":
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute("SELECT COALESCE(SUM(amount),0) as total, COUNT(*) as antal FROM lessons WHERE customer_id=%s AND invoiced=FALSE", (c["id"],))
                data = cur.fetchone()
                total, antal = data["total"], data["antal"]
            if total == 0: continue
            text = f"*{c['name']}* (time)\n{antal} lektioner\nTotal: {total} kr"
        else:
            total = c["monthly_price"]
            text = f"*{c['name']}* (fast)\nMånedspris: {total} kr"
        keyboard = [[InlineKeyboardButton("Betalt", callback_data=f"pay_{c['id']}_{total}"), InlineKeyboardButton("Skylder", callback_data=f"owe_{c['id']}_{total}")]]
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, cust_id, total = query.data.split("_")
    cust_id, total = int(cust_id), int(total)
    status = "betalt" if action == "pay" else "skylder"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO payments (customer_id, amount, status) VALUES (%s,%s,%s)", (cust_id, total, status))
        cur.execute("UPDATE lessons SET invoiced=TRUE WHERE customer_id=%s AND invoiced=FALSE", (cust_id,))
        conn.commit()
    await query.message.reply_text(f"Markeret som {status} ✅")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Annulleret")
    return ConversationHandler.END

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    conv_add = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_customer_start, pattern="^add_customer$")],
        states={
            ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
            ADD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_phone)],
            ADD_PRICING: [
                CallbackQueryHandler(add_pricing, pattern="^type_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_pricing)
            ],
            ADD_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_rate)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_message=False
    )

    conv_lesson = ConversationHandler(
        entry_points=[CallbackQueryHandler(new_lesson_start, pattern="^new_lesson$")],
        states={
            LESSON_HOURS: [
                CallbackQueryHandler(lesson_choose, pattern="^lesson_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lesson_hours)
            ],
            LESSON_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, lesson_note)]
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
        per_message=False
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_add)
    app.add_handler(conv_lesson)
    app.add_handler(CallbackQueryHandler(list_customers, pattern="^list_customers$"))
    app.add_handler(CallbackQueryHandler(month_close, pattern="^month_close$"))
    app.add_handler(CallbackQueryHandler(handle_payment, pattern="^(pay|owe)_"))

    logging.info("Bot kører...")
    app.run_polling()

if __name__ == "__main__":
    main()