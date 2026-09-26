import asyncio
from random import choices, randint, shuffle
import psycopg
from time import ctime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
import os
from dotenv import load_dotenv

load_dotenv("secret.env")

#CONF INFO //////////////////////////////
TOKEN = os.environ["BOT_TOKEN"]
conn = psycopg.connect(
    dbname=os.environ["DB_NAME"],
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    host=os.environ["DB_HOST"])
# /// /// /// /// /// /// /// /// /// ///

cursor = conn.cursor()

bot = Bot(TOKEN)
dp = Dispatcher()
with open('Слова ФИПИ.txt', 'r', encoding='utf-8') as f: right_text = f.read()
words_T = [[x.strip(), True] for x in open("Слова ФИПИ.txt", encoding="utf-8")]
words_F = [[x.strip(), False] for x in open("Слова ФИПИ_неправильные ударения.txt", encoding="utf-8")]
words_FT_dict = {words_F[x][0]: words_T[x][0] for x in range(len(words_T))}

menu_text = (
      "🎯 *ЕГЭ по русскому языку: Задание 4 (Ударения)*\n\n"
      "Привет! Здесь ты сможешь до автоматизма отработать официальный "
      "орфоэпический словник ФИПИ. Никакой лишней теории — только реальная практика!\n\n"
      "📈 Каждый правильный ответ улучшает твою статистику и приближает к заветным баллам.\n\n"
      "👇 Начнём тренировку?"
)

text_settings = ("⚙️ Настройки бота:\n\n"
"🤔 Здесь вы можете изучить официальный словник от ФИПИ или.\n"
"✍️ Сохранения помогут вам оставить результаты ваших попыток в истории бота.")

class GameState(StatesGroup):
  playing = State()

def reload_questions():
  while True:
    amount_T = randint(2, 4)
    ch_T = choices(words_T, k=amount_T)
    ch_F = choices(words_F, k=5 - amount_T)

    ch = ch_T + ch_F
    shuffle(ch)

    # Возвращаем список слов и словарь правильных ответов
    current_words = [word[0] for word in ch]
    right_answers = {f"v{index+1}": word[1] for index, word in enumerate(ch)}
    if all(words_FT_dict.get(x, None) not in current_words for x in current_words):
      return current_words, right_answers

def savings_check(a):
  try:
    query = "SELECT savings FROM user_stats WHERE user_id = (%s)"
    cursor.execute(query, (a, ))
    current_flag = bool(cursor.fetchone()[0])
    conn.commit()
  except TypeError:
    current_flag = False
  return current_flag

def get_main_menu_keyboard():
    builder0 = InlineKeyboardBuilder()
    builder0.button(text="🎮 Играть", callback_data="play")
    builder0.button(text="📊 Статистика", callback_data="stats")
    builder0.button(text="⚙️ Настройки", callback_data="settings")
    builder0.button(text="📢 Жалоба", callback_data="report")
    builder0.adjust(2)
    return builder0.as_markup()

# ВЫВОДИТ МЕНЮ
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
  await message.delete()
  await state.clear()

  await message.answer(text=menu_text, reply_markup=get_main_menu_keyboard())

# ТОЖЕ ВЫВОДИТ МЕНЮ
@dp.callback_query(F.data == "exit")
async def exit_to_the_start_menu(callback: CallbackQuery, state: FSMContext):
  await callback.message.delete()
  await state.clear()

  builder0 = InlineKeyboardBuilder()
  builder0.button(text="🎮 Играть", callback_data="play")
  builder0.button(text="📊 Статистика", callback_data="stats")
  builder0.button(text="⚙️ Настройки", callback_data="settings")
  builder0.button(text="📢 Жалоба", callback_data="report")
  builder0.adjust(2)

  await callback.message.answer(text=menu_text, reply_markup=get_main_menu_keyboard())

