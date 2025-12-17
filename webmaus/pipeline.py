import threading
import time
from pathlib import Path
from progressbar import progressbar

from .connector import run_pipeline, make_output_filename


class Pipeline:
    def __init__(self, files, output_directory, language, 
        output_format = 'TextGrid', pipe = 'G2P_MAUS_PHO2SYL',
        preseg = 'true', language_dict = None):
        '''Initialize the Pipeline object to handle forced alignment of
        orthographically annotated speech recordings.
        files:              list of dicts with 'audio_filename' and 
                            'text_filename' keys
        output_directory:   directory to save the output files
        language:           language code for the input files
        output_format:      desired output format (default: 'TextGrid')
        pipe:               processing pipeline to use 
                            (default: 'G2P_MAUS_PHO2SYL')
        preseg:             whether to use pre-segmentation (default: 'true')
        language_dict:      optional dict mapping file IDs to language codes
        '''

        self.files = files
        self.output_directory = output_directory
        self.language = language
        self.output_format = output_format
        self.pipe = pipe
        self.preseg = preseg
        self.language_dict = language_dict

        self.done = []
        self.skipped = []
        self.errors = []
        self.executors = []
        self.wait_time = 1

    def __repr__(self):
        m = f'Pipeline(language={self.language}, '
        m += f'format={self.output_format}, '
        m += f'pipe={self.pipe}, '
        m += f'preseg={self.preseg})'
        return m

    def run(self):
        for entry in progressbar(self.files):
            audio_filename = entry['audio_filename']
            text_filename = entry['text_filename']

            output_file = make_output_filename(self.output_directory,
                audio_filename, self.output_format)

            if Path(output_file).exists():
                self.skipped.append(audio_filename)
                continue

            ok = self._throttle()
            if not ok: break

            thread = threading.Thread(target=self._run_single,
                args=(audio_filename, text_filename))
            thread.start()
            self.executors.append(thread)

            time.sleep(self.wait_time)

    def _run_single(self, audio_filename, text_filename):
        language = self.language

        if self.language_dict:
            sid = Path(audio_filename).stem
            language = self.language_dict.get(sid, language)

        response = run_pipeline(
            audio_filename=audio_filename,
            text_filename=text_filename,
            language=language,
            output_format=self.output_format,
            pipe=self.pipe,
            preseg=self.preseg,
        )

        if response is None:
            self.errors.append(audio_filename)
            return
        if not response.success:
            self.errors.append(audio_filename)
            return

        response.save_alignment(output_directory = self.output_directory)
        self.done.append([audio_filename, response.output_filename])

    def _throttle(self):
        self.executors = [e for e in self.executors if e.is_alive()]
        self.start = time.time()
        do_restart = False
        while len(self.executors) > 6:
            time.sleep(1)
            self.executors = [e for e in self.executors if e.is_alive()]
            if time.time() - self.start > 1200:
                print("Timeout waiting for threads to complete.")
                do_restart = True
                break
        if do_restart:
            print("Restarting thread pool...")
            self.executors = []
            time.sleep(3)
            self.run()
            return False
        return True
            

