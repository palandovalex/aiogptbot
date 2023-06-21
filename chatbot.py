#!/home/lexsilentium/ChatGPTBot/.venv/bin/python

import os
from logging import warning, error
from time import sleep
from requests import ReadTimeout

from aiogram.types import Message, ParseMode
from types import CoroutineType
from aiogram.dispatcher.filters import MediaGroupFilter
from aiogram.utils.exceptions import CantParseEntities, NetworkError
from aiogram import executor as aio_executor
from asyncio.exceptions import TimeoutError
from aiUtils import aiAnswer, aiHear, aiDraw
from session import AioSession as Session
from authUtils import checkBotReaction
from constants import TMPFS_DIR, BOT as bot, DISP as disp
import bot_options
from key_reset import keyReset
from aiogram_media_group import media_group_handler

import time

print(bot_options.__doc__)

keyReset()
async def downloadFile(file_url):
    file_path = (await bot.get_file(file_url)).file_path
    tmp_file_path = os.path.join(TMPFS_DIR, file_path)
    await bot.download_file(file_path, tmp_file_path)
    return tmp_file_path


def includeGroup(is_group): return MediaGroupFilter(is_media_group=is_group)


@disp.message_handler(
    checkBotReaction, includeGroup(False),
    content_types=['photo', 'document']
)
async def photo_handler(message: Message):
    keyReset()
    warning('from photo_handler')
    warning(message)
    prompt = message.caption or ''
    chat_id = message.chat.id
    session = Session.getSession(chat_id)

    if message.document:
        file = await message.document.get_file()
        mime = message.document.mime_type
        if not mime.startswith('image'):
            return await message.reply(text='Отправьте мне изображение(jpeg, png, gif). Подробнее смотри по команде /help')
        if prompt and mime not in ['image/png', 'image/gif']:
            return await message.reply('невозможно обработать изображение с комментарием, если в изображении нет альфа канала.')
    else:
        file = await message.photo[-1].get_file()
    # elif file.mime_type not in ['image/png', 'image/gif']

    tmp_img_path = downloadFile(file.file_id)
    response = aiDraw(session, prompt, await tmp_img_path)

    await sendAiResponse(message, chat_id, await response)


@disp.message_handler(
        checkBotReaction,
        includeGroup(True),
        content_types=['document', 'photo'])
@media_group_handler
async def photo_mask_handler(messages: list[Message]):

    warning('from photo_mask_handler')
    msg_iter = iter(messages)
    message = next(msg_iter)
    keyReset()
    prompt = message.caption or ''
    chat_id = message.chat.id
    session = Session.getSession(chat_id)

    if message.document:
        mime = message.document.mime_type
        if not mime.startswith('image'):
            return await message.reply(text='Отправьте мне группу изображений(jpeg, png, gif). Подробнее смотри по команде /help')
        image = await message.document.get_file()
    else:
        image = await message.photo[-1].get_file()

    image_id = image.file_id

    message = next(msg_iter)

    if message.document:
        mask_mime = message.document.mime_type
        if mask_mime not in ['image/png', 'image/gif']:
            return await message.reply('Этот тип маски не реализован, Используйте png или gif')
        mask = await message.document.get_file()
    else:
        mask = await message.photo[-1].get_file()

    mask_id = mask.file_id

    def clb(**kwargs):
        return type("CallbackFunctor", (object,), kwargs)()

    async def handleMediaGroup(self, text):
        temp_image_path = downloadFile(self.image_id)
        temp_mask_path = downloadFile(self.mask_id)
        response = await aiDraw(
            session, text,
            await temp_image_path,
            await temp_mask_path
            )
        return await sendAiResponse(message, chat_id, response)
    if prompt:
        await handleMediaGroup(prompt)
    else:
        session.inputHandler = clb(
            image_id=image_id, mask_id=mask_id,
            __call__=handleMediaGroup
        )
        await message.reply('добавьте описание изображения(всего изображения, а не только закрашенной области), которое хотите получить')


@disp.message_handler(checkBotReaction, includeGroup(False), content_types=["voice"])
async def voiceHandler(message: Message):
    start_time = time.monotonic()
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

    prompt = await aiHear(tmp_path)
    if prompt:
        mid_time = time.monotonic()
        await status_msg.edit_text(
            f"Вы сказали:\n{prompt}"
        )
        warning(f'\n[transcribe-time = {mid_time-start_time}]')
        response = await aiAnswer(session, prompt)
        warning(f'\n[text-processing-time = {time.monotonic()-mid_time}')

        await sendAiResponse(response)
    else:
        return await status_msg.edit_text("Речь не распознана")


@disp.message_handler(
    checkBotReaction, includeGroup(False),
    content_types=["text"]
)
async def messageHandler(message: Message):
    warning("from msg handler")
    if message.text and message.text.startswith("/"):
        if not message.text.startswith("/img"):
            return

    if message.document or message.photo or message.voice:
        return

    keyReset()
    prompt = message.text
    chat_id = message.chat.id
    session = Session.getSession(chat_id)

    if session.inputHandler:
        response = session.inputHandler(prompt)
        if type(response) == CoroutineType:
            response = await response

        await bot.send_message(chat_id=chat_id, text=response)
        return

    if not prompt:
        return

    start_time = time.monotonic()
    response = await aiAnswer(session, prompt)
    warning(f'[text-processing-time = {time.monotonic() - start_time} s]')

    await sendAiResponse(message, chat_id, response)


async def sendAiResponse(message, chat_id, response):
    if response[0] == "image":
        img_file = response[1]
        ext = img_file.split(".")[-1]
        if ext in "png.jpg.jpeg.gif.pjpeg.svg.ico.wbmp.webp".split("."):
            await bot.send_document(chat_id=chat_id, document=open(img_file, "rb"))
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
