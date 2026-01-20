from . import audio
from lxml import etree
from pathlib import Path
import requests
from requests.exceptions import ConnectionError
from . import text_utils


PIPELINE_URL = 'https://clarin.phonetik.uni-muenchen.de/'
PIPELINE_URL += 'BASWebServices/services/runPipeline'


class Response:
    '''class to interact with the webmaus api response'''
    def __init__(self, response):
        '''Initialize the Response object to parse the webmaus api response.
        '''
        self.response = response
        self.content = response.content.decode()
        if self.content in ['0', '1', '2']:
            self._handle_load_indicator_response()
        self.success = False
        self.download_link = None
        self.output = None
        self.warnings = None
        if 'downloadLink' in self.content:
            self._handle_pipeline_response()

    def __repr__(self):
        m = self.type 
        if self.type == 'load_indicator':
            m += ' | load: ' + str(self.load)
        if self.type == 'pipeline':
            m += ' | success: ' + str(self.success)
            m += ' | output_filename: ' + self.output_filename
        return m

    def _handle_load_indicator_response(self):
        self.type = 'load_indicator'
        self.load = int(self.content)

    def _handle_pipeline_response(self):
        self.type = 'pipeline'
        self.xml = etree.fromstring(self.content.encode())
        self.success = self.xml.find('success').text == 'true'
        self.download_link = self.xml.find('downloadLink').text
        if self.download_link:
            self.output_filename = Path(self.download_link).name
        self.output = self.xml.find('output').text
        self.warnings = self.xml.find('warnings').text

    def download(self):
        if hasattr(self,'download_output'):
            return self.download_output
        self.download_output = None
        self.download_connection_ok = None
        if self.success and self.type == 'pipeline':
            try:
                self.download_response = requests.get(self.download_link)
                self.download_output = self.download_response.content.decode()
                self.download_connection_ok = True
            except ConnectionError as e:
                print('ConnectionError')#, print(e))
                self.download_connection_ok = False
                self.response.download_connection_error = e
            except Exception as e:
                self.response.download_error = e
        return self.download_output

    def save_output(self, output, filename):
        with open(filename, 'w') as f:
            f.write(output)

    def save_alignment(self, output_directory = '', audio_filename = None,
        start_time = None, end_time = None):
        output = self.download()
        filename = make_output_filename(output_directory, audio_filename,
            'TextGrid', start_time, end_time)
        self.save_output(output, filename)
        return filename


def run_pipeline(audio_filename, text_filename, language, start_time=None,
    end_time=None, output_format = 'TextGrid', pipe = 'G2P_MAUS_PHO2SYL', 
    preseg = 'true', output_symbol = 'ipa', text = None):
    ''' Run the forced alignment pipeline via the webmaus API.
    audio_filename:     path to the audio file
    text_filename:      path to the text file
    language:          language code for the input files
    start_time:        start time in seconds (optional)
    end_time:          end time in seconds (optional)
    output_format:     desired output format (default: 'TextGrid')
    pipe:              processing pipeline to use 
                       (default: 'G2P_MAUS_PHO2SYL')
    preseg:            whether to use pre-segmentation (default: 'true')
    output_symbol:     output symbol set: 'sampa', 'ipa', 'manner', 'place'
    text:              optional text input as string (overrides text_filename)
    '''
    if not output_symbol in ['sampa', 'ipa', 'manner', 'place']:
        raise ValueError('output_symbol must be one of: '
            "'x-sampa', 'ipa', 'manner', 'place'")
    if start_time is None and end_time is None:
        signal = open(audio_filename, 'rb')
    else: signal = audio.load_partial_audio_in_bytes_buffer(
        audio_filename, start_time, end_time, format='WAV')
    if text is not None:
        if text_filename is not None:
            m = f'Warning: text input provided as string, '
            m += f'ignoring text_filename: {text_filename}'
        else:text_filename = '.txt'
        fin = text_utils.string_to_bytes_buffer(text, filename=text_filename)
    else: fin = open(text_filename, 'rb')
        
    files = {'SIGNAL': signal,
        'TEXT': fin }
    data = {'LANGUAGE': language, 'OUTFORMAT': output_format, 'PIPE': pipe,
        'PRESEG': preseg, 'OUTSYMBOL': output_symbol}
    try:
        response = requests.post(PIPELINE_URL, files=files, data=data)
    except ConnectionError:
        _close_files(files)
        return None
    _close_files(files)
    return Response(response)

def run_g2p_maus_phon2syl(audio_filename, text_filename, language, 
    start_time = None, end_time = None, output_format='TextGrid', preseg='true'):
    ''' Run the G2P_MAUS_PHO2SYL pipeline via the webmaus API.
    audio_filename:     path to the audio file
    text_filename:      path to the text file
    language:          language code for the input files
    start_time:        start time in seconds (optional)
    end_time:          end time in seconds (optional)
    output_format:     desired output format (default: 'TextGrid')
    preseg:            whether to use pre-segmentation (default: 'true')
    '''
    return run_pipeline(audio_filename, text_filename, language, start_time,
         end_time, output_format, pipe='G2P_MAUS_PHO2SYL', preseg=preseg)


def make_output_filename(output_directory, audio_filename, output_format,
    start_time=None, end_time=None):
    ''' Create the output filename based on the audio filename and output format.
    '''
    stem = Path(audio_filename).stem
    if start_time is None and end_time is None: pass
    else:
        if start_time is not None:
            stem += f'_s-{int(start_time*1000)}'
            if end_time is not None:
                stem += f'-'
        if end_time is not None:
            if start_time is None:
                stem += '_'
            stem += f'e-{int(end_time*1000)}'
        stem += '-ms'
    return str(Path(output_directory) / f'{stem}.{output_format}')

def _close_files(files):
    for f in files.values():
        f.close()


def create_data_dict(language, output_format = 'TextGrid', 
    pipe = 'G2P_MAUS_PHO2SYL',preseg = True):
    return {'LANGUAGE': language,
            'OUTFORMAT': output_format,
            'PRESEG': preseg,
            'PIPE': pipe,
            }


def _handle_pipeline_run(args):
    output_filename = make_output_filename(args.output_directory, 
        args.audio_filename, args.output_format)
    if Path(output_filename).exists(): 
        print('output exists error')
        return 
    response = run_pipeline(args.audio_filename, args.text_filename,
        args.language, args.start_time, args.end_time, args.output_format, 
        args.pipe, args.preseg)
    if response != None and response.success: 
        output = response.download()
        if output:
            save_output(output, output_filename)
            print('saved:', output_filename)
        else: print('download error')
    else: print('response error')

def _main():
    description = 'interact with bas web services'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('audio_filename', help='path to audio file')
    parser.add_argument('text_filename', help='path to text file')
    parser.add_argument('output_directory', help='directory to save output')
    parser.add_argument('language', help='language code')
    parser.add_argument('--start_time', type=float, help='start time in seconds',
        default=None)
    parser.add_argument('--end_time', type=float, help='end time in seconds',
        default=None)
    parser.add_argument('--output_format', help='output format', 
        default='TextGrid')
    parser.add_argument('--pipe', help='pipeline', 
        default='G2P_MAUS_PHO2SYL')
    parser.add_argument('--preseg', help='presegmentation',
        default='true')
    args = parser.parse_args()
    return _handle_pipeline_run(args)

if __name__ == '__main__':
    _main()
