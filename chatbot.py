#!/home/lexsilentium/ChatGPTBot/.venv/bin/python

from dotenv import load_dotenv
load_dotenv()

from collections.abc import Iterable, Sequence
from ctypes import ArgumentError
from logging import warning, error
from time import sleep
from aiogram.utils.exceptions import CantParseEntities, NetworkError
from aiogram.utils.markdown import escape_md
from requests import ReadTimeout
from aiogram import Dispatcher, Bot, executor as aio_executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, ParseMode
from asyncio.exceptions import TimeoutError
import openai
from aiUtils import aiAnswer, aiHear
from session import AioSession as Session
from authUtils import loadKey, checkCallbackReaction, checkBotReaction
from constants import TMPFS_DIR, BOT as bot, DISP as disp
import os
from key_reset import KEY_ROLLER, keyReset

try:
    #bot = Bot(loadKey("TG_AUTH_TOKEN"))
    keyReset()
    #openai.api_key = next(KEY_ROLLER)
except Exception as e:
    error(e)
    raise
    
#disp = Dispatcher(bot)


def handleOptionInputItem(item: Sequence, session: Session):
    session_id = session.session_id
    warning(f"session_id: {session_id}")
    handlers = session.getOptHandlers()
    if len(item) not in (1,2):
        raise ArgumentError()

    if len(item) == 2:
        key, value = item
        text = handlers[key][1](value) or f"Setting [{key}] is set to [{value}]"
    else:
        optKey = item[0]
        if isinstance(handlers[optKey][0], Iterable):
            choises = handlers[optKey][0]
            j=lambda v: optKey + '=' + v
            btnsData = [[(value, j(value))] for value in choises ]
            markup = renderKeyboard(btnsData)
            text = f'Chouse {optKey} value:'
            return bot.send_message(chat_id=session_id, text=text, reply_markup=markup)
        else:
            valType = handlers[optKey][0]
            session.inputHandler = handlers[optKey][1]
            text = f'enter the value for {optKey}, value must be a "{valType}"'
    return bot.send_message(chat_id=session_id, text=text)


@disp.message_handler(checkBotReaction, commands=['opt'])
async def optHandler(message: Message):

    session_id = message.chat.id
    session = Session.getSession(session_id)
    input = message.text.replace('/opt', '').strip()
    if input:
        item = input.split('=')
        try:
            return await handleOptionInputItem(item, session)
        except (KeyError, ValueError, ArgumentError):
            return await bot.send_message(chat_id=session_id, text='bad input')
    else:

        choises = session.optKeys()
        buttonts = [[(k+'='+ str(session.getOpt(k))  , k)] for k in choises] 
        markup = renderKeyboard(buttonts)

        text='You can change one of this options:'
        return await message.reply(text=text, reply_markup=markup)
    

@disp.message_handler(checkBotReaction, commands=['clear'])
async def cleanHandeler(message: Message):
    markup = renderKeyboard ([
        [ ('clean current current', 'clear') ], 
        [ ("clean all history", 'clearAll') ],
        [ ('cancel', 'rm_markup') ]
    ])

    await bot.send_message(message.chat.id, 'Conform history cleaning', reply_markup=markup)


def renderKeyboard(buttonsData):
    keyboard = InlineKeyboardMarkup()
    for row in buttonsData:
        btnRow = []    
        for text, call_data in row:
            btnRow.append(InlineKeyboardButton(text=text, callback_data=call_data))
        keyboard.row(*btnRow)
        
    return keyboard


