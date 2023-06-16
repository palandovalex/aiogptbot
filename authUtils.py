from logging import warning
import os
import json
from aiogram.types import CallbackQuery, Message
from session import AioSession
from constants import CHATBOT_HANDLE

dir_path = os.path.dirname(os.path.realpath(__file__))
whitelist_path = os.path.join(dir_path, "../whiteList.json")


with open(whitelist_path, "r") as file:
    whiteList = json.load(file)
    user_ids = whiteList["users"]
    chat_ids = whiteList["chats"]


def checkChat(chat_id: int):
    if chat_id in chat_ids:
        return True


def checkUser(user_id: int):
    if user_id in user_ids:
        return True


def checkAuth(message: Message):
    chat_id = message.chat.id
    return checkUser(chat_id) or checkChat(chat_id)


def checkCallbackReaction(call: CallbackQuery):
    message = call.message
    if checkAuth(message):
        return True


def checkBotReaction(message: Message):
    if not checkAuth(message):
        return False

    if message.chat.type == "private":
        return True

    if message.reply_to_message.from_user.username == CHATBOT_HANDLE[1:]:
        return True

    if message.text:
        chat_id = message.chat.id
        persName = AioSession.getSession(chat_id)._personality
        user_message = message.text
        if user_message.startswith(persName) or CHATBOT_HANDLE in user_message:
            message.text = message.text.replace(CHATBOT_HANDLE, "")
            return True
    return False
