from logging import warning
from typing import Any, TypedDict, Literal, Callable

from constants import IMG_SIZES, TEXT_MODELS

from session_storage import JsonSessionStorage

MODELS = TEXT_MODELS


class SessionMessage(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str


MsgHistory = list[SessionMessage]
Personality = str


def save_decor(func):
    def wraper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
            self.save()
            return result
        finally:
            self.inputHandler = None

    return wraper


class AioSession:
    def __init__(self, session_id):
        self.session_id: int = session_id
        self.inputHandler: Callable | None = None
        self.message_histories: dict[str, MsgHistory] = {"Смитт": [], "Neo": []}
        self._model = "gpt-3.5-turbe"
        self._history_length: int = 15

        self.personalities: dict[str, str] = {
            "empty": "",
            "Смитт": "Answer strictly, straightforwardly, briefly.\n",
            "Neo": "Answer like professional programmer, and wrap code fragments like this:\n<!CODE>languageName\ncodeFragment()\n<!ENDCODE>\n",
        }

        self._personality: str = "Смитт"

        self._model: str = MODELS[4]
        self._image_size: str = "512x512"

        optHandlers = {
            "model": MODELS,
            "image_size": IMG_SIZES,
            "personality": self.personalities,
            "history_length": "must be integer betwin 0 and 50",
        }

        for key, val in optHandlers.items():
            optHandler = getattr(self, "set_" + key)
            optHandlers[key] = [val, optHandler]
        self.optHandlers = optHandlers

    def optKeys(self):
        return self.getOptHandlers().keys()

    def getOptHandlers(self) -> dict[str, tuple[Any, Callable]]:
        return self.optHandlers

    def getOpt(self, optKey):
        if optKey in self.getOptHandlers().keys():
            return self.__getattribute__("_" + optKey)
        raise RuntimeError("incorrect optKey")

    def getHistory(self):
        return self.message_histories[self._personality]

    @save_decor
    def remove_personality(self, name):
        if name == "empty":
            return "нельзя удалить пустую персональность"
        if name in self.personalities.keys():
            pers = self.personalities[name]
            del self.personalities[name]
            del self.message_histories[name]
            if len(self.personalities) == 0:
                self.personalities["empty"] = ""
                self.message_histories[""] = []
                return f"все персональности удалены.\nТекущая персональность - empty (не хранит память)."
            return f"персональность [{name}] удалена"
        else:
            return f'персональность "{name}" не найдена'

    @save_decor
    def addMessage(self, role, message):
        msg = SessionMessage(role=role, content=message)
        hist = self.getHistory()
        hist.append(msg)
        if len(hist) > self._history_length:
            hist.pop(0)

    def getContext(self):
        pers = self.personalities[self._personality]
        hist = self.getHistory()
        message: SessionMessage = hist[-1].copy()

        if not pers:
            return [message]

        context = hist[:-1]
        sys_msg = SessionMessage(role="system", content=pers)
        context.append(sys_msg)
        context.append(message)
        return context

    @save_decor
    def cleanHistory(self, target):
        if target == "cleanAll":
            for hist in self.message_histories.values():
                del hist[:]
            result = "вся история сообщений сброшена"
        else:
            hist = self.getHistory()
            del hist[:]
            result = "история сообщений текущей персональности сброшена"
        self.save()
        return result

    def changeOptions(self, value):
        if not self.inputHandler:
            raise RuntimeError("empty Input state")
        try:
            self.inputHandler(value)

            self.save()
            return "updated"
        except Exception as e:
            print(e)
            return str(e)

    def save(self):
        # ensure state to be equal to settings
        if len(self.getHistory()) > self._history_length:
            for hist in self.message_histories.values():
                hist = hist[-self._history_length :]

        sessionData = {}
        for key, value in self.__dict__.items():
            if key not in ("optHandlers", "inputHandler"):
                sessionData[key] = value

        STORAGE.save(self.session_id, sessionData)

    @classmethod
    def getSession(cls, session_id) -> "AioSession":
        return STORAGE.getSession(session_id=session_id)

    @classmethod
    def fromData(cls, session_id: int, data: dict):
        session = AioSession(session_id)
        session.__dict__.update(data)
        return session

    @save_decor
    def setDefault(self):
        default = AioSession(-1)
        for optKey, optValue in default.getOptItems():
            setattr(self, optKey, optValue)

        self.save()
        return "ваши настройки сброшены"

    @save_decor
    def set_history_length(self, v: int):
        if v > 30 or v < 0:
            raise ValueError("длинна истории должна быть от 0 до 30 сообщений")
        if v < self._history_length:
            for history in self.message_histories:
                history = history[-v:]
        self._history_length = v

    @save_decor
    def update_personality(self, name: str, value: str):
        if not name:
            return "нельзя использовать пустое название персональности"
        if value.isdigit():
            return "персональность не может состоять из одних чисел"
        result = f'создана новая персональность c именем "{name}"'
        if name in self.personalities.keys():
            result = f'персональность "{name}" изменена,'

        result += f", значение: [{value}]"

        self.personalities[name] = value
        self.message_histories[name] = []
        self._personality = name
        return result + f"\n текущая персональность: {name}"

    @save_decor
    def set_personality(self, name: str):
        # проверяем точное совпадение названия
        if name in self.personalities.keys():
            self._personality = name
            return f"Текущая персональность: {[name]}"

        candidates = []
        # если пользователь не ввёл точное название персонельности, то ищем похожие
        for persName in self.personalities.keys():
            if persName.startswith(name):
                candidates.append(persName)
        # если найдена одна похожая персональность - устанавливаем её
        if len(candidates) == 1:
            self._personality = candidates[0]
            return f"Текущая персональность: {candidates[0]}"
        # иначе возвращаем причину неудачи
        elif len(candidates) > 1:
            return f"Слишком много похожих кандидатов: {candidates}"
        return f"Персональность {name} не найдена"

    @save_decor
    def set_model(self, v):
        if v not in MODELS:
            ValueError(f"Model must be one of this: {MODELS}")
        self._model = v

    @save_decor
    def set_image_size(self, v):
        if v not in IMG_SIZES:
            ValueError(f"size must be one of {IMG_SIZES}")
        self._imageSize = v

    @save_decor
    def getOptItems(self):
        return {item for item in self.__dict__.items() if item[0].startswith("_")}


STORAGE = JsonSessionStorage(Session=AioSession)

DEFAULT = AioSession(-1)
print("DEFAULTS")
print(f"model of engine: { DEFAULT._model }")
print(f"image size: { DEFAULT._image_size }")
print(f"history length: { DEFAULT._history_length }")
print(f"bot_personality: { DEFAULT._personality }")
print(f"personalities: { DEFAULT.personalities }")
