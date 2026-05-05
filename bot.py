import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import TOKEN, ALLOWED_USERS
from db import init_db
from keyboards import main_menu
from handlers import customers, lessons

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def restricted(update: Update):
    if update.effective_user.id not in ALLOWED_USERS:
        await update.effective_message.reply_text("🚫 Ingen adgang")
        return False
    return True

async def start(update: Update, context):
    if not await restricted(update):
        return
    await update.message.reply_text("DarulQuranBot v3", reply_markup=main_menu())

async def back_main(update: Update, context):
    q = update.callback_query
    await q.answer()
    await q.message.edit_text("Vælg:", reply_markup=main_menu())

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error("Exception while handling update:", exc_info=context.error)

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(back_main, pattern="^back_main$"))

    # Kunder
    app.add_handler(customers.conv_add)
    app.add_handler(CallbackQueryHandler(customers.list_customers, pattern="^list_customers$"))
    app.add_handler(CallbackQueryHandler(customers.show_customer, pattern="^cust_"))
    app.add_handler(CallbackQueryHandler(customers.delete_customer, pattern="^del_"))

    # Lektioner
    app.add_handler(CallbackQueryHandler(lessons.new_lesson_start, pattern="^new_lesson$"))
    app.add_handler(CallbackQueryHandler(lessons.choose_customer, pattern="^lc_"))
    app.add_handler(CallbackQueryHandler(lessons.quick_hour, pattern="^lh_"))
    app.add_handler(CallbackQueryHandler(lessons.month_close, pattern="^month_close$"))

    # NY: log fejl pænt
    app.add_error_handler(error_handler)

    logging.info("Bot v3 kører...")
    app.run_polling()

if __name__ == "__main__":
    main()