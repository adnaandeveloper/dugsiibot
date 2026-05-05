from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import datetime

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Tilføj kunde", callback_data="add_customer")],
        [InlineKeyboardButton("📋 Mine kunder", callback_data="list_customers")],
        [InlineKeyboardButton("📝 Ny lektion", callback_data="new_lesson")],
        [InlineKeyboardButton("📊 Status denne måned", callback_data="status_month")],
        [InlineKeyboardButton("🏫 Klasser", callback_data="classes_main")],
        [InlineKeyboardButton("🔄 Nulstil ALLE saldi", callback_data="reset_all")],
    ])

def back_button(target="back_main"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Tilbage", callback_data=target)]
    ])

def hours_keyboard(customer_id: int, rate: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"0.5t ({int(rate*0.5)} kr)", callback_data=f"lh_{customer_id}_0.5"),
         InlineKeyboardButton(f"1t ({rate} kr)", callback_data=f"lh_{customer_id}_1")],
        [InlineKeyboardButton(f"1.5t ({int(rate*1.5)} kr)", callback_data=f"lh_{customer_id}_1.5"),
         InlineKeyboardButton(f"2t ({rate*2} kr)", callback_data=f"lh_{customer_id}_2")],
        [InlineKeyboardButton("⬅️", callback_data="new_lesson")]
    ])

def customer_detail_keyboard(customer_id: int, months):
    btns = []
    for ym, net in months:
        dt = datetime.datetime.strptime(ym, "%Y-%m")
        navn = dt.strftime("%b %Y")
        btns.append([InlineKeyboardButton(f"{navn}: {net} kr", callback_data=f"month_{customer_id}_{ym}")])
    btns.append([
        InlineKeyboardButton("✏️ Rediger pris", callback_data=f"edit_{customer_id}"),
        InlineKeyboardButton("🔄 Nulstil saldo", callback_data=f"reset_{customer_id}")
    ])
    btns.append([InlineKeyboardButton("🗑 Slet kunde", callback_data=f"del_{customer_id}")])
    btns.append([InlineKeyboardButton("⬅️ Tilbage", callback_data="list_customers")])
    return InlineKeyboardMarkup(btns)

def month_detail_keyboard(customer_id: int, ym: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Betal fuldt", callback_data=f"payfull_{customer_id}_{ym}"),
         InlineKeyboardButton("✏️ Delbetaling", callback_data=f"paypart_{customer_id}_{ym}")],
        [InlineKeyboardButton("🏷 Rabat", callback_data=f"rabat_{customer_id}_{ym}")],
        [InlineKeyboardButton("⬅️ Tilbage", callback_data=f"cust_{customer_id}")]
    ])

def betalingsmetode_keyboard(action, cid, ym, belob=0):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 Kontant", callback_data=f"met_{action}_{cid}_{ym}_{belob}_kontant"),
         InlineKeyboardButton("🏦 Bank", callback_data=f"met_{action}_{cid}_{ym}_{belob}_bank")],
        [InlineKeyboardButton("⬅️", callback_data=f"month_{cid}_{ym}")]
    ])

def classes_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Ny klasse", callback_data="add_class")],
        [InlineKeyboardButton("📚 Mine klasser", callback_data="list_classes")],
        [InlineKeyboardButton("⬅️", callback_data="back_main")]
    ])

def class_list_keyboard(classes):
    btns = []
    for c in classes:
        btns.append([InlineKeyboardButton(f"{c['name']} ({c['monthly_price']} kr)", callback_data=f"class_{c['id']}")])
    btns.append([InlineKeyboardButton("⬅️", callback_data="classes_main")])
    return InlineKeyboardMarkup(btns)

def class_detail_keyboard(cid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Tilføj elev", callback_data=f"add_student_{cid}")],
        [InlineKeyboardButton("✅ Kryds af betalt", callback_data=f"pay_class_{cid}")],
        [InlineKeyboardButton("📊 Se manglende", callback_data=f"missing_{cid}")],
        [InlineKeyboardButton("🗑 Slet klasse", callback_data=f"del_class_{cid}")],
        [InlineKeyboardButton("⬅️", callback_data="list_classes")]
    ])