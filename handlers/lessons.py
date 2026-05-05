from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import get_conn
from keyboards import main_menu, hours_keyboard
from config import ALLOWED_USERS

async def check(u):
    return u.effective_user.id in ALLOWED_USERS

async def new_lesson_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check(update):
        return
    q = update.callback_query
    await q.answer()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM customers ORDER BY name")
            cs = cur.fetchall()

    kb = [[InlineKeyboardButton(c["name"], callback_data=f"lc_{c['id']}")] for c in cs]
    kb.append([InlineKeyboardButton("⬅️", callback_data="back_main")])
    await q.message.edit_text("Vælg kunde:", reply_markup=InlineKeyboardMarkup(kb))

async def choose_customer(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    cid = int(q.data.split("_")[1])

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM customers WHERE id=%s", (cid,))
            c = cur.fetchone()

    if c["pricing_type"] == "monthly":
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO lessons(customer_id, amount, hours) VALUES (%s, 0, 0)", (cid,))
            conn.commit()
        await q.message.edit_text("✅ Måned registreret", reply_markup=main_menu())
        return

    # time-kunde – brug den nye keyboard
    await q.message.edit_text(
        f"{c['name']} – vælg timer:",
        reply_markup=hours_keyboard(cid, c["hourly_rate"])
    )

async def quick_hour(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    _, cid, h = q.data.split("_")
    cid, h = int(cid), float(h)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT hourly_rate FROM customers WHERE id=%s", (cid,))
            rate = cur.fetchone()["hourly_rate"]
            amount = int(h * rate)
            cur.execute(
                "INSERT INTO lessons(customer_id, amount, hours) VALUES (%s, %s, %s)",
                (cid, amount, h)
            )
        conn.commit()

    await q.message.edit_text(f"✅ {h}t = {amount}kr gemt", reply_markup=main_menu())

async def month_close(update: Update, ctx):
    q = update.callback_query
    await q.answer()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE lessons SET invoiced=true WHERE invoiced=false")
        conn.commit()
    await q.message.edit_text("✅ Måned afsluttet", reply_markup=main_menu())