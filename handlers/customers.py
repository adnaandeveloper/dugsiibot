#... behold imports og conv_add øverst...

async def show_customer(update: Update, context):
    q = update.callback_query
    await q.answer()
    cid = int(q.data.split("_")[1])
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, pricing_type FROM customers WHERE id=%s", (cid,))
            c = cur.fetchone()
            # samlet saldo
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM lessons WHERE customer_id=%s", (cid,))
            charged = cur.fetchone()['coalesce'] or 0
            cur.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE customer_id=%s", (cid,))
            paid = cur.fetchone()['coalesce'] or 0
            saldo = charged - paid
            # måneder med aktivitet
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

async def month_detail(update: Update, context):
    q = update.callback_query
    await q.answer()
    _, cid, ym = q.data.split("_")
    cid = int(cid)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT SUM(amount) FROM lessons WHERE customer_id=%s AND to_char(created_at,'YYYY-MM')=%s", (cid, ym))
            charged = cur.fetchone()['sum'] or 0
            cur.execute("SELECT SUM(amount) FROM payments WHERE customer_id=%s AND to_char(paid_at,'YYYY-MM')=%s", (cid, ym))
            paid = cur.fetchone()['sum'] or 0
            rest = charged - paid
    await q.message.edit_text(f"Måned {ym}\nFaktureret: {int(charged)} kr\nBetalt: {int(paid)} kr\nRest: {int(rest)} kr",
                              reply_markup=month_detail_keyboard(cid, ym))

async def pay_full(update: Update, context):
    q = update.callback_query
    await q.answer()
    _, cid, ym = q.data.split("_")
    cid = int(cid)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT SUM(amount) FROM lessons WHERE customer_id=%s AND to_char(created_at,'YYYY-MM')=%s", (cid, ym))
            charged = cur.fetchone()['sum'] or 0
            cur.execute("SELECT SUM(amount) FROM payments WHERE customer_id=%s AND to_char(paid_at,'YYYY-MM')=%s", (cid, ym))
            paid = cur.fetchone()['sum'] or 0
            rest = charged - paid
            if rest > 0:
                cur.execute("INSERT INTO payments (customer_id, amount, paid_at) VALUES (%s,%s,%s)",
                            (cid, rest, f"{ym}-28"))
        conn.commit()
    await q.message.edit_text(f"✅ {int(rest)} kr registreret for {ym}", reply_markup=month_detail_keyboard(cid, ym))

# delbetaling og rabat – simpel version
async def pay_part_start(update: Update, context):
    q = update.callback_query
    await q.answer()
    _, cid, ym = q.data.split("_")
    context.user_data["pay"] = {"cid": int(cid), "ym": ym}
    await q.message.edit_text("Skriv beløb der er betalt:")

async def pay_part_save(update: Update, context):
    data = context.user_data.get("pay")
    if not data: return
    try: belob = int(update.message.text)
    except: return await update.message.reply_text("Kun tal")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO payments (customer_id, amount, paid_at) VALUES (%s,%s,%s)",
                        (data["cid"], belob, f"{data['ym']}-28"))
        conn.commit()
    await update.message.reply_text(f"{belob} kr registreret", reply_markup=month_detail_keyboard(data["cid"], data["ym"]))