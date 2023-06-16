from aiogram.types import (
    InlineKeyboardButton as IKbButton,
    InlineKeyboardMarkup as IKbMarkup,
    CallbackQuery,
)
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher import FSMContext
from aiogram import types, executor
import logging
from constants import BOT as bot, DISP as dp
from prompts_loader import PROMPTS
from typing import Sequence, Dict, Tuple


logging.basicConfig(level=logging.INFO)
pagination_callback = CallbackData("pagination", "page")
pagination_chats: Dict[int, Tuple[CallbackData, Sequence]] = {}


def get_item_nums(page_num: int, items: Sequence, limit=10) -> tuple:
    start_index = limit * (page_num - 1)
    end_index = limit * page_num
    if end_index > len(items) - 1:
        end_index = len(items) - 1

    has_prev = page_num > 1
    has_next = end_index < len(items) - 1
    result_indexes = [i for i in range(start_index, end_index)]
    return has_prev, has_next, result_indexes


async def get_keyboard(
    page: int, itemsCallbackData: CallbackData, items: Sequence
) -> IKbMarkup:
    has_prev, has_next, page_indexes = get_item_nums(page, items)
    keyboard = IKbMarkup(row_width=1)
    buttons = []
    print(page_indexes)
    for index in page_indexes:
        buttons.append(
            IKbButton(
                f"{index+1}. {items[index]}",
                callback_data=itemsCallbackData.new(index=index),
            )
        )
    keyboard.add(*buttons)

    last_row = []
    if has_prev:
        prevPageCallback = pagination_callback.new(page=page - 1)
        prev_page_button = IKbButton("<< Prev", callback_data=prevPageCallback)
        last_row.append(prev_page_button)

    if has_next:
        nextPageCallback = pagination_callback.new(page=page + 1)
        next_page_button = IKbButton("Next >>", callback_data=nextPageCallback)
        last_row.append(next_page_button)

    keyboard.row(*last_row)
    return keyboard


async def send_items_list(
    chat_id: int,
    itemsCallbackData: CallbackData,
    items_list: Sequence,
    page_num: int = 1,
):
    pagination_chats[chat_id] = (itemsCallbackData, items_list)
    keyboard = await get_keyboard(page_num, itemsCallbackData, items_list)
    await bot.send_message(chat_id, "List of items:", reply_markup=keyboard)


@dp.callback_query_handler(pagination_callback.filter())
async def pagination_handler(
    callback_query: CallbackQuery, callback_data: dict, state: FSMContext
):
    chat_id = callback_query.message.chat.id
    try:
        itemsCallbackData, items_list = pagination_chats.get(chat_id)
    except TypeError:
        await bot.send_message(chat_id, "session not found")

    page = callback_data["page"]
    page = int(page)
    keyboard = await get_keyboard(page, itemsCallbackData, items_list)
    await bot.edit_message_reply_markup(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=keyboard,
    )
    await bot.answer_callback_query(callback_query_id=callback_query.id)


if __name__ == "__main__":
    prompts = list(PROMPTS.keys())
    print(prompts)
    sorted(prompts)
    items_base = [i for i in range(len(prompts))]
    testCallbackHandeler = CallbackData("test_callback", "index")

    @dp.message_handler(Command("list"))
    async def show_items_list_command_handler(
        message: types.Message, state: FSMContext
    ):
        await send_items_list(
            chat_id=message.chat.id,
            itemsCallbackData=testCallbackHandeler,
            items_list=prompts,
        )

    @dp.callback_query_handler(testCallbackHandeler.filter())
    async def show_test_reaction(
        callback_query: CallbackQuery, callback_data: dict, state: FSMContext
    ):
        chat_id = callback_query.message.chat.id
        await bot.send_message(chat_id, f"{callback_data}")

    print("running bot")
    executor.start_polling(dp)
