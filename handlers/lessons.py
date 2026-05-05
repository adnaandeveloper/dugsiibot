from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler
from db import get_conn
from keyboards import main_menu
from config import ALLOWED_USERS

async def check(u): return u.effective_user.id in ALLOWED_USERS

async def new_lesson_start(update: Update, ctx):
    if not await check(update): return
    q=update.callback_query; await q.answer()
    with get_conn() as conn, cur:=conn.cursor():
        cur.execute("SELECT id,name,hourly_rate,pricing_type FROM customers")
        cs=cur.fetchall()
    kb=[[InlineKeyboardButton(c["name"], callback_data=f"lc_{c['id']}")] for c in cs]
    await q.message.edit_text("Vælg:", reply_markup=InlineKeyboardMarkup(kb))

async def choose_customer(update: Update, ctx):
    q=update.callback_query; await q.answer(); cid=int(q.data.split("_")[1])
    with get_conn() as conn, cur:=conn.cursor():
        cur.execute("SELECT * FROM customers WHERE id=%s",(cid,)); c=cur.fetchone()
    if c["pricing_type"]=="monthly":
        # fast kunde = 1 klik
        with get_conn() as conn, cur:=conn.cursor():
            cur.execute("INSERT INTO lessons(customer_id,amount,hours) VALUES(%s,0,0)",(cid,)); conn.commit()
        await q.message.edit_text("✅ Måned registreret", reply_markup=main_menu()); return
    # time kunde -> vis knapper
    rate=c["hourly_rate"]
    kb=[
        [InlineKeyboardButton(f"0.5t ({int(rate*0.5)}kr)", callback_data=f"lh_{cid}_0.5"),
         InlineKeyboardButton(f"1t ({rate}kr)", callback_data=f"lh_{cid}_1")],
        [InlineKeyboardButton(f"1.5t ({int(rate*1.5)}kr)", callback_data=f"lh_{cid}_1.5"),
         InlineKeyboardButton(f"2t ({rate*2}kr)", callback_data=f"lh_{cid}_2")],
        [InlineKeyboardButton("⬅️", callback_data="new_lesson")]
    ]
    await q.message.edit_text(f"{c['name']} - vælg timer:", reply_markup=InlineKeyboardMarkup(kb))

async def quick_hour(update: Update, ctx):
    q=update.callback_query; await q.answer()
    _,cid,h = q.data.split("_"); cid=int(cid); h=float(h)
    with get_conn() as conn, cur:=conn.cursor():
        cur.execute("SELECT hourly_rate FROM customers WHERE id=%s",(cid,)); rate=cur.fetchone()["hourly_rate"]
        amount=int(h*rate)
        cur.execute("INSERT INTO lessons(customer_id,amount,hours) VALUES(%s,%s,%s)",(cid,amount,h)); conn.commit()
    await q.message.edit_text(f"✅ {h}t = {amount}kr gemt", reply_markup=main_menu())

async def month_close(update: Update, ctx):
    q=update.callback_query; await q.answer()
    with get_conn() as conn, cur:=conn.cursor():
        # automatisk: hver måned regnes for sig pga date_trunc i queries
        cur.execute("SELECT id,name FROM customers WHERE pricing_type='hourly'")
        for c in cur.fetchall():
            cur.execute("UPDATE lessons SET invoiced=true WHERE customer_id=%s AND invoiced=false", (c["id"],))
        conn.commit()
    await q.message.edit_text("✅ Måned afsluttet - ny måned startet", reply_markup=main_menu())

conv_lesson = ConversationHandler(
    entry_points=[CallbackQueryHandler(new_lesson_start, pattern="^new_lesson$")],
    states={},
    fallbacks=[],
    allow_reentry=True
)
# tilføj choose handler
from telegram.ext import Application
# vi registrerer den separat i bot.py, men for enkelthed:
conv_lesson.entry_points.append(CallbackQueryHandler(choose_customer, pattern="^lc_"))