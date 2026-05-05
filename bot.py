import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

from config import TOKEN, ALLOWED_USERS
from db import init_db
from keyboards import main_menu
from handlers import customers, lessons, classes

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

async def restricted(update: Update):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.effective_message.reply_text("🚫 Ingen adgang")
        return False
    return True

async def start(update: Update, context):
    if not await restricted(update): return
    await update.message.reply_text("DarulQuranBot v3", reply_markup=main_menu())

async def back_main(update: Update, context):
    q = update.callback_query; await q.answer()
    await q.message.edit_text("Vælg:", reply_markup=main_menu())

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))

    # kunder
    app.add_handler(customers.conv_add)
    app.add_handler(CallbackQueryHandler(customers.list_customers, pattern="^list_customers$"))
    app.add_handler(CallbackQueryHandler(customers.show_customer, pattern="^cust_"))
    app.add_handler(CallbackQueryHandler(customers.delete_customer, pattern="^del_"))
    app.add_handler(CallbackQueryHandler(customers.reset_customer, pattern="^reset_\\d+$"))
    app.add_handler(CallbackQueryHandler(customers.reset_all, pattern="^reset_all$"))
    app.add_handler(CallbackQueryHandler(customers.status_month, pattern="^status_month$"))
    app.add_handler(CallbackQueryHandler(customers.month_detail, pattern="^month_"))
    app.add_handler(CallbackQueryHandler(customers.pay_full, pattern="^payfull_"))
    app.add_handler(CallbackQueryHandler(customers.pay_part_start, pattern="^paypart_"))
    app.add_handler(CallbackQueryHandler(customers.save_payment_method, pattern="^met_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, customers.pay_part_save))

    # lektioner
    app.add_handler(CallbackQueryHandler(lessons.new_lesson_start, pattern="^new_lesson$"))
    app.add_handler(CallbackQueryHandler(lessons.choose_customer, pattern="^lc_"))
    app.add_handler(CallbackQueryHandler(lessons.quick_hour, pattern="^lh_"))

    # klasser
    app.add_handler(CallbackQueryHandler(classes.classes_main, pattern="^classes_main$"))
    app.add_handler(CallbackQueryHandler(classes.list_classes, pattern="^list_classes$"))
    app.add_handler(CallbackQueryHandler(classes.show_class, pattern="^class_\\d+$"))
    app.add_handler(CallbackQueryHandler(classes.pay_class, pattern="^pay_class_"))
    app.add_handler(CallbackQueryHandler(classes.pay_student, pattern="^paystu_"))
    app.add_handler(CallbackQueryHandler(classes.missing, pattern="^missing_"))
    app.add_handler(CallbackQueryHandler(classes.del_class, pattern="^del_class_"))
    app.add_handler(classes.conv_add_class)
    app.add_handler(classes.conv_add_student)

    logging.info("Bot v3 kører...")
    app.run_polling()

if __name__ == "__main__":
    main()