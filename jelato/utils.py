def summarize(text, max_length):
    if len(text) <= max_length:
        return text
    else:
        return text[0:max_length].strip() + '...'
