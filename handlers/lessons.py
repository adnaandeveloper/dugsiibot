from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import get_conn
from keyboards import hours_keyboard, back_button

async def new_lesson_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, hourly_rate FROM customers ORDER BY name")
            rows = cur.fetchall()
    btns = [[InlineKeyboardButton(f"{r['name']} ({r['hourly_rate']} kr)", callback_data=f"lc_{r['id']}")] for r in rows]
    btns.append([InlineKeyboardButton("⬅️", callback_data="back_main")])
    await q.message.edit_text("Vælg kunde:", reply_markup=InlineKeyboardMarkup(btns))

async def choose_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split("_")[1])
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT hourly_rate FROM customers WHERE id=%s", (cid,))
            rate = cur.fetchone()['hourly_rate']
    await q.message.edit_text("Vælg timer:", reply_markup=hours_keyboard(cid, rate))

async def quick_hour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    _, cid, hours = q.data.split("_")
    cid = int(cid); hours = float(hours)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT hourly_rate FROM customers WHERE id=%s", (cid,))
            rate = cur.fetchone()['hourly_rate']
            amount = int(rate * hours)
            cur.execute("INSERT INTO lessons (customer_id, hours, amount) VALUES (%s,%s,%s)", (cid, hours, amount))
        conn.commit()
    await q.message.edit_text(f"✅ {hours}t ({amount} kr) registreret", reply_markup=back_button("back_main"))