@dp.callback_query(F.data.in_({"theory", "settings", "savings"}))
async def go_to_settings(callback: CallbackQuery, state: FSMContext):
  await callback.answer()

  my_callback_data = callback.data

  if my_callback_data == "savings":
    query = "INSERT INTO user_stats (user_id, user_games_count, user_victouries_count, user_winrate, user_time, savings)" \
    "VALUES (%s, 0, 0, 0, %s, FALSE) " \
    "ON CONFLICT (user_id) DO NOTHING "
    cursor.execute(query, (callback.from_user.id, ctime()))
    conn.commit()
    current_flag = await asyncio.to_thread(savings_check, callback.from_user.id)
    current_flag = not(current_flag)
    query = "UPDATE user_stats SET savings = (%s) WHERE user_id = (%s)"
    cursor.execute(query, (current_flag, callback.from_user.id))
    conn.commit()

  current_flag = await asyncio.to_thread(savings_check, callback.from_user.id)
    
  builder_set = InlineKeyboardBuilder()
  builder_set.button(text="📔 Список слов ФИПИ", callback_data="theory")
  if current_flag == False:
    builder_set.button(text="📁 Сохранения: Включены", callback_data="savings")
  else:
    builder_set.button(text="📂 Сохранения: Выключены", callback_data="savings")
  builder_set.button(text="🚪 Назад", callback_data="exit")
  builder_set.adjust(2)

  if my_callback_data in ("settings", "savings"):
    await callback.message.edit_text(text=text_settings, reply_markup=builder_set.as_markup())

  if my_callback_data == "theory":
    await callback.message.edit_text(text=right_text, reply_markup=builder_set.as_markup())

