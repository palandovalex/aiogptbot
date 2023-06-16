from logging import warning
import openai
from openai.error import RateLimitError
from session import AioSession as Session
from constants import IMG_WORDS, TRANSCRIBE_MODEL
import os
import subprocess
from constants import TMPFS_DIR

import requests
import uuid
import mimetypes

def ogg_to_mp3(input_file, output_file):
    subprocess.call(['ffmpeg', '-i', input_file, '-vn', '-ar', '44100', '-ac', '2', '-ab', '192k', '-f', 'mp3', output_file])


def aiAnswer(session:Session, prompt):
    try:
        if prompt.lower().startswith(IMG_WORDS):
            return aiDraw(session, prompt)
        else:
            response = aiText(session, prompt)
            return 'text', response

    except RateLimitError:
        return 'text', 'Server is overloaded'


def aiHear(file_path):

    try:
        ogg_to_mp3(file_path, file_path+".mp3")
        with open(file_path+'.mp3','rb') as f:
            transcript = openai.Audio.transcribe(TRANSCRIBE_MODEL, f)
        return transcript['text']
    except Exception as e:
        warning(e)
        return None
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(file_path+'.mp3'):
            os.remove(file_path+'.mp3')


def aiDraw(session:Session, prompt: str):
    prompt = prompt.replace('/img','').strip()
    if not prompt:
        return 'text', 'нечего рисовать'
    warning('from openAImage')
    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size=session.getOpt('image_size')
    )
    url = response['data'][0]['url']
    try:
        return downloadFile(url)

    except Exception as e:
        warning(e)
        return ('text', url)





def aiText(session: Session, prompt):
    session.addMessage('user', prompt)
    context = session.getContext()
    model = session.getOpt("model")

    
    # warning(openai.Model.list())

    chatModels = ('gpt-3.5-turbo')
    if model in chatModels:
        completion = openai.ChatCompletion.create(model=model, messages=context)
    else:
        prompt, stop = renderPrompt(model, context)
        completion = openai.Completion.create(model=model, prompt=prompt, stop=stop)
        
    for choice in completion.choices:
        warning(f"\nchoise:\n{choice.message.content}\n")

    response = completion.choices[0].message.content
    session.addMessage('assistant', response)
    return response


def renderPrompt(model, context):
    prompt = ''
    for msg in context:
        prompt+= msg["role"] + ' message\n'
        prompt+= msg["content"] + '<!stop>\n'
    stop = ['<!stop>\n']

    return (prompt, stop)


def downloadFile(url):
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        content_type = r.headers['Content-Type']
        ext = mimetypes.guess_extension(content_type.split(';')[0])
        filename = str(uuid.uuid4()) + ext
        filename = os.path.join(TMPFS_DIR, 'downloads', filename)
        warning(filename)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'wb') as f:
            r.raw.decode_content = True
            for chunk in r:
                f.write(chunk)
        return 'image', filename
    warning("can't download image, return url")
    return 'text', url
