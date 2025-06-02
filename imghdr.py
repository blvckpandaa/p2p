"""
Простая реализация модуля imghdr для совместимости с python-telegram-bot
"""

def what(file, h=None):
    """
    Упрощенная версия функции для определения типа изображения
    """
    if h is None:
        if isinstance(file, str):
            with open(file, 'rb') as f:
                h = f.read(32)
        else:
            location = file.tell()
            h = file.read(32)
            file.seek(location)
            
    if h.startswith(b'\xff\xd8'):
        return 'jpeg'
    elif h.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    elif h.startswith(b'GIF87a') or h.startswith(b'GIF89a'):
        return 'gif'
    elif h.startswith(b'BM'):
        return 'bmp'
    elif h[0:4] == b'\x00\x00\x01\x00':
        return 'ico'
    elif h.startswith(b'\x00\x00\x00\x0c\x6a\x50\x20\x20\x0d\x0a\x87\x0a'):
        return 'jp2'
    elif h.startswith(b'RIFF') and h[8:12] == b'WEBP':
        return 'webp'
    return None 