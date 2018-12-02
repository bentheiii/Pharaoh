_ltr_chars = frozenset('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;?@[\\]^_`{|}~ ')


def normalize_RTL(src: str):
    """
    check if a string contains any non-english letters, and if so, return it appended by itself backwards
    This is so it would be easy to read hebrew titles
    """
    if any(c in _ltr_chars for c in src):
        return src + ' (' + src[::-1] + ')'
    return src


_safe_chars = frozenset((' ', '.', '_'))


def safe_filename(src: str):
    """scrub a filename, replace every non alphanumeric character with a whitespace"""
    return "".join(
        (c if c.isalnum() or c in _safe_chars else ' ')
        for c in src).rstrip()
