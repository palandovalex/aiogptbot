import os


PROMPTS = {}

lambdas = {
    'concat': lambda pers_name, pers, arg: (pers_name, pers + arg),
    'ident': lambda pers_name, pers, arg: (pers_name, pers),
    'replace': lambda pers_name, pers, arg: (pers_name.replace(*arg.split('|')), pers.replace(*arg.split('|'))),
}

prompts_path = os.path.join(os.path.dirname(__file__), './prompts2.csv')
with open(prompts_path) as csvfile:

    current_lambda = lambdas['ident']
    arg = None
    next(csvfile)
    for line in csvfile:
        pers_name, prompt = line.split('","', 1)
        prompt = prompt[:-2].replace('""', '"')
        pers_name = pers_name[1:]
        if pers_name.startswith('fn'):
            current_lambda = lambdas.get(pers_name.split(' ')[1])
            arg = prompt
        elif pers_name == 'act':
            current_lambda = lambdas['ident']
            arg = None
        else:
            pers_name, prompt = current_lambda(pers_name, prompt, arg)
            PROMPTS[pers_name] = prompt


if __name__ == '__main__':

    count = 3
    keys = list(PROMPTS.keys())[:count]
    keys = keys + list(PROMPTS.keys())[25: 35]
    for key in keys:
        print(key)
        print(PROMPTS[key])

