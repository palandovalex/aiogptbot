from pathlib import Path
import openai

keys_path = Path(__file__).resolve().parent.parent.joinpath("api_keys.csv")


def getKeys():
    keys = []
    with open(keys_path) as f:
        keys = f.read().split("\n")
    keys = [key.split("//")[0].strip() for key in keys if key]
    print(keys)
    return keys


class KeyRoller:
    def __init__(self):
        self.keys = getKeys()
        self.key_id = 0

    def __iter__(self):
        return self

    def __next__(self):
        key = self.keys[self.key_id]
        self.key_id += 1
        if self.key_id >= len(self.keys):
            self.key_id = 0
        return key

    def reset(self):
        self.keys = getKeys()


KEY_ROLLER = KeyRoller()


def keyReset():
    openai.api_key = next(KEY_ROLLER)
