# import reg


def compare(name, wiki):
    name = name.lower().replace('_(город)', '')
    wiki = wiki[:100].lower()
    i = 0
    for lett in wiki:
        if lett not in 'йцукенгшщзхъфывапролджэячсмитьбю -':
            wiki = wiki[:i] + wiki[i + 1:]
        else:
            i += 1
    if name in wiki:
        return True
    else:
        return False
