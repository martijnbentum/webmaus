# webmaus
simple utility to use webmaus in python to force align an orthographic transcription with speech recordings


## installation

### pip
pip install git+ssh://git@github.com/martijnbentum/webmaus.git

### uv pip
uv pip install git+ssh://git@github.com/martijnbentum/webmaus.git

## usage
```python
from webmaus import pipeline, connector, utils

# webmaus works with iso 639-3 language codes
# utils.languages contains a dictionary with supported languages
# with languague names as keys and iso 639-3 codes as values
language =  utils.languages['dutch']

# files is a list of dictionaries with 'audio_filename' and 'text_filename' keysj
files = [{
    'audio_filename': 'path/to/audio.wav',
    'text_filename': 'path/to/transcription.txt'
}]

output_dir = 'path/to/output/dir'

p = pipeline.Pipeline(files, output_dir, language= language)
p.run()
# output files will be stored in output_dir
# standard format is textgrid

```
