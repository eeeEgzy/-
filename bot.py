import os
import asyncio
import sqlite3
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BotCommand, BotCommandScopeDefault


TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [697212400]
bot = Bot(token=TOKEN)
dp = Dispatcher()

BUSINESS_TYPES = {
    "🛒 Лоток з овочами": {"price": 1200, "income": 45},
    "🦝 Єнотяче кафе": {"price": 3500, "income": 120},
    "☕ Кав'ярня": {"price": 5000, "income": 150},
    "🛠 СТО": {"price": 25000, "income": 800},
    "⛽ АЗС": {"price": 120000, "income": 4500},
    "🏨 Гранд-Готель": {"price": 500000, "income": 22000}
}
MAX_BIZ_COUNT = 4
BTC_PRICE = 68000



def db_query(query, params=(), fetchone=True, commit=False):
    conn = None
    try:
        conn = sqlite3.connect("economy.db", timeout=15)
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
            return True
        res = cursor.fetchone() if fetchone else cursor.fetchall()
        if fetchone and res is not None and isinstance(res, tuple) and len(res) == 1:
            return res[0]
        return res
    except Exception as e:
        print(f"❌ Помилка БД: {e}")
        return None
    finally:
        if conn: conn.close()


async def check_user(user: types.User):
    db_query("INSERT OR IGNORE INTO users (user_id, username, balance, crypto) VALUES (?, ?, 1000, 0.0)",
             (user.id, user.full_name), commit=True)



