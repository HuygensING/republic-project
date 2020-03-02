def get_textregion_text(textregion):
    text = ''
    for line in textregion['lines']:
        if not 'text' in line or not line['text']:
            continue
        if line['text'][-1] in ['-']:
            text += line['text'][:-1]
        else:
            text += ' ' + line['text']
    return text


