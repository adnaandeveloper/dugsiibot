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

ADD_NAME, ADD_PHONE, ADD_RATE, LESSON_AMOUNT, LESSON_NOTE = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Tilføj kunde", callback_data="add_customer")],
        [InlineKeyboardButton("📋 Vis kunder", callback_data="list_customers")],
        [InlineKeyboardButton("📝 Ny lektion", callback_data="new_lesson")],
        [InlineKeyboardButton("📅 Månedsafslutning", callback_data="month_close")],
    ]
    await update.message.reply_text("Vælg handling:", reply_markup=InlineKeyboardMarkup(keyboard))

async def add_customer_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Hvad hedder kunden?")
    return ADD_NAME

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Telefonnummer (skriv - for at springe over):")
    return ADD_PHONE

async def add_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text
    context.user_data["phone"] = None if phone == "-" else phone
    await update.message.reply_text("Timepris i kr (fx 250):")
    return ADD_RATE

async def add_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rate = int(update.message.text)
    except:
        rate = 0
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO customers (name, phone, hourly_rate) VALUES (%s,%s,%s)", 
                    (context.user_data["name"], context.user_data["phone"], rate))
        conn.commit()
    await update.message.reply_text(f"Kunde {context.user_data['name']} oprettet ✅")
    return ConversationHandler.END

async def list_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name, hourly_rate FROM customers ORDER BY name")
        rows = cur.fetchall()
    if not rows:
        await query.message.reply_text("Ingen kunder endnu.")
        return
    text = "Kunder:\n" + "\n".join([f"{r['id']}. {r['name']} – {r['hourly_rate']} kr" for r in rows])
    await query.message.reply_text(text)

async def new_lesson_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name FROM customers ORDER BY name")
        customers = cur.fetchall()
    if not customers:
        await query.message.reply_text("Tilføj en kunde først.")
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(c["name"], callback_data=f"lesson_cust_{c['id']}")] for c in customers]
    await query.message.reply_text("Vælg kunde:", reply_markup=InlineKeyboardMarkup(keyboard))
    return LESSON_AMOUNT

async def lesson_choose_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cust_id = int(query.data.split("_")[-1])
    context.user_data["cust_id"] = cust_id
    await query.message.reply_text("Beløb i kr (fx 250):")
    return LESSON_AMOUNT

async def lesson_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text)
    except:
        await update.message.reply_text("Skriv et tal, fx 250")
        return LESSON_AMOUNT
    context.user_data["amount"] = amount
    await update.message.reply_text("Note (fx '1,5 time' eller -):")
    return LESSON_NOTE

async def lesson_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note = update.message.text
    if note == "-": note = None
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO lessons (customer_id, amount, note) VALUES (%s,%s,%s)",
                    (context.user_data["cust_id"], context.user_data["amount"], note))
        conn.commit()
    await update.message.reply_text("Lektion gemt ✅")
    return ConversationHandler.END

async def month_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT c.id, c.name, COALESCE(SUM(l.amount),0) as total, COUNT(l.id) as antal FROM customers c LEFT JOIN lessons l ON l.customer_id = c.id AND l.invoiced = FALSE GROUP BY c.id, c.name HAVING COALESCE(SUM(l.amount),0) > 0")
        rows = cur.fetchall()
    if not rows:
        await query.message.reply_text("Ingen ufakturerede lektioner.")
        return
    for r in rows:
        text = f"*{r['name']}*\nAntal: {r['antal']}\nTotal: {r['total']} kr"
        keyboard = [[InlineKeyboardButton("Marker betalt", callback_data=f"pay_{r['id']}_{r['total']}"), InlineKeyboardButton("Skylder", callback_data=f"owe_{r['id']}_{r['total']}")]]
        await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, cust_id, total = query.data.split("_")
    cust_id, total = int(cust_id), int(total)
    status = "betalt" if action == "pay" else "skylder"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO payments (customer_id, amount, status) VALUES (%s,%s,%s)", (cust_id, total, status))
        cur.execute("UPDATE lessons SET invoiced = TRUE WHERE customer_id = %s AND invoiced = FALSE", (cust_id,))
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
        states={ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)], ADD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_phone)], ADD_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_rate)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    conv_lesson = ConversationHandler(
        entry_points=[CallbackQueryHandler(new_lesson_start, pattern="^new_lesson$")],
        states={LESSON_AMOUNT: [CallbackQueryHandler(lesson_choose_customer, pattern="^lesson_cust_"), MessageHandler(filters.TEXT & ~filters.COMMAND, lesson_amount)], LESSON_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, lesson_note)]},
        fallbacks=[CommandHandler("cancel", cancel)],
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