@dp.message(Command("статус", "status", prefix="!/"))
async def cmd_status(message: types.Message):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        u_cnt = db_query("SELECT COUNT(*) FROM users")
        b_cnt = db_query("SELECT COUNT(*) FROM business")
        await message.answer(
            f"⚙️ **Статус системи:**\n✅ База: OK\n👥 Гравців: `{u_cnt}`\n🏢 Бізнесів: `{b_cnt}`\n💰 BTC: `{BTC_PRICE}$`",
            parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Помилка: {e}")


@dp.message(Command("дати", prefix="!/"))
async def admin_give(message: types.Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS or not message.reply_to_message: return
    try:
        amt = int(command.args);
        tid = message.reply_to_message.from_user.id
        db_query("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, tid), commit=True)
        await message.answer(f"💰 Нараховано `{amt}$` для {message.reply_to_message.from_user.full_name}")
    except:
        await message.answer("Формат: !дати 1000 (реплаєм)")


@dp.message(Command("дати_біт", prefix="!/"))
async def admin_give_btc(message: types.Message, command: CommandObject):
    if message.from_user.id not in ADMIN_IDS or not message.reply_to_message: return
    try:
        amt = float(command.args.replace(',', '.'));
        tid = message.reply_to_message.from_user.id
        db_query("UPDATE users SET crypto = crypto + ? WHERE user_id = ?", (amt, tid), commit=True)
        await message.answer(f"💎 Нараховано `{amt}` BTC для {message.reply_to_message.from_user.full_name}")
    except:
        await message.answer("Формат: !дати_біт 0.5 (реплаєм)")


@dp.message(Command("забрати", prefix="!/"))
async def admin_take(message: types.Message):
    if message.from_user.id not in ADMIN_IDS or not message.reply_to_message: return
    tid = message.reply_to_message.from_user.id
    db_query("UPDATE users SET balance = 0, crypto = 0.0 WHERE user_id = ?", (tid,), commit=True)
    await message.answer("🚫 Майно гравця анульовано.")



@dp.message(Command("start", "help", prefix="!/"))
async def cmd_start(message: types.Message):
    await check_user(message.from_user)
    await message.answer(
        "🎮 **Економіка активована!**\nКоманди: !профіль, !зп, !бізнес, !апгрейд, !казино, !топ, !біржа")


@dp.message(Command("продати_бізнес", prefix="!/"))
async def cmd_sell_business(message: types.Message):
    uid = message.from_user.id
    await check_user(message.from_user)


    conn = sqlite3.connect("economy.db")
    cursor = conn.cursor()
    cursor.execute("SELECT rowid, biz_name FROM business WHERE user_id = ? ORDER BY rowid DESC LIMIT 1", (uid,))
    res = cursor.fetchone()
    conn.close()

    if not res:
        return await message.answer("❌ У вас немає бізнесів для продажу!")


    db_rowid, biz_name = res

    if biz_name in BUSINESS_TYPES:
        price = BUSINESS_TYPES[biz_name]["price"]
        sell_price = int(price * 0.75)

        # Видаляємо саме цей рядок через rowid
        db_query("DELETE FROM business WHERE rowid = ?", (db_rowid,), commit=True)
        db_query("UPDATE users SET balance = balance + ? WHERE user_id = ?", (sell_price, uid), commit=True)

        await message.answer(
            f"✅ Ви продали **{biz_name}**!\n"
            f"💰 Отримано: `{sell_price}$` (75% від вартості)"
        )
    else:
        await message.answer(f"❌ Помилка: бізнес '{biz_name}' не знайдено в прайсі.")


@dp.message(Command("профіль", "profile", prefix="!/"))
async def cmd_profile(message: types.Message):
    uid = message.from_user.id
    await check_user(message.from_user)
    bal = db_query("SELECT balance FROM users WHERE user_id = ?", (uid,)) or 0
    cry = db_query("SELECT crypto FROM users WHERE user_id = ?", (uid,)) or 0.0
    cnt = db_query("SELECT COUNT(*) FROM business WHERE user_id = ?", (uid,)) or 0
    await message.answer(
        f"👤 **{message.from_user.full_name}**\n💰 Баланс: `{bal}$`\n💎 BTC: `{cry:.4f}`\n🏢 Бізнеси: `{cnt}/{MAX_BIZ_COUNT}`",
        parse_mode="Markdown")


@dp.message(Command("зп", "salary", prefix="!/"))
async def cmd_salary(message: types.Message):
    uid = message.from_user.id
    await check_user(message.from_user)
    last = db_query("SELECT last_work FROM users WHERE user_id = ?", (uid,))
    now = datetime.now()
    if last and now < datetime.strptime(str(last), "%Y-%m-%d %H:%M:%S") + timedelta(hours=1):
        return await message.answer("⏳ ЗП раз на годину!")
    sal = random.randint(500, 1500)
    db_query("UPDATE users SET balance = balance + ?, last_work = ? WHERE user_id = ?",
             (sal, now.strftime("%Y-%m-%d %H:%M:%S"), uid), commit=True)
    await message.answer(f"💵 Отримано `{sal}$`!")


@dp.message(Command("казино", "casino", prefix="!/"))
async def cmd_casino(message: types.Message, command: CommandObject):
    await check_user(message.from_user)
    if not command.args or not command.args.isdigit(): return await message.answer("❌ !казино 100")
    bet = int(command.args);
    bal = db_query("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) or 0
    if bet > bal or bet <= 0: return await message.answer("❌ Мало грошей!")
    if random.random() < 0.45:
        db_query("UPDATE users SET balance = balance + ? WHERE user_id = ?", (bet, message.from_user.id), commit=True)
        await message.answer(f"🎉 Виграш! +`{bet}$`")
    else:
        db_query("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, message.from_user.id), commit=True)
        await message.answer(f"📉 Програш! -`{bet}$`")


@dp.message(Command("топ", "top", prefix="!/"))
async def cmd_top(message: types.Message):
    users = db_query("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10", fetchone=False)
    text = "🏆 **Топ-10 багатіїв:**\n"
    if users:
        for i, (n, b) in enumerate(users, 1): text += f"{i}. {n} — `{b}$`\n"
    await message.answer(text)


@dp.message(Command("біржа", "exchange", prefix="!/"))
async def cmd_exchange(message: types.Message):
    price = BTC_PRICE + random.randint(-2000, 2000)
    await message.answer(f"📈 **Курс BTC:** `{price}$`\nКоманди: `!купити [к-сть]`, `!продати [к-сть]`")


@dp.message(Command("купити", "buy", prefix="!/"))
async def cmd_buy(message: types.Message, command: CommandObject):
    try:
        amt = float(command.args.replace(',', '.'));
        cost = int(amt * BTC_PRICE)
        bal = db_query("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) or 0
        if bal < cost: return await message.answer("❌ Мало грошей!")
        db_query("UPDATE users SET balance = balance - ?, crypto = crypto + ? WHERE user_id = ?",
                 (cost, amt, message.from_user.id), commit=True)
        await message.answer(f"✅ Куплено `{amt}` BTC!")
    except:
        await message.answer("Приклад: !купити 0.1")


@dp.message(Command("продати", "sell", prefix="!/"))
async def cmd_sell(message: types.Message, command: CommandObject):
    try:
        amt = float(command.args.replace(',', '.'));
        cry = db_query("SELECT crypto FROM users WHERE user_id = ?", (message.from_user.id,)) or 0.0
        if cry < amt: return await message.answer("❌ Мало BTC!")
        gain = int(amt * BTC_PRICE)
        db_query("UPDATE users SET balance = balance + ?, crypto = crypto - ? WHERE user_id = ?",
                 (gain, amt, message.from_user.id), commit=True)
        await message.answer(f"✅ Продано `{amt}` BTC!")
    except:
        await message.answer("Приклад: !продати 0.1")


@dp.message(Command("апгрейд", "upgrade", prefix="!/"))
async def cmd_upgrade(message: types.Message):
    bizs = db_query("SELECT biz_name, level FROM business WHERE user_id = ?", (message.from_user.id,), fetchone=False)
    if not bizs: return await message.answer("❌ Немає бізнесів!")
    builder = InlineKeyboardBuilder()
    for name, lvl in bizs:
        pr = int(BUSINESS_TYPES[name]["price"] * 0.5 * lvl)
        builder.button(text=f"🔼 {name} (Lvl {lvl}) | {pr}$", callback_data=f"upg_{name}")
    await message.answer("🛠 **Апгрейд бізнесу:**", reply_markup=builder.adjust(1).as_markup())


@dp.message(Command("бізнес", "business", prefix="!/"))
async def cmd_biz(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="💼 Мої підприємства", callback_data="my_biz")
    builder.button(text="🛒 Магазин", callback_data="biz_shop")
    builder.button(text="💰 Зібрати прибуток", callback_data="collect_money")
    await message.answer("🏗 **Бізнес-меню:**", reply_markup=builder.adjust(1).as_markup())


# --- CALLBACKS ---
@dp.callback_query(F.data == "collect_money")
async def collect_money(callback: types.CallbackQuery):
    uid = callback.from_user.id
    bizs = db_query("SELECT biz_name, level, last_collect FROM business WHERE user_id = ?", (uid,), fetchone=False)
    if not bizs: return await callback.answer("❌ Немає бізнесів!", show_alert=True)
    total = 0;
    now = datetime.now()
    for name, lvl, lt in bizs:
        try:
            hrs = int((now - datetime.strptime(str(lt), "%Y-%m-%d %H:%M:%S")).total_seconds() // 3600)
            if hrs >= 1:
                inc = int(BUSINESS_TYPES[name]["income"] * hrs * (1 + (lvl - 1) * 0.2))
                total += inc
                db_query("UPDATE business SET last_collect=? WHERE user_id=? AND biz_name=?",
                         (now.strftime("%Y-%m-%d %H:%M:%S"), uid, name), commit=True)
        except:
            db_query("UPDATE business SET last_collect=? WHERE user_id=? AND biz_name=?",
                     (now.strftime("%Y-%m-%d %H:%M:%S"), uid, name), commit=True)
    if total > 0:
        db_query("UPDATE users SET balance = balance + ? WHERE user_id = ?", (total, uid), commit=True)
        await callback.message.answer(f"💰 Зібрано: `{total}$`!");
        await callback.answer()
    else:
        await callback.answer("⏳ Ще не минуло години.", show_alert=True)
    await callback.answer()


@dp.callback_query(F.data.startswith("upg_"))
async def upgrade_proc(callback: types.CallbackQuery):
    name = callback.data.replace("upg_", "")
    lvl = db_query("SELECT level FROM business WHERE user_id=? AND biz_name=?", (callback.from_user.id, name)) or 1
    pr = int(BUSINESS_TYPES[name]["price"] * 0.5 * lvl)
    bal = db_query("SELECT balance FROM users WHERE user_id=?", (callback.from_user.id,)) or 0
    if bal >= pr:
        db_query("UPDATE users SET balance=balance-? WHERE user_id=?", (pr, callback.from_user.id), commit=True)
        db_query("UPDATE business SET level=level+1 WHERE user_id=? AND biz_name=?", (callback.from_user.id, name),
                 commit=True)
        await callback.message.edit_text(f"🚀 Покращено {name} до Lvl {lvl + 1}!");
        await callback.answer()
    else:
        await callback.answer("❌ Мало грошей!", show_alert=True)


@dp.callback_query(F.data == "my_biz")
async def my_biz_call(callback: types.CallbackQuery):
    bizs = db_query("SELECT biz_name, level FROM business WHERE user_id=?", (callback.from_user.id,), fetchone=False)
    text = "💼 **Твої бізнеси:**\n" + ("\n".join([f"• {b} (Lvl {l})" for b, l in bizs]) if bizs else "Порожньо.")
    builder = InlineKeyboardBuilder().button(text="⬅️ Назад", callback_data="back_main")
    await callback.message.edit_text(text, reply_markup=builder.as_markup());
    await callback.answer()


@dp.callback_query(F.data == "biz_shop")
async def shop_call(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for n, i in BUSINESS_TYPES.items(): builder.button(text=f"{n} | {i['price']}$", callback_data=f"buy_{n}")
    builder.button(text="⬅️ Назад", callback_data="back_main")
    await callback.message.edit_text("🏪 **Магазин:**", reply_markup=builder.adjust(1).as_markup());
    await callback.answer()


@dp.callback_query(F.data == "back_main")
async def back_call(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder().button(text="💼 Мої підприємства", callback_data="my_biz").button(text="🛒 Магазин",
                                                                                                       callback_data="biz_shop").button(
        text="💰 Зібрати прибуток", callback_data="collect_money")
    await callback.message.edit_text("🏗 **Меню:**", reply_markup=builder.adjust(1).as_markup());
    await callback.answer()


@dp.callback_query(F.data.startswith("buy_"))
async def buy_proc(callback: types.CallbackQuery):
    uid, name = callback.from_user.id, callback.data.replace("buy_", "")
    cnt = db_query("SELECT COUNT(*) FROM business WHERE user_id=?", (uid,)) or 0
    if cnt >= MAX_BIZ_COUNT: return await callback.answer("❌ Ліміт 4 бізнеси!", show_alert=True)
    pr = BUSINESS_TYPES[name]["price"]
    bal = db_query("SELECT balance FROM users WHERE user_id=?", (uid,)) or 0
    if bal >= pr:
        db_query("UPDATE users SET balance=balance-? WHERE user_id=?", (pr, uid), commit=True)
        db_query("INSERT INTO business (user_id, biz_name, level, last_collect) VALUES (?, ?, 1, ?)",
                 (uid, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")), commit=True)
        await callback.message.edit_text(f"🎉 Куплено: {name}!");
        await callback.answer()
    else:
        await callback.answer("❌ Мало грошей!", show_alert=True)


# --- ОСНОВНА ФУНКЦІЯ ---
async def main():
    conn = sqlite3.connect("economy.db")
    c = conn.cursor()
    c.execute(
        'CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 1000, crypto REAL DEFAULT 0, last_work TEXT, last_rob TEXT)')
    c.execute(
        'CREATE TABLE IF NOT EXISTS business (user_id INTEGER, biz_name TEXT, level INTEGER DEFAULT 1, last_collect TEXT)')
    conn.commit();
    conn.close()

    await bot.set_my_commands([
        BotCommand(command="start", description="🚀 Меню"), BotCommand(command="profile", description="👤 Профіль"),
        BotCommand(command="salary", description="💵 ЗП"), BotCommand(command="business", description="🏗 Бізнес"),
        BotCommand(command="upgrade", description="🛠 Апгрейд"), BotCommand(command="casino", description="🎰 Казино"),
        BotCommand(command="top", description="🏆 Топ"), BotCommand(command="exchange", description="📈 Біржа"),
        BotCommand(command="status", description="⚙️ Статус")
    ], scope=BotCommandScopeDefault())

    print("🚀 Бот запущений!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

