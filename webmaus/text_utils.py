import io
from pathlib import Path

def string_to_bytes_buffer(input_string, encoding='utf-8', filename = None):
    ''' Convert a string to a bytes buffer.
    input_string:  input string
    encoding:      encoding to use (default: 'utf-8')
    returns:       io.BytesIO object containing the encoded string
    '''
    if filename is not None:
        name = Path(filename).name
    else: name = ''
    byte_data = input_string.encode(encoding)
    buffer = io.BytesIO(byte_data)
    buffer.name = name
    return buffer
