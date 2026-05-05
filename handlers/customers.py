from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from db import get_conn
from keyboards import back_button, customer_detail_keyboard, month_detail_keyboard
import datetime

ADD_NAME, ADD_PRICE = range(2)

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.edit_text("Navn på kunde:")
    return ADD_NAME

async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Timepris i kr:")
    return ADD_PRICE

async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text)
    except:
        await update.message.reply_text("Kun tal")
        return ADD_PRICE
    name = context.user_data["name"]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO customers (name, hourly_rate, pricing_type) VALUES (%s,%s,'hourly')", (name, price))
        conn.commit()
    await update.message.reply_text(f"{name} tilføjet", reply_markup=back_button("list_customers"))
    return ConversationHandler.END

conv_add = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_start, pattern="^add_customer$")],
    states={
        ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
        ADD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_price)],
    },
    fallbacks=[],
    per_message=False
)

async def list_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM customers ORDER BY name")
            rows = cur.fetchall()
    btns = [[InlineKeyboardButton(r['name'], callback_data=f"cust_{r['id']}")] for r in rows]
    btns.append([InlineKeyboardButton("⬅️", callback_data="back_main")])
    await q.message.edit_text("Vælg kunde:", reply_markup=InlineKeyboardMarkup(btns))

async def show_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cid = int(q.data.split("_")[1])
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, pricing_type FROM customers WHERE id=%s", (cid,))
            c = cur.fetchone()
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM lessons WHERE customer_id=%s", (cid,))
            charged = cur.fetchone()['coalesce'] or 0
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE customer_id=%s", (cid,))
            paid = cur.fetchone()['coalesce'] or 0
            saldo = charged - paid
            cur.execute("""
                SELECT to_char(date_trunc('month', created_at),'YYYY-MM') ym,
                       SUM(amount) as charged
                FROM lessons WHERE customer_id=%s
                GROUP BY ym ORDER BY ym DESC LIMIT 12
            """, (cid,))
            months_raw = cur.fetchall()
            months = []
            for r in months_raw:
                ym = r['ym']
                cur.execute("SELECT COALESCE(SUM(amount),0) as paid FROM payments WHERE customer_id=%s AND to_char(paid_at,'YYYY-MM')=%s", (cid, ym))
                paid_m = cur.fetchone()['paid']
                net = r['charged'] - paid_m
                months.append((ym, int(net)))
    text = f"{c['name']}\nType: {c['pricing_type']}\nSamlet saldo: {saldo} kr\n\nVælg måned:"
    await q.message.edit_text(text, reply_markup=customer_detail_keyboard(cid, months))

async def month_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, cid, ym = q.data.split("_")
    cid = int(cid)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM lessons WHERE customer_id=%s AND to_char(created_at,'YYYY-MM')=%s", (cid, ym))
            charged = cur.fetchone()['coalesce']
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE customer_id=%s AND to_char(paid_at,'YYYY-MM')=%s", (cid, ym))
            paid = cur.fetchone()['coalesce']
            rest = charged - paid
    await q.message.edit_text(f"Måned {ym}\nFaktureret: {int(charged)} kr\nBetalt: {int(paid)} kr\nRest: {int(rest)} kr",
                              reply_markup=month_detail_keyboard(cid, ym))

async def pay_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, cid, ym = q.data.split("_")
    cid = int(cid)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM lessons WHERE customer_id=%s AND to_char(created_at,'YYYY-MM')=%s", (cid, ym))
            charged = cur.fetchone()['coalesce']
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE customer_id=%s AND to_char(paid_at,'YYYY-MM')=%s", (cid, ym))
            paid = cur.fetchone()['coalesce']
            rest = charged - paid
            if rest > 0:
                cur.execute("INSERT INTO payments (customer_id, amount, paid_at) VALUES (%s,%s,%s)", (cid, rest, f"{ym}-28"))
        conn.commit()
    await q.message.edit_text(f"✅ {int(rest)} kr registreret for {ym}", reply_markup=month_detail_keyboard(cid, ym))

async def pay_part_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, cid, ym = q.data.split("_")
    context.user_data["pay"] = {"cid": int(cid), "ym": ym}
    await q.message.edit_text("Skriv beløb der er betalt:")

async def pay_part_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data.get("pay")
    if not data:
        return
    try:
        belob = int(update.message.text)
    except:
        await update.message.reply_text("Kun tal")
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO payments (customer_id, amount, paid_at) VALUES (%s,%s,%s)",
                        (data["cid"], belob, f"{data['ym']}-28"))
        conn.commit()
    await update.message.reply_text(f"{belob} kr registreret", reply_markup=month_detail_keyboard(data["cid"], data["ym"]))

async def delete_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cid = int(q.data.split("_")[1])
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM customers WHERE id=%s", (cid,))
        conn.commit()
    await q.message.edit_text("Slettet", reply_markup=back_button("list_customers"))

async def reset_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cid = int(q.data.split("_")[1])
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM lessons WHERE customer_id=%s", (cid,))
            charged = cur.fetchone()['coalesce']
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE customer_id=%s", (cid,))
            paid = cur.fetchone()['coalesce']
            saldo = charged - paid
            if saldo!= 0:
                cur.execute("INSERT INTO payments (customer_id, amount, paid_at) VALUES (%s,%s,now())", (cid, saldo))
        conn.commit()
    await q.message.edit_text(f"✅ Saldo nulstillet ({int(saldo)} kr udlignet)", reply_markup=back_button(f"cust_{cid}"))

async def reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Nulstiller...")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM customers")
            for cust in cur.fetchall():
                cid = cust['id']
                cur.execute("SELECT COALESCE(SUM(amount),0) FROM lessons WHERE customer_id=%s", (cid,))
                charged = cur.fetchone()['coalesce']
                cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE customer_id=%s", (cid,))
                paid = cur.fetchone()['coalesce']
                saldo = charged - paid
                if saldo!= 0:
                    cur.execute("INSERT INTO payments (customer_id, amount, paid_at) VALUES (%s,%s,now())", (cid, saldo))
        conn.commit()
    await q.message.edit_text("✅ Alle saldi nulstillet", reply_markup=back_button("back_main"))