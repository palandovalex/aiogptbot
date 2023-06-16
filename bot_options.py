#!/home/lexsilentium/ChatGPTBot/.venv/bin/python
"""
This file will add option handlers to bot. 1
"""
from collections.abc import Iterable, Sequence
from ctypes import ArgumentError
from logging import warning

from aiogram.types import (
    InlineKeyboardButton as IKbButton,
    InlineKeyboardMarkup as IKbMarkup,
    Message,
    CallbackQuery,
)

from aiogram.utils.callback_data import CallbackData
from session import AioSession as Session
from authUtils import checkBotReaction, checkCallbackReaction
from prompts_loader import PROMPTS
import paginate_bot
from constants import DISP as disp, BOT as bot


def handleOptionInputItem(item: Sequence, session: Session):
    session_id = session.session_id
    warning(f"session_id: {session_id}")
    handlers = session.getOptHandlers()
    if len(item) not in (1, 2):
        raise ArgumentError()

    if len(item) == 2:
        key, value = item
        text = handlers[key][1](value) or f"[{key}] set to [{value}]"
        return bot.send_message(chat_id=session_id, text=text)

    optKey = item[0]

    if isinstance(handlers[optKey][0], Iterable):
        choises = handlers[optKey][0]

        def j(v):
            return optKey + "=" + v

        btnsData = [[(value, j(value))] for value in choises]
        markup = renderKeyboard(btnsData)
        text = f"Chouse {optKey} value:"
        return bot.send_message(session_id, text, reply_markup=markup)

    valType = handlers[optKey][0]
    session.inputHandler = handlers[optKey][1]
    text = f'enter the value for {optKey}, value must be a "{valType}"'
    return bot.send_message(chat_id=session_id, text=text)


@disp.message_handler(checkBotReaction, commands=["opt"])
async def optHandler(message: Message):
    session_id = message.chat.id
    session = Session.getSession(session_id)
    input = message.text.replace("/opt", "").strip()
    if input:
        item = input.split("=")
        try:
            return await handleOptionInputItem(item, session)
        except (KeyError, ValueError, ArgumentError):
            return await bot.send_message(chat_id=session_id, text="bad input")
    else:
        choises = session.optKeys()
        buttonts = [[(k + "=" + str(session.getOpt(k)), k)] for k in choises]
        markup = renderKeyboard(buttonts)

        text = "You can change one of this options:"
        return await message.reply(text=text, reply_markup=markup)


@disp.message_handler(checkBotReaction, commands=["clear"])
async def cleanHandeler(message: Message):
    markup = renderKeyboard(
        [
            [("clean current current", "clear")],
            [("clean all history", "clearAll")],
            [("cancel", "rm_markup")],
        ]
    )

    await bot.send_message(
        message.chat.id, "Conform history cleaning", reply_markup=markup
    )


def renderKeyboard(buttonsData: list[list[tuple[str, str]]]):
    keyboard = IKbMarkup()
    for row in buttonsData:
        btnRow = []
        for text, call_data in row:
            btnRow.append(IKbButton(text=text, callback_data=call_data))
        keyboard.row(*btnRow)

    return keyboard


choosePersCallbackData = CallbackData("choosePersonality", "chooseFrom")
setPersCallbackData = CallbackData("setPersonality", "index")
default_pers_callback = CallbackData("pers", "index")


@disp.callback_query_handler(checkCallbackReaction, choosePersCallbackData.filter())
async def choose_pers_handler(callback_query: CallbackQuery, callback_data: dict):
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    session = Session.getSession(chat_id)
    chooseFrom = callback_data["chooseFrom"]
    print(chooseFrom)

    def clb(**kwargs):
        return type("CallbackFunctor", (object,), kwargs)()

    if chooseFrom == "session":
        items = [key for key in session.personalities.keys()]

        def call(self, id):
            return session.set_personality(self.items[id])

    elif chooseFrom == "presets":
        items = [prompt for prompt in PROMPTS.keys()]

        def call(self, id):
            return session.update_personality(self.items[id], PROMPTS[self.items[id]])

    else:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"unknown destination {chooseFrom}",
        )
        return

    session.inputHandler = clb(items=items, __call__=call)

    msg_del = bot.delete_message(chat_id=chat_id, message_id=message_id)
    await paginate_bot.send_items_list(chat_id, setPersCallbackData, items)
    await msg_del


@disp.callback_query_handler(checkCallbackReaction, setPersCallbackData.filter())
async def set_pers_handler(
    callback_query: CallbackQuery,
    callback_data: dict,
):
    chat_id = callback_query.message.chat.id
    msg_id = callback_query.message.message_id
    session = Session.getSession(chat_id)
    index = callback_data["index"]
    print("from set_pers_handler", session.inputHandler)
    handler = session.inputHandler
    session.inputHandler = None
    if handler:
        output = handler(int(index))
        await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=output)
    else:
        output = 'Сессия "забыла" контекст, пожалуйста повторите ввод:'
        await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=output)


@disp.message_handler(checkBotReaction, commands=["pers"])
async def personality_handler(message: Message):
    chat_id = message.chat.id
    session = Session.getSession(chat_id)
    markup = None

    input = message.text.replace("/pers", "").strip()
    if input == "":
        text = f"Текущая персональность: [{session._personality}] "
        text += "\n Персональности в текущей сессии: \n"
        for persName in session.personalities.keys():
            text += f"{persName}\n"
        text += "\nдля описания комманды:\n/pers -h"

        btnsData = [
            [
                (
                    "Выбрать из текущих",
                    choosePersCallbackData.new(chooseFrom="session"),
                ),
                (
                    "Выбрать из пресетов",
                    choosePersCallbackData.new(chooseFrom="presets"),
                ),
            ]
        ]
        markup = renderKeyboard(btnsData)

    elif input.startswith(
        (
            "-h",
            "--help",
        )
    ):
        text = "\nкоманда /pers может: \n,выводить "
        "список персональностей при пустом вводе,"
        "\nили принимает [personality name], которое следует установить,"
        "\nили выражение [persName=personality value] для задания"
        " новой или изменения имеющейся персональности."
        "\nМожно также удалить персональность:\n /pers --rm [pers name]\n"

    elif input.startswith("--rm"):
        input.replace("--rm", "").strip()
        text = session.remove_personality(input)
    else:
        input = input.split("=")
        if len(input) == 1:
            text = session.set_personality(input[0])
        else:
            personality = "=".join(input[1:])
            text = session.update_personality(input[0], personality)

    return await bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)


@disp.callback_query_handler(checkCallbackReaction)
async def callback_Handler(call: CallbackQuery):
    warning("from callback_Handler")
    chat_id = call.message.chat.id
    warning(f"chat_id: {chat_id}")
    warning(call)
    session = Session.getSession(chat_id)
    warning(f"session_id: {session.session_id}")

    call_data = call.data.split("=")
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    target = call_data[0]
    if target in ("clear", "clearAll"):
        warning("from clear")
        result = session.cleanHistory(target)
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        return await bot.send_message(chat_id=chat_id, text=result)

    elif target == "rm_markup":
        warning("from rm_markup")
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        return
    else:
        warning("from handle option item")
        await handleOptionInputItem(call_data, session)
