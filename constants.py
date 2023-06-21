import os
from logging import warning
from aiogram import Bot, Dispatcher
from prompt_loader import PROMPTS
import hashlib
from aiogram.contrib.fsm_storage.memory import MemoryStorage

BOT_HANDLE = "@AiogptentSmithBot"
TMPFS_DIR = os.getenv("TMPFS_DIR")

if not TMPFS_DIR:
    TMPFS_DIR = os.path.join(os.path.dirname(__file__), '../../tmpfs')
warning(f"TMPFS_DIR={TMPFS_DIR}")

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


def loadKey(keyName):
    key = os.environ[keyName]
    key_sha = hashlib.sha1(keyName.encode(encoding="UTF-8", errors="strict"))
    print(f"{keyName} fingerprint: {key_sha.hexdigest()}")
    return key


PROMPTS = PROMPTS

BOT = Bot(loadKey("TG_AUTH_TOKEN"))
DISP = Dispatcher(BOT, storage=MemoryStorage())
