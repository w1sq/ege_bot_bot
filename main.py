# coding=utf8
import asyncio
import aiogram
from sqlalchemy import func
import random
import aioschedule
import os
import pandas
import dataframe_image
from aiogram.dispatcher.filters.state import State, StatesGroup
import datetime
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from db_data import db_session
from db_data.__all_models import User, StudyRecord
import matplotlib.pyplot as plt
import pandas as pd
from pandas.plotting import table

API_KEY = "6070681835:AAEwkqHsGGct7o8KBXzqxGG_OEOzxy_CsVg"
group_id = "-1001687206399"
# group_id = "-1001915266423" #канал
last_data = None

bot = Bot(token=API_KEY)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
db_session.global_init()
print('Bot started')

menu_keyb = ReplyKeyboardMarkup(resize_keyboard=True).row(KeyboardButton(text='Учиться')).row(KeyboardButton(text='Таблица'), KeyboardButton(text='Онлайн'))

class NewState(State):
    async def set(self, user=None):
        state = dp.current_state(user=user)
        await state.set_state(self.state)

class GetCircle(StatesGroup):
    circle = NewState()

workers = {}
checks = {}

@dp.message_handler(commands=['start'])
async def start(message:aiogram.types.Message):
    if message.chat.type == "private":
        db_sess = db_session.create_session() 
        # user = db_sess.query(User).get(message.chat.id)
        user = db_sess.get(User, message.chat.id)
        if not user:
            name = dict(message.from_user).get('first_name', '') + ' ' + dict(message.from_user).get('last_name', '')
            user=User(id=message.chat.id, name=name)
            db_sess.add(user)
            db_sess.commit()
            await message.answer('Добро пожаловать!\nЧитай правила: /rules\nЕсли всё знаешь - желаю продуктивной работы', reply_markup=menu_keyb)
        else:
            await message.answer('Добро пожаловать назад', reply_markup=menu_keyb)
        db_sess.close()
    else:
        await message.answer('Работаю только в <a href="https://t.me/egebotbot">личных сообщениях</a>', parse_mode='HTML')
        # await message.answer('Очистил клавиатуру', reply_markup=aiogram.types.ReplyKeyboardRemove())

@dp.message_handler(commands=['rules'])
async def rules(message:aiogram.types.Message):
    await message.answer('Пока правила простые:\n1)Начинаешь отсчет времени по кнопке Учиться\n2)Учишься\n3)Раз в час тебе может придти уведомление от бота прислать кружок, если за 2 минуты ты его не присылаешь, то твой таймер обнуляется. Если ты успеваешь - кружок отсылается в общую группу, где все оценивают твоё трудолюбие.')

@dp.message_handler(text="Учиться")
async def study(message:aiogram.types.Message):
    if message.chat.type != "private":
        await message.answer('Сколько раз тебе говорить что эта функция не доступна в этой группе?')
    elif message.chat.id in workers.keys() and workers[message.chat.id] is not None:
        await message.answer('Ты уже занимаешься, куда тебе еще')
    else:
        finish_keyb = InlineKeyboardMarkup().row(InlineKeyboardButton(text='ЗАКОНЧИТЬ', callback_data=f'finish {message.chat.id}'))
        answer = await message.answer('Я начал отсчитывать время, но если проколешься с кружком - вечный позор и отмена всего времени', reply_markup=finish_keyb)
        await answer.pin(disable_notification=True)
        await message.chat.delete_message(answer.message_id+1)
        workers[message.chat.id] = datetime.datetime.now()
        checks[message.chat.id] = datetime.datetime.now() + datetime.timedelta(minutes=random.randint(40, 90))
        # checks[message.chat.id] = datetime.datetime.now() + datetime.timedelta(seconds=random.randint(1, 5))

async def check_circles():
    for user in checks.keys():
        if checks[user] and checks[user] < datetime.datetime.now():
            await bot.send_message(user, 'Пришло время прислать кружок, где ты ботаешь. У тебя 2 минуты!')
            await GetCircle.circle.set(user=user)
            state = dp.current_state(user=user)
            await state.update_data(start = checks[user].strftime("%m/%d/%Y, %H:%M:%S"))
            checks[user] = ''

@dp.message_handler(state=GetCircle.circle, content_types=['text','video_note'])
async def process_circle(message: aiogram.types.Message, state: aiogram.dispatcher.FSMContext):
    state_data = await state.get_data()
    time = datetime.datetime.strptime(state_data['start'], "%m/%d/%Y, %H:%M:%S")
    if (datetime.datetime.now() - time).seconds > 120:
        await message.answer('Ты опоздал... Время этой сессии тебе не зачтется')
        workers[message.chat.id] = None
        checks[message.chat.id] = None
        await state.finish()
    elif message.text:
        await message.answer('Текст здесь не принимается')
    else:
        await message.answer('Всё окей, продолжай работать. Кружок я переслал твоим друзьям на оценку')
        # checks[message.chat.id] = datetime.datetime.now() + datetime.timedelta(seconds=random.randint(1, 5)) 
        checks[message.chat.id] = datetime.datetime.now() + datetime.timedelta(minutes=random.randint(40, 90))
        await bot.send_message(group_id, f"Посмотрите на вашего друга {dict(message.from_user).get('first_name', '') + ' ' + dict(message.from_user).get('last_name', '')} за работой")
        await message.forward(group_id)
        await state.finish()

