import requests
from pathlib import Path
from lxml import etree
from requests.exceptions import ConnectionError


PIPELINE_URL = 'https://clarin.phonetik.uni-muenchen.de/'
PIPELINE_URL += 'BASWebServices/services/runPipeline'


class Response:
    '''class to interact with the webmaus api response'''
    def __init__(self, response):
        '''Initialize the Response object to parse the webmaus api response.
        '''
        self.content = response.content.decode()
        self.success = False
        self.download_link = None
        self.output = None
        self.warnings = None

        if 'downloadLink' in self.content:
            self._parse_pipeline()

    def _parse_pipeline(self):
        xml = etree.fromstring(self.content.encode())
        self.success = xml.find('success').text == 'true'
        self.download_link = xml.find('downloadLink').text
        self.output = xml.find('output').text
        self.warnings = xml.find('warnings').text


def run_pipeline(audio_filename, text_filename, language, 
    output_format = 'TextGrid', pipe = 'G2P_MAUS_PHO2SYL', preseg = 'true'):
    ''' Run the forced alignment pipeline via the webmaus API.
    audio_filename:     path to the audio file
    text_filename:      path to the text file
    language:          language code for the input files
    output_format:     desired output format (default: 'TextGrid')
    pipe:              processing pipeline to use 
                       (default: 'G2P_MAUS_PHO2SYL')
    preseg:            whether to use pre-segmentation (default: 'true')
    '''
    files = {'SIGNAL': open(audio_filename, 'rb'),
        'TEXT': open(text_filename, 'rb') }
    data = {'LANGUAGE': language, 'OUTFORMAT': output_format, 'PIPE': pipe,
        'PRESEG': preseg}
    try:
        response = requests.post(PIPELINE_URL, files=files, data=data)
    except ConnectionError:
        _close_files(files)
        return None
    _close_files(files)
    return Response(response)


def make_output_filename(output_directory, audio_filename, output_format):
    ''' Create the output filename based on the audio filename and output format.
    '''
    stem = Path(audio_filename).stem
    return str(Path(output_directory) / f'{stem}.{output_format}')

def _close_files(files):
    for f in files.values():
        f.close()