@disp.message_handler(checkBotReaction, commands=['pers'])
async def personality_handler(message:Message):
    chat_id = message.chat.id
    session = Session.getSession(chat_id)

    input = message.text.replace('/pers','').strip()
    if input == '':
        text = f"Текущая персональность: [{session._personality}] "
        text += f"\n Персональности в текущей сессии: \n"
        for persName, pers in session.personalities.items():
            text += f"[{persName}] = [{pers}]\n"
        text += "\nдля описания комманды:\n/pers -h"

    elif input.startswith(('-h','--help',)):
        text =  '\nкоманда /pers может: \n,выводить список персональностей при пустом вводе,'
        text += '\nили принимает [personality name], которое следует установить,'
        text += '\nили выражение [persName=personality value] для задания новой или изменения имеющейся персональности.'
        text += '\nМожно также удалить персональность:\n /pers --rm [pers name]\n'

    elif input.startswith('--rm'):
        input.replace('--rm','').strip()
        text = session.remove_personality(input)
    else:
        input = input.split('=')
        if len(input) == 1:
            text = session.set_personality(input[0])
        else:
            personality = "=".join(input[1:])
            text = session.update_personality(input[0],personality)
     
    return await bot.send_message(chat_id=chat_id, text=text)


@disp.callback_query_handler(checkCallbackReaction)
async def callback_Handler(call: CallbackQuery):
    warning('from callback_Handler') 
    chat_id = call.message.chat.id
    warning(f"chat_id: {chat_id}")
    warning(call)
    session = Session.getSession(chat_id)
    warning(f"session_id: {session.session_id}")
    

    call_data = call.data.split('=')
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    target = call_data[0]
    if target in ('clear','clearAll'):
        warning('from clear') 
        result = session.cleanHistory(target)
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        return await bot.send_message(chat_id=chat_id, text=result)
    
    elif target == 'rm_markup':
        warning('from rm_markup') 
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        return
    else:
        warning('from handle option item') 
        await handleOptionInputItem(call_data, session)
    
    
def checkMessage(message: Message):
    return checkBotReaction(message) and (message.text or message.voice)


@disp.message_handler(checkMessage, content_types=['text', 'voice'])
async def messageHandler(message: Message): 
    warning('from msg handler')
    if message.text and message.text.startswith('/'):
        if not message.text.startswith('/img'):
            return
    prompt = message.text
    chat_id = message.chat.id
    session = Session.getSession(chat_id)
    
    
    if session.inputHandler:
        response = session.inputHandler(prompt)
        await bot.send_message(chat_id=chat_id, text=response)
    
    else:
        if message.voice:
            file_id = message.voice.file_id
            file = await bot.get_file(file_id)
            if file.file_size > 50000000:
                return await message.reply(text='речь слишком длинная') 
            
            status_msg = await bot.send_message(
                chat_id=chat_id, 
                reply_to_message_id=message.message_id, 
                text='Речь распознаётся, пожалуйста подождите...'
            )

            file_path = file.file_path 
            tmp_path = os.path.join(TMPFS_DIR, file.file_path)
            os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
            await bot.download_file(file_path, tmp_path)
            prompt = aiHear(tmp_path)
            if prompt:
                await status_msg.edit_text(f"Вы сказали:\n{prompt}")
            else:
                return await status_msg.edit_text(f"Речь не распознана")
        if not prompt:
            return

        response = aiAnswer(session, prompt)
        keyReset()
        
        if response[0] == 'image':
            img_file = response[1]
            ext = img_file.split('.')[-1]
            if ext in 'png.jpg.jpeg.gif.pjpeg.svg.ico.wbmp.webp'.split('.'):
                await bot.send_photo(chat_id=chat_id, photo=open(img_file, 'rb'))
            os.remove(img_file)
            return
        response = response[1]
        

        async def sendMsg(parse_mode):
            return await bot.send_message(
                chat_id=chat_id, 
                reply_to_message_id=message.message_id, 
                text=response, 
                parse_mode=parse_mode)
        try:
            await sendMsg(ParseMode.MARKDOWN_V2)
        except CantParseEntities as e:
            warning(e)
            await sendMsg(None)

if __name__ == '__main__':
    do_pulling = True
    while do_pulling:
        try:
            warning("running bot")
            aio_executor.start_polling(disp)
            do_pulling = False
        except (ReadTimeout, ConnectionError, NetworkError, TimeoutError) as e:
            error(e)
            sleep(15)
