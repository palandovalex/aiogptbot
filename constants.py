import os
import hashlib
from aiogram import Bot, Dispatcher

CHATBOT_HANDLE = "@AiogptentSmithBot"  # "@ChatGPTMaster"
TEXT_MODELS = (
    "text-davinci-003,text-curie-001,text-babbage-001,text-ada-001,gpt-3.5-turbo".split(
        ","
    )
)
TRANSCRIBE_MODEL = "whisper-1"

IMG_SIZES = "256x256", "512x512", "1024x1024"
IMG_WORDS = tuple(
    "/img,нарисуй,намалюй,изобрази,начерти,draw,paint,sketch,imaginate".split(",")
)
TMPFS_DIR = os.path.join(os.path.dirname(__file__), "../.tmpfs")


def loadKey(keyName):
    key = os.environ[keyName]
    key_sha = hashlib.sha1(keyName.encode(encoding="UTF-8", errors="strict"))
    print(f"{keyName} fingerprint: {key_sha.hexdigest()}")
    return key


TG_AUTH_TOKEN = loadKey("TG_AUTH_TOKEN")

BOT = Bot(token=TG_AUTH_TOKEN)
DISP = Dispatcher(BOT)