# REPORT
@dp.callback_query(F.data == "report")
async def handle_report(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.update_data(needhelp=True)
    
    button_report = InlineKeyboardBuilder()
    button_report.button(text="🚪 Выход", callback_data="exit")

    sent_message = await callback.message.answer(text="⚠️ Режим отправки репорта\n\nПопытайтесь описать проблему, с которой вы столкнулись. Учтите, что максимальное кол-во символов = 2001", reply_markup=button_report.as_markup())
    await state.update_data(needhelp=True, report_msg_id=sent_message.message_id)
    await callback.answer()
  
@dp.message() 
async def echo_handler(message: Message, state: FSMContext):
  user_data = await state.get_data()
  if user_data.get("needhelp", False) == True:
      query = "INSERT INTO user_reports (user_id, time_report, text_of_report) " \
      "VALUES (%s, %s, %s)"
      cursor.execute(query, (message.from_user.id, ctime(), message.text))
      conn.commit()
      report_msg_id = user_data.get("report_msg_id")
      if report_msg_id:
          try:
              await message.bot.delete_message(chat_id=message.chat.id, message_id=report_msg_id)
          except Exception:
              pass
  await state.clear()
  await message.delete()
  await message.answer(text=menu_text, reply_markup=get_main_menu_keyboard())

# ВЫВОД СТАТИСТИКИ
@dp.callback_query(F.data == "stats")
async def handle_button_click2(callback: CallbackQuery):
  await callback.message.delete()
  query = "SELECT * FROM user_stats WHERE user_id = %s"
  cursor.execute(query, (callback.from_user.id,))
  builderstats = InlineKeyboardBuilder()
  builderstats.button(text="🚪 Назад", callback_data="exit")

  user_info = cursor.fetchone()
  if user_info:
    user_id, user_games_count, user_victouries_count, user_winrate, user_time, user_savings =  user_info

    stats_text = (
                  "📊 Статистика выполнений: \n\n"
              f"📝 Всего заданий выполнено: {user_games_count}\n"
              f"🟢 Выполненных верно заданий: {user_victouries_count}\n"
              f"📈 Винрейт: {user_winrate}%\n\n"
    )
    await callback.message.answer(text = stats_text, reply_markup=builderstats.as_markup())
  else:
    await callback.message.answer(text = "☹️ Вы ещё не играли.", reply_markup=builderstats.as_markup())

# ПРОВЕРКА ОТВЕТОВ
@dp.callback_query(F.data == "check", GameState.playing)
async def check_answers(callback: CallbackQuery, state: FSMContext):

  user_data = await state.get_data()
  flags = user_data.get("flags", {"v1": False, "v2": False, "v3": False, "v4": False, "v5": False})
  answers = user_data.get("answers", {})
  words = user_data.get("words", ["", "", "", "", ""])

  text_numbers = []

  for index, x in enumerate(words):
    if answers.get(f"v{index+1}") == True:
      text_numbers.append(f"{x}")
    else:
      text_numbers.append(f"{x} => {words_FT_dict.get(x, x)}")

  right_ans_flag = True
  builder2 = InlineKeyboardBuilder()

  for i in range(5):
    key = f"v{i+1}"
    if answers.get(key) == flags.get(key):
      builder2.button(text=f"{text_numbers[i]} ✅", callback_data="__")
    else:
      builder2.button(text=f"{text_numbers[i]} ❌", callback_data="__")
      right_ans_flag = False

  builder2.button(text="➡️ Далее", callback_data="next")
  builder2.button(text="🚪 Назад", callback_data="exit")
  builder2.adjust(1)
  
  if right_ans_flag == True:
    await callback.message.edit_text(text="✅ <b>Правильно.</b> Продолжайте в том же духе!", parse_mode="HTML", reply_markup=builder2.as_markup())
    start_victory = 1
    start_winrate = 100
  else:
    await callback.message.edit_text(text="❌ <b>Неверный ответ</b>. Попробуйте еще раз!", parse_mode="HTML", reply_markup=builder2.as_markup())
    start_victory = 0
    start_winrate = 0

  query = "INSERT INTO user_stats (user_id, user_games_count, user_victouries_count, user_winrate, user_time, savings) " \
          "VALUES (%s, 1, %s, %s, %s, FALSE) " \
          "ON CONFLICT (user_id) " \
          "DO UPDATE SET " \
          "user_time = EXCLUDED.user_time, " \
          "user_games_count = user_stats.user_games_count + 1, " \
          "user_victouries_count = user_stats.user_victouries_count + EXCLUDED.user_victouries_count, " \
          "user_winrate = ROUND(((user_stats.user_victouries_count + EXCLUDED.user_victouries_count)::NUMERIC / (user_stats.user_games_count + 1)) * 100, 2);"

  a = (callback.from_user.id, start_victory, start_winrate, ctime())
  cursor.execute(query, a)
  conn.commit()
  await state.clear()

# ОБРАБОТКА ИГРЫ И КЛИКОВ ПО ВАРИАНТАМ
@dp.callback_query(F.data == "next")
@dp.callback_query(F.data == "play")
@dp.callback_query(F.data.in_({"v1", "v2", "v3", "v4", "v5"}), GameState.playing)
async def handle_game_process(callback: CallbackQuery, state: FSMContext):
  await callback.answer()
  my_callbackdata = callback.data

  if my_callbackdata in ("play", "next"):
    await state.set_state(GameState.playing)

    current_words, right_answers = reload_questions()
    initial_flags = {"v1": False, "v2": False, "v3": False, "v4": False, "v5": False,}
    await state.update_data(words=current_words, answers=right_answers, flags=initial_flags)
    user_data = await state.get_data()

    if my_callbackdata == "play":
        await callback.message.delete()

  else:
    user_data = await state.get_data()
    flags = user_data.get("flags", {})

    flags[my_callbackdata] = not flags.get(my_callbackdata, False)
    await state.update_data(flags=flags)
    user_data["flags"] = flags

  words = user_data.get("words", ["", "", "", "", ""])
  flags = user_data.get("flags", {})

  builder11 = InlineKeyboardBuilder()
  for index, x in enumerate(words):
    key = f"v{index+1}"
    is_checked = flags.get(key, False)
    builder11.button(text=f"{x} ✔" if is_checked else f"{x}", callback_data=key)

  builder11.button(text="✍️ Проверить", callback_data="check")
  builder11.button(text="🚪 Назад", callback_data="exit")
  builder11.adjust(1)

  current_flag = await asyncio.to_thread(savings_check, callback.from_user.id)

  if my_callbackdata == "play" or (current_flag == False and my_callbackdata in ("next", "exit")):
    await callback.message.answer(text="В каком слове <b>ВЕРНО</b> выделена буква, обозначающая ударный гласный звук?\n\n", parse_mode="HTML", reply_markup=builder11.as_markup())
  else:
    await callback.message.edit_text(text="В каком слове <b>ВЕРНО</b> выделена буква, обозначающая ударный гласный звук?\n\n", parse_mode="HTML", reply_markup=builder11.as_markup())

async def main():
  await dp.start_polling(bot)

if __name__ == "__main__":
  asyncio.run(main())