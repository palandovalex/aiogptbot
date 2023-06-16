#!/home/lexsilentium/ChatGPTBot/.venv/bin/python

import os
from logging import warning, error
from time import sleep
from requests import ReadTimeout

from aiogram.types import Message, ParseMode
from aiogram.utils.exceptions import CantParseEntities, NetworkError
from aiogram import executor as aio_executor
from asyncio.exceptions import TimeoutError
from aiUtils import aiAnswer, aiHear
from session import AioSession as Session
from authUtils import checkBotReaction
from constants import TMPFS_DIR, BOT as bot, DISP as disp
import bot_options
from key_reset import keyReset

print(bot_options.__doc__)

keyReset()


@disp.message_handler(checkBotReaction, content_types=["text", "voice"])
async def messageHandler(message: Message):
    warning("from msg handler")
    if message.text and message.text.startswith("/"):
        if not message.text.startswith("/img"):
            return

    keyReset()
    prompt = message.text
    chat_id = message.chat.id
    session = Session.getSession(chat_id)

    if session.inputHandler:
        response = session.inputHandler(prompt)
        await bot.send_message(chat_id=chat_id, text=response)
        return

    if message.voice:
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        if file.file_size > 50000000:
            return await message.reply(text="речь слишком длинная")

        status_msg = await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=message.message_id,
            text="Речь распознаётся, пожалуйста подождите...",
        )

        file_path = file.file_path
        tmp_path = os.path.join(TMPFS_DIR, file.file_path)
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
        await bot.download_file(file_path, tmp_path)
        prompt = aiHear(tmp_path)
        if prompt:
            await status_msg.edit_text(f"Вы сказали:\n{prompt}")
        else:
            return await status_msg.edit_text("Речь не распознана")
    if not prompt:
        return

    response = aiAnswer(session, prompt)

    if response[0] == "image":
        img_file = response[1]
        ext = img_file.split(".")[-1]
        if ext in "png.jpg.jpeg.gif.pjpeg.svg.ico.wbmp.webp".split("."):
            await bot.send_photo(chat_id=chat_id, photo=open(img_file, "rb"))
        os.remove(img_file)
        return

    response = response[1]

    async def sendMsg(parse_mode):
        return await bot.send_message(
            chat_id=chat_id,
            reply_to_message_id=message.message_id,
            text=response,
            parse_mode=parse_mode,
        )

    try:
        await sendMsg(ParseMode.MARKDOWN_V2)
    except CantParseEntities as e:
        warning(e)
        await sendMsg(None)


if __name__ == "__main__":
    do_pulling = True
    while do_pulling:
        try:
            warning("running bot")
            aio_executor.start_polling(disp)
            do_pulling = False
        except (ReadTimeout, ConnectionError, NetworkError, TimeoutError) as e:
            error(e)
            sleep(15)
