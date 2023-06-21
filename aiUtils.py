import asyncio
from logging import warning
from openai.error import RateLimitError
import openai
from session import AioSession as Session
from constants import IMG_WORDS, TRANSCRIBE_MODEL
import os
from typing import Tuple
from constants import TMPFS_DIR

import aiohttp
from PIL import Image
from io import BytesIO

import uuid
import mimetypes


IMAGING_HELP_TEXT = 'Для использования функции генерации изображений вы можете' + \
' использовать активационную фразу:\n' + f"{IMG_WORDS}\n\n\n" + \
'Также вы можете дать мне изображение, чтобы я создал похожее, достаточно просто его прислать мне.\n\n' + \
'Вы также можете дать мне задание для обработки изображений. ' + \
'Дайте мне изображение в формате png с зонами, закрашенными "прозрачным" ' + \
'и описание изображения, которое должно получиться.\n\n' + \
'Если хотите, можно улучшить результат. Для этого дайте мне группу из ' + \
'изображения и маски(в этом же порядке), а потом дайте описание изображения, ' + \
'которое хотите получить. дадите мне отдельно изображение, и отдельно ' + \
'маску(изображение с прозрачностью, в котором закрашены все зоны интереса).'


async def ogg_to_mp3(input_file, output_file):
    await asyncio.subprocess.create_subprocess_exec(
        'ffmpeg', '-i', input_file,
        '-vn', '-ar', '44100', '-ac', '2', '-ab', '192k', '-f', 'mp3',
        output_file,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
        )


async def aiAnswer(session: Session, prompt) -> Tuple:
    try:
        if prompt.lower().startswith(IMG_WORDS):
            return await aiDraw(session, prompt)
        else:
            response = await aiText(session, prompt)
            return 'text', response

    except RateLimitError:
        return 'text', 'Server is overloaded'


async def aiHear(file_path):
    try:
        await ogg_to_mp3(file_path, file_path+".mp3")
        with open(file_path+'.mp3', 'rb') as f:
            transcript = await openai.Audio.atranscribe(TRANSCRIBE_MODEL, f)
        return transcript['text']
    except Exception as e:
        warning(e)
        return 'text', 'что то пошло не так. Возможно запись слишком длинная, или формат не поддерживается.'
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(file_path+'.mp3'):
            os.remove(file_path+'.mp3')


async def aiDraw(session: Session, prompt: str, image_path=None, mask_path=None):
    try:
        prompt = prompt.replace('/img', '')
        warning('from aiDraw')

        if not prompt and not image_path:
            
            return 'text', IMAGING_HELP_TEXT

        size = session.getOpt('image_size').split('x')
        size = tuple(map(int, size))

        image = prepere_image(image_path, size) if image_path else None
        mask = prepere_image(mask_path, size) if mask_path else None

        if image and not prompt:
            response = await openai.Image.acreate_variation(
                image=image,
                n=1,
                size=session.getOpt('image_size')
                )
        elif image_path and prompt:
            response = await openai.Image.acreate_edit(
                image=image,
                mask=mask,
                prompt=prompt,
                n=1,
                size=session.getOpt('image_size')
                )
        else:
            response = await openai.Image.acreate(
                prompt=prompt,
                n=1,
                size=session.getOpt('image_size')
            )

        url = response['data'][0]['url']
        try:
            return await downloadFile(url)
        except Exception as e:
            warning(e)
            return ('text', url)
    finally:
        if image_path:
            os.remove(image_path)
        if mask_path:
            os.remove(mask_path)


async def aiText(session: Session, prompt):
    session.addMessage('user', prompt)
    context = session.getContext()
    model = session.getOpt("model")

    chatModels = ('gpt-3.5-turbo')
    if model in chatModels:
        completion = await openai.ChatCompletion.acreate(
                model=model, messages=context)
    else:
        prompt, stop = renderPrompt(model, context)
        completion = await openai.Completion.acreate(
                model=model, prompt=prompt, stop=stop)

    for choice in completion.choices:
        warning(f"\nchoise:\n{choice.message.content}\n")

    response = completion.choices[0].message.content
    session.addMessage('assistant', response)
    return response


def renderPrompt(model, context):
    prompt = ''
    for msg in context:
        prompt += msg["role"] + ' message\n'
        prompt += msg["content"] + '<!stop>\n'
    stop = ['<!stop>\n']

    return (prompt, stop)


def correct_resize(image_path, size):
    with Image.open(image_path) as image:

        old_width, old_height = image.size
        old_relation = old_width/old_height
        width, height = size
        relation = width/height
        if old_relation>relation:
            new_size = width, int(old_height*width/old_width)
        else:
            new_size = int(old_width*height/old_height), height

        print(f"old size = {image.size}, new size = {new_size}")
        image = image.resize(new_size, Image.ANTIALIAS)

        new_image = Image.new("RGBA", size)
        new_image.paste(
            image, ((size[0] - image.size[0]) // 2, (size[1] - image.size[1]) // 2)
        )
        return new_image


def prepere_image(image_path, size):
    image = correct_resize(image_path, size)

    #image = image.resize(size)

    b_io = BytesIO()
    image.save(b_io, format='png')
    image = b_io.getvalue()
    return image


async def downloadFile(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, raise_for_status=True) as response:
            if response.status == 200:
                content_type = response.headers['Content-Type']
                ext = mimetypes.guess_extension(content_type.split(';')[0])
                filename = str(uuid.uuid4()) + ext
                filename = os.path.join(TMPFS_DIR, 'downloads', filename)
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, 'wb') as f:
                    async for chunk in response.content.iter_chunked(1024):
                        f.write(chunk)
                return 'image', filename
    warning("can't download image, return url")
    return 'text', url
