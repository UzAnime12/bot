import asyncio
import os
import psycopg2
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ================== SOZLAMALAR ==================
TOKEN = "8429768199:AAESgat9RxGc_vaHC9lEm1gyrO2_1qlmhb4"
SUPER_ADMIN = 8348353169  # Asadbek sizning ID
CHANNEL_ID = -1002972635022  # Oxirgi rasmdagi kanal ID
BOT_USERNAME = "UzAnimeHub_bot"
IMAGE_DIR = "images"

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "Yelaykisi",
    "host": "localhost",
    "port": 5432
}

os.makedirs(IMAGE_DIR, exist_ok=True)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ================== STATES ==================
class AnimeAdd(StatesGroup):
    photo = State()
    video = State()
    name = State()
    genre = State()
    year = State()


class AdminManage(StatesGroup):
    add_admin = State()


# ================== DATABASE ==================
def init_db():
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                            CREATE TABLE IF NOT EXISTS animes
                            (
                                id
                                SERIAL
                                PRIMARY
                                KEY,
                                name
                                TEXT,
                                genre
                                TEXT,
                                year
                                TEXT,
                                image_path
                                TEXT,
                                video_id
                                TEXT
                            );
                            """)
                cur.execute("""
                            CREATE TABLE IF NOT EXISTS bot_admins
                            (
                                user_id
                                BIGINT
                                PRIMARY
                                KEY
                            );
                            """)
                cur.execute("INSERT INTO bot_admins (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (SUPER_ADMIN,))
                conn.commit()
    except Exception as e:
        print(f"Baza xatosi: {e}")


def is_admin(user_id):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM bot_admins WHERE user_id = %s", (user_id,))
                return cur.fetchone() is not None
    except:
        return False


# ================== HANDLERLAR ==================

@dp.message(Command("start"))
async def start(message: types.Message, command: CommandObject):
    args = command.args
    if args:
        try:
            with psycopg2.connect(**DB_CONFIG) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT name, video_id FROM animes WHERE id = %s", (args,))
                    anime = cur.fetchone()
                    if anime:
                        await message.answer_video(video=anime[1], caption=f"🎬 {anime[0]}")
        except:
            await message.answer("❌ Xato yuz berdi.")
    else:
        await message.answer(f"👋 Salom {message.from_user.first_name}!")


@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id): return

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="➕ Admin Qo'shish", callback_data="admin_add"))
    builder.row(types.InlineKeyboardButton(text="➖ Admin Bo'shatish", callback_data="admin_list_del"))
    builder.row(types.InlineKeyboardButton(text="📋 Adminlar Ro'yxati", callback_data="admin_show"))
    builder.row(types.InlineKeyboardButton(text="🎬 Anime Qo'shish", callback_data="anime_add_start"))

    await message.answer("🛠 **Admin Boshqaruv Paneli**", reply_markup=builder.as_markup())


# --- ADMIN QO'SHISH (XATOLAR TO'G'IRLANDI) ---
@dp.callback_query(F.data == "admin_add")
async def ask_admin_id(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != SUPER_ADMIN:
        await callback.answer("Faqat asosiy admin qo'sha oladi!", show_alert=True)
        return
    await callback.message.answer("🆕 Yangi adminning ID raqamini yozing:")
    await state.set_state(AdminManage.add_admin)


@dp.message(AdminManage.add_admin)
async def save_admin(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam yozing!")
        return

    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO bot_admins (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (int(message.text),))
                conn.commit()
        await message.answer(f"✅ ID: {message.text} admin etib tayinlandi!")
    except:
        await message.answer("❌ Xato!")
    await state.clear()


# --- ADMINLARNI KO'RISH (XATOLAR TO'G'IRLANDI) ---
@dp.callback_query(F.data == "admin_show")
async def show_admins(callback: types.CallbackQuery):
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_id FROM bot_admins")
                admins = cur.fetchall()
                text = "📋 **Adminlar ro'yxati:**\n\n"
                for a in admins: text += f"• `{a[0]}`\n"
                await callback.message.answer(text, parse_mode="Markdown")
    except:
        await callback.answer("Xato!")


@dp.callback_query(F.data == "admin_list_del")
async def list_admins_del(callback: types.CallbackQuery):
    if callback.from_user.id != SUPER_ADMIN:
        await callback.answer("Faqat asosiy admin o'chira oladi!", show_alert=True)
        return

    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM bot_admins WHERE user_id != %s", (SUPER_ADMIN,))
            admins = cur.fetchall()
            builder = InlineKeyboardBuilder()
            for a in admins:
                builder.row(types.InlineKeyboardButton(text=f"❌ {a[0]}", callback_data=f"del_{a[0]}"))
            await callback.message.answer("Qaysi adminni bo'shatasiz?", reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("del_"))
async def delete_admin(callback: types.CallbackQuery):
    admin_id = int(callback.data.split("_")[1])
    with psycopg2.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM bot_admins WHERE user_id = %s", (admin_id,))
            conn.commit()
    await callback.message.edit_text(f"🗑 ID: {admin_id} adminlikdan bo'shatildi!")


# --- ANIME QO'SHISH (XATOLAR TO'G'IRLANDI) ---
@dp.callback_query(F.data == "anime_add_start")
async def anime_start(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("🖼 Anime rasmini yuboring:")
    await state.set_state(AnimeAdd.photo)


@dp.message(AnimeAdd.photo, F.photo)
async def get_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    path = f"{IMAGE_DIR}/{photo.file_unique_id}.jpg"
    await bot.download_file(file.file_path, path)
    await state.update_data(image_path=path)
    await message.answer("📹 Anime videosini yuboring:")
    await state.set_state(AnimeAdd.video)


@dp.message(AnimeAdd.video, F.video | F.document)
async def get_video(message: types.Message, state: FSMContext):
    v_id = message.video.file_id if message.video else message.document.file_id
    await state.update_data(video_id=v_id)
    await message.answer("✍️ Anime nomi:")
    await state.set_state(AnimeAdd.name)


@dp.message(AnimeAdd.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("🎭 Janrini yozing:")
    await state.set_state(AnimeAdd.genre)


@dp.message(AnimeAdd.genre)
async def get_genre(message: types.Message, state: FSMContext):
    await state.update_data(genre=message.text)
    await message.answer("📅 Yilini yozing:")
    await state.set_state(AnimeAdd.year)


@dp.message(AnimeAdd.year)
async def save_anime(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO animes (name, genre, year, image_path, video_id) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                    (data['name'], data['genre'], message.text, data['image_path'], data['video_id']))
                new_id = cur.fetchone()[0]
                conn.commit()

        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(text="👁 Tomosha qilish", url=f"https://t.me/{BOT_USERNAME}?start={new_id}"))

        cap = f"🎬 <b>Nomi:</b> {data['name']}\n🎭 <b>Janri:</b> {data['genre']}\n📅 <b>Yili:</b> {message.text}"
        await bot.send_photo(CHANNEL_ID, types.FSInputFile(data["image_path"]), caption=cap, parse_mode="HTML",
                             reply_markup=builder.as_markup())
        await message.answer("✅ Kanalga yuborildi!")
    except Exception as e:
        await message.answer(f"❌ Xato: {e}")
    await state.clear()


async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())