@dp.callback_query_handler(lambda call: call.data.startswith('finish '))
async def finish_study(call:aiogram.types.CallbackQuery):
    user_id = int(call.data.split()[1])
    if user_id in workers.keys() and workers[user_id]:
        await call.message.edit_reply_markup(reply_markup=None)
        checks[call.message.chat.id] = None
        duration = (datetime.datetime.now() - workers[user_id]).seconds // 60
        db_sess = db_session.create_session()
        if duration < 30:
            await call.message.answer('Не густо, но лучше чем ничего...\nПрибавил тебе твои гроши', reply_markup=menu_keyb)
        elif duration >= 30 and duration < 120:
            await call.message.answer('Средненький результат, но все равно молодец', reply_markup=menu_keyb)
        else:
            await call.message.answer('Обалденная работа, респект', reply_markup=menu_keyb)
        await call.message.chat.unpin_all_messages()
        # user = db_sess.query(User).get(user_id)
        user = db_sess.get(User, user_id)
        record = db_sess.query(StudyRecord).join(StudyRecord.user).filter(StudyRecord.date == workers[user_id].date(), User.id == user.id).first()
        if record:
            record.minutes += duration
        else:
            record = StudyRecord(date=workers[user_id].date(), minutes = duration)
            user.records.append(record)
        workers[user_id] = None
        db_sess.commit()
        db_sess.close()
    else:
        await call.message.answer('У тебя сейчас нет активной сессии')

@dp.message_handler(text="Таблица")
async def send_table(message:aiogram.types.Message):
    global last_data
    db_sess = db_session.create_session()
    indexes =  []
    id_indexes = []
    users = db_sess.query(User).all()
    for user in users:
        if db_sess.query(StudyRecord).join(StudyRecord.user).filter(User.id == user.id, StudyRecord.minutes > 0).count() > 0:
            indexes.append(user.name)
            id_indexes.append(user.id)
    first_record = db_sess.get(StudyRecord, db_sess.query(func.min(StudyRecord.id)).scalar())
    last_record = db_sess.get(StudyRecord, db_sess.query(func.max(StudyRecord.id)).scalar())
    cols = [first_record.date + datetime.timedelta(days=dayss) for dayss in range(0,(last_record.date-first_record.date).days+1)]
    data = {}
    for col in cols:
        data[col.strftime("%d/%m")] = [str(db_sess.query(StudyRecord).join(StudyRecord.user).filter(StudyRecord.date == col, User.id == id_index).first()) if db_sess.query(StudyRecord).join(StudyRecord.user).filter(StudyRecord.date == col, User.id == id_index).first() is not None else '0' for id_index in id_indexes]
    cols = [col.strftime("%d/%m") for col in cols]
    df = pandas.DataFrame(data, index=pandas.Index(indexes), columns=pandas.Index(cols))
    if last_data == data:
        with open('table.png', 'rb') as file:
            await message.answer_photo(file)
    else:
        ax = plt.subplot(111, frame_on=False) # no visible frame
        ax.xaxis.set_visible(False)  # hide the x axis
        ax.yaxis.set_visible(False)  # hide the y axis
        table(ax, df, loc='center')
        # table(ax, df)  # where df is your data frame
        last_data = data
        name = 'table.png'
        plt.savefig(name, bbox_inches='tight')
        # dataframe_image.export(df, name, fontsize=20)
        with open('table.png', 'rb') as file:
            await message.answer_photo(file)
    db_sess.close()

@dp.message_handler(text="Онлайн")
async def send_online(message:aiogram.types.Message):
    db_sess = db_session.create_session()
    users = db_sess.query(User).all()
    text = 'Сейчас работают:\n'
    for user in users:
        if user.id in workers.keys() and workers[user.id] is not None:
            text += f'<a href="tg://user?id={user.id}">{user.name}</a>\n'
    if text == 'Сейчас работают:\n':
        await message.answer('Пока никто не работает')
    else:
        await message.answer(text, parse_mode='HTML')
    db_sess.close()

async def check_schedule():
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)

if __name__ == '__main__':
    aioschedule.every().second.do(check_circles)
    loop = asyncio.get_event_loop()
    loop.create_task(check_schedule())
    loop.run_until_complete(dp.start_polling())