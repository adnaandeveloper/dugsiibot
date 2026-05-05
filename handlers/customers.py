from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from db import get_conn
from keyboards import back_button, main_menu, customer_detail_keyboard
from config import ALLOWED_USERS

ADD_NAME, ADD_PHONE, ADD_TYPE, ADD_RATE = range(4)

async def check(u):
    return u.effective_user.id in ALLOWED_USERS

async def add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check(update):
        await update.callback_query.answer("Ingen adgang", show_alert=True)
        return ConversationHandler.END
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Navn?", reply_markup=back_button())
    return ADD_NAME

async def add_name(u, c):
    c.user_data["n"] = u.message.text
    await u.message.reply_text("Telefon?")
    return ADD_PHONE

async def add_phone(u, c):
    c.user_data["p"] = u.message.text
    kb = [[InlineKeyboardButton("Time", callback_data="t_h"),
           InlineKeyboardButton("Fast", callback_data="t_m")]]
    await u.message.reply_text("Type?", reply_markup=InlineKeyboardMarkup(kb))
    return ADD_TYPE

async def add_type(u, c):
    await u.callback_query.answer()
    c.user_data["t"] = "hourly" if "h" in u.callback_query.data else "monthly"
    await u.callback_query.message.reply_text("Pris i kr?")
    return ADD_RATE

async def add_rate(u, c):
    try:
        rate = int(u.message.text)
    except:
        await u.message.reply_text("Skriv kun tal")
        return ADD_RATE

    t = c.user_data["t"]
    h = rate if t == "hourly" else 0
    m = rate if t == "monthly" else 0

    with get_conn() as conn:
        with conn.cursor() as cur:
            # FIX: 5 værdier = 5 %s
            cur.execute(
                "INSERT INTO customers(name, phone, pricing_type, hourly_rate, monthly_price) VALUES(%s,%s,%s)",
                (c.user_data["n"], c.user_data["p"], t, h, m)
            )
        conn.commit()

    await u.message.reply_text("✅ Oprettet", reply_markup=main_menu())
    return ConversationHandler.END

conv_add = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_start, pattern="^add_customer$")],
    states={
        ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
        ADD_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_phone)],
        ADD_TYPE: [CallbackQueryHandler(add_type, pattern="^t_")],
        ADD_RATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_rate)]
    },
    fallbacks=[],
    allow_reentry=True
)

async def list_customers(update: Update, ctx):
    if not await check(update): return
    q = update.callback_query
    await q.answer()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM customers ORDER BY name")
            rows = cur.fetchall()

    kb = [[InlineKeyboardButton(r["name"], callback_data=f"cust_{r['id']}")] for r in rows]
    kb.append([InlineKeyboardButton("⬅️", callback_data="back_main")])
    await q.message.edit_text("Vælg kunde:", reply_markup=InlineKeyboardMarkup(kb))

async def show_customer(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    cid = int(q.data.split("_")[1])

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM customers WHERE id=%s", (cid,))
            c = cur.fetchone()

            cur.execute("""SELECT COALESCE(SUM(amount),0) as betalt FROM payments
                           WHERE customer_id=%s AND status='betalt'
                           AND date_trunc('month', paid_at)=date_trunc('month', now())""", (cid,))
            betalt = cur.fetchone()["betalt"]

            cur.execute("""SELECT COALESCE(SUM(amount),0) as skyld FROM lessons
                           WHERE customer_id=%s AND invoiced=false
                           AND date_trunc('month', created_at)=date_trunc('month', now())""", (cid,))
            skyld = cur.fetchone()["skyld"]

    text = f"*{c['name']}*\nType: {c['pricing_type']}\nDenne måned betalt: {betalt} kr\nUafsluttet: {skyld} kr"

    await q.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=customer_detail_keyboard(cid) # bruger den nye keyboard
    )

async def delete_customer(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    cid = int(q.data.split("_")[1])

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM customers WHERE id=%s", (cid,))
        conn.commit()

    await q.message.edit_text("Slettet", reply_markup=main_menu())