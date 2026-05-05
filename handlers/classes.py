from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from db import get_conn
from keyboards import back_button, classes_menu, class_list_keyboard, class_detail_keyboard
import datetime

ADD_CLASS_NAME, ADD_CLASS_PRICE, ADD_STUDENT_NAME = range(3)

async def classes_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.message.edit_text("Klasser:", reply_markup=classes_menu())

async def list_classes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, monthly_price FROM classes ORDER BY name")
            classes = cur.fetchall()
    await q.message.edit_text("Vælg klasse:", reply_markup=class_list_keyboard(classes))

async def show_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split("_")[1])
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, monthly_price FROM classes WHERE id=%s", (cid,))
            c = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM class_students WHERE class_id=%s", (cid,))
            antal = cur.fetchone()['count']
    await q.message.edit_text(f"{c['name']}\nPris: {c['monthly_price']} kr/md\nElever: {antal}", reply_markup=class_detail_keyboard(cid))

async def add_class_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.message.edit_text("Navn på klasse:"); return ADD_CLASS_NAME

async def add_class_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['classname'] = update.message.text
    await update.message.reply_text("Månedspris i kr:"); return ADD_CLASS_PRICE

async def add_class_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: price = int(update.message.text)
    except: await update.message.reply_text("Kun tal"); return ADD_CLASS_PRICE
    name = context.user_data['classname']
    with get_conn() as conn:
        with conn.cursor() as cur: cur.execute("INSERT INTO classes (name, monthly_price) VALUES (%s,%s)", (name, price))
        conn.commit()
    await update.message.reply_text(f"{name} oprettet", reply_markup=classes_menu())
    return ConversationHandler.END

conv_add_class = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_class_start, pattern="^add_class$")],
    states={ADD_CLASS_NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, add_class_name)],
            ADD_CLASS_PRICE:[MessageHandler(filters.TEXT & ~filters.COMMAND, add_class_price)]},
    fallbacks=[], per_message=False
)

async def add_student_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split("_")[2])
    context.user_data['cid'] = cid
    await q.message.edit_text("Navn på elev:"); return ADD_STUDENT_NAME

async def add_student_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text; cid = context.user_data['cid']
    with get_conn() as conn:
        with conn.cursor() as cur: cur.execute("INSERT INTO class_students (class_id, name) VALUES (%s,%s)", (cid, name))
        conn.commit()
    await update.message.reply_text(f"{name} tilføjet", reply_markup=class_detail_keyboard(cid))
    return ConversationHandler.END

conv_add_student = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_student_start, pattern="^add_student_")],
    states={ADD_STUDENT_NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, add_student_save)]},
    fallbacks=[], per_message=False
)

async def pay_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split("_")[2])
    ym = datetime.datetime.now().strftime("%Y-%m")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM class_students WHERE class_id=%s ORDER BY name", (cid,))
            students = cur.fetchall()
    btns = [[InlineKeyboardButton(s['name'], callback_data=f"paystu_{cid}_{s['id']}_{ym}")] for s in students]
    btns.append([InlineKeyboardButton("⬅️", callback_data=f"class_{cid}")])
    await q.message.edit_text(f"Kryds af for {ym}:", reply_markup=InlineKeyboardMarkup(btns))

async def pay_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    _, cid, sid, ym = q.data.split("_")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT monthly_price FROM classes WHERE id=%s", (cid,))
            price = cur.fetchone()['monthly_price']
            cur.execute("INSERT INTO class_payments (student_id, class_id, amount, month_ym, method) VALUES (%s,%s,%s,%s,'kontant') ON CONFLICT DO NOTHING", (sid, cid, price, ym))
        conn.commit()
    await q.answer("✅ Betalt", show_alert=True)

async def missing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split("_")[1])
    ym = datetime.datetime.now().strftime("%Y-%m")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT s.name FROM class_students s LEFT JOIN class_payments p ON s.id=p.student_id AND p.month_ym=%s WHERE s.class_id=%s AND p.id IS NULL", (ym, cid))
            missing = [r['name'] for r in cur.fetchall()]
    text = "Mangler at betale:\n" + "\n".join(missing) if missing else "Alle har betalt ✅"
    await q.message.edit_text(text, reply_markup=class_detail_keyboard(cid))

async def del_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    cid = int(q.data.split("_")[2])
    with get_conn() as conn:
        with conn.cursor() as cur: cur.execute("DELETE FROM classes WHERE id=%s", (cid,))
        conn.commit()
    await q.message.edit_text("Klasse slettet", reply_markup=classes_menu())