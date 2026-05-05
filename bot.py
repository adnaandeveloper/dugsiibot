from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tilføj kunde", callback_data="add_customer")],
        [InlineKeyboardButton("📋 Mine kunder", callback_data="list_customers")],
        [InlineKeyboardButton("📝 Ny lektion", callback_data="new_lesson")],
        [InlineKeyboardButton("📅 Månedsafslutning", callback_data="month_close")],
    ])

def back_button(target="back_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Tilbage", callback_data=target)]])

def hours_keyboard(customer_id: int, rate: int):
    """Bruges når du vælger en time-kunde – 1 klik = gemt"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"0.5t ({int(rate*0.5)} kr)", callback_data=f"lh_{customer_id}_0.5"),
            InlineKeyboardButton(f"1t ({rate} kr)", callback_data=f"lh_{customer_id}_1")
        ],
        [
            InlineKeyboardButton(f"1.5t ({int(rate*1.5)} kr)", callback_data=f"lh_{customer_id}_1.5"),
            InlineKeyboardButton(f"2t ({rate*2} kr)", callback_data=f"lh_{customer_id}_2")
        ],
        [InlineKeyboardButton("⬅️", callback_data="new_lesson")]
    ])

def customer_detail_keyboard(customer_id: int):
    """Bruges på 'Mine kunder' detaljeside"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Rediger pris", callback_data=f"edit_{customer_id}"),
         InlineKeyboardButton("💰 Marker betalt", callback_data=f"pay_{customer_id}")],
        [InlineKeyboardButton("🗑 Slet kunde", callback_data=f"del_{customer_id}")],
        [InlineKeyboardButton("⬅️ Tilbage", callback_data="list_customers")]
    ])

def confirm_delete_keyboard(customer_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ja, slet", callback_data=f"del_yes_{customer_id}"),
         InlineKeyboardButton("❌ Annuller", callback_data=f"cust_{customer_id}")]
    ])