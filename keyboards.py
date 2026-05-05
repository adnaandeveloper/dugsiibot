from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tilføj kunde", callback_data="add_customer")],
        [InlineKeyboardButton("📋 Mine kunder", callback_data="list_customers")],
        [InlineKeyboardButton("📝 Ny lektion", callback_data="new_lesson")],
        [InlineKeyboardButton("📅 Månedsafslutning", callback_data="month_close")],
    ])

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Tilbage", callback_data="back_main")]])