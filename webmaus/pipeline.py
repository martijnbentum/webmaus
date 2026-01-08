import threading
import time
from pathlib import Path
from progressbar import progressbar

from .connector import run_pipeline, make_output_filename


class Pipeline:
    def __init__(self, files, output_directory, language, 
        output_format = 'TextGrid', pipe = 'G2P_MAUS_PHO2SYL',
        preseg = 'true', language_dict = None, overwrite = False):
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
        self.overwrite = overwrite

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
            text_filename = entry.get('text_filename', None)
            start_time = entry.get('start_time', None)
            end_time = entry.get('end_time', None)
            text = entry.get('text', None)

            output_file = make_output_filename(self.output_directory,
                audio_filename, self.output_format, start_time, end_time)

            if Path(output_file).exists() and not self.overwrite:
                self.skipped.append((audio_filename, start_time, end_time))
                continue

            ok = self._throttle()
            if not ok: 
                print("Work interrupted due to thread pool restart.")
                break

            thread = threading.Thread(target=self._run_single,
                args=(audio_filename, text_filename, start_time, end_time,
                    text))
            thread.start()
            self.executors.append(thread)
            time.sleep(self.wait_time)
            if len(self.executors) > 0:
                print(f'n executors: {len(self.executors)}')
        print("Waiting for all threads to complete...")
        while len(self.executors) > 0:
            time.sleep(self.wait_time)
            ok = self._throttle()
            if not ok:
                print("Work interrupted due to thread pool restart.")
                break
        print("All audio files processed.")
        m = f'Done: {len(self.done)}, '
        m += f'Skipped: {len(self.skipped)}, '
        m += f'Errors: {len(self.errors)}'
        m += f'\nFiles can be found in : {self.output_directory}'
        print(m)

    def _run_single(self, audio_filename, text_filename, start_time = None, 
        end_time = None, text=None):
        '''Run the forced alignment pipeline for a single audio-text pair.
        audio_filename:     path to the audio file
        text_filename:      path to the text file
        '''
        language = self.language

        if self.language_dict:
            sid = Path(audio_filename).stem
            language = self.language_dict.get(sid, language)

        response = run_pipeline(
            audio_filename=audio_filename,
            text_filename=text_filename,
            start_time=start_time,
            end_time=end_time,
            language=language,
            output_format=self.output_format,
            pipe=self.pipe,
            preseg=self.preseg,
            text=text,
        )

        if response is None:
            self.errors.append(audio_filename)
            return
        if not response.success:
            self.errors.append(audio_filename)
            return

        f = response.save_alignment(output_directory = self.output_directory,
            audio_filename = audio_filename, start_time = start_time,
            end_time = end_time)
        self.done.append([audio_filename, f])

    def _throttle(self):
        '''Throttle the number of concurrent threads to avoid overloading 
        the system.
        checks the number of active threads every second, and if there are
        more than 6 active threads for more than 20 minutes, it restarts
        (assuming some threads are stuck).
        cleans ups finished threads from the executor list.
        '''
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
            

