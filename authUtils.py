from logging import warning
import os
import json
from aiogram.types import Message, CallbackQuery
import hashlib
from session import AioSession
from constants import BOT_HANDLE

dir_path = os.path.dirname(os.path.realpath(__file__))
whitelist_path = os.path.join(dir_path, '../whiteList.json')


def loadKey(keyName):
    key = os.environ[keyName]
    key_sha = hashlib.sha1(keyName.encode(encoding='UTF-8', errors='strict'))
    warning(f"{keyName} fingerprint: {key_sha.hexdigest()}")
    return key


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
        warning(f"message from unrecognized user: {message}")
        return False

    if message.chat.type == 'private':
        return True

    if message.reply_to_message\
            and message.reply_to_message.from_user.username == BOT_HANDLE[1:]:
        return True

    chat_id = message.chat.id
    user_message = message.text
    persName = AioSession.getSession(chat_id)._personality
    if (user_message):
        msg = message.text
        if user_message.startswith(persName):
            msg = msg.split(persName)
            msg = msg[1:]
            msg = persName.join(msg).strip()

        elif BOT_HANDLE in user_message:
            msg = msg.replace(BOT_HANDLE, '').strip()

        if msg != message.text:
            if msg.startswith(','):
                msg = msg[1:].strip()
            message.text = msg
            return True
    return False
