import threading
import time
from pathlib import Path
from progressbar import progressbar

from .connector import run_pipeline, make_output_filename
from . import utils


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
        self.infos = []
        self._max_concurrent_executors = 9
        self.executors = []
        self.output_directories = set()
        self.wait_time = 1
        self._stop_run = False
        self.running = False
        self.status_done = False

    def __repr__(self):
        m = f'Pipeline(language={self.language}, '
        m += f'format={self.output_format}, '
        m += f'pipe={self.pipe}, '
        m += f'preseg={self.preseg})'
        return m

    def run(self):
        self._stop_run = False
        self.running = True
        self.status_done = False
        self.run_thread = threading.Thread(target=self._run)
        self.run_thread.start()

    def stop(self):
        self._stop_run = True
        self.running = False

    @property
    def eta_seconds(self):
        return self.tracker.pretty_eta()
        
    @property
    def eta(self):
        t = f'ETA: {self.tracker.pretty_eta}\n'
        t += f'working executors: {len(self.executors)}\n'
        t += f'files done: {len(self.done)}\n'
        t += f'files skipped: {len(self.skipped)}\n'
        t += f'errors: {len(self.errors)}\n'
        t += f'at file number: {self.tracker._i} of {self.tracker.total}\n'
        t += f'percentage done: {self.tracker.percentage_done:.2f}%\n'
        t += f'running: {self.running}\n'
        t += f'status done: {self.status_done}\n'
        print(t)

    def _run(self, show_progress = False):
        self.tracker = utils.LoopETA(total=len(self.files), 
            show_progress=show_progress)
        for index, entry in enumerate(self.files):
            self.tracker.update(index + 1)
            if self._stop_run: 
                print("Work interrupted by user, started jobs will complete.")
                break
            audio_filename = entry['audio_filename']
            text_filename = entry.get('text_filename', None)
            start_time = entry.get('start_time', None)
            end_time = entry.get('end_time', None)
            text = entry.get('text', None)
            output_directory = entry.get('output_directory', None)
            if output_directory is None:
                output_directory = self.output_directory
            self.output_directories.add(output_directory)
            
            output_file = make_output_filename(output_directory,
                audio_filename, self.output_format, start_time, end_time)

            if Path(output_file).exists() and not self.overwrite:
                self.skipped.append((audio_filename, start_time, end_time,
                    str(output_file)))
                self.infos.append(make_info(audio_filename, start_time,
                    end_time, str(output_file), 'skipped'))
                continue

            ok = self._throttle()
            if not ok: 
                print("Work interrupted due to thread pool restart.")
                break

            thread = threading.Thread(target=self._run_single,
                args=(audio_filename, text_filename, start_time, end_time,
                    text, output_directory))
            thread.start()
            self.executors.append(thread)
            time.sleep(self.wait_time)
        print("Waiting for all threads to complete...")
        while len(self.executors) > 0:
            time.sleep(self.wait_time)
            ok = self._throttle()
            if not ok:
                print("Work interrupted due to thread pool restart.")
                break

        if index + 1 == self.tracker.total:
            self.status_done = True
        print("audio files processed.")
        m = f'Done: {len(self.done)}, '
        m += f'Skipped: {len(self.skipped)}, '
        m += f'Errors: {len(self.errors)}'
        m += f'\nFiles can be found in : {self.output_directories}'
        m += f'\nfiles processed: {index + 1} of {self.tracker.total}'
        m += f'\nstatus done: {self.status_done}'
        print(m)
        self.running = False

    def _run_single(self, audio_filename, text_filename, start_time = None, 
        end_time = None, text=None, output_directory = None):
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

        if response is None or not response.success:
            self.errors.append((audio_filename, start_time, end_time))
            self.infos.append(make_info(audio_filename, start_time, end_time,
                None, 'error'))
            return

        if output_directory is None:
            output_directory = self.output_directory
        f = response.save_alignment(output_directory = output_directory,
            audio_filename = audio_filename, start_time = start_time,
            end_time = end_time)
        self.done.append((audio_filename, start_time, end_time, f))
        self.infos.append(make_info(audio_filename, start_time, end_time,
            f, 'done'))

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
        while len(self.executors) >= self._max_concurrent_executors:
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


    @property
    def done_infos(self):
        infos = [info for info in self.infos if info['status'] == 'done']
        return infos 

    @property
    def error_infos(self):
        infos = [info for info in self.infos if info['status'] == 'error']
        return infos

    @property
    def skipped_infos(self):
        infos = [info for info in self.infos if info['status'] == 'skipped']
        return infos
        



    
            

def make_info(audio_filename, start_time, end_time, output_file, status):
    info = {
        'audio_filename': audio_filename,
        'start_time': start_time,
        'end_time': end_time,
        'output_file': output_file,
        'status': status,
        'timestamp': readable_timestamp(),
        'time': time.time(),
        }
    return info

def readable_timestamp():
    return time.strftime('%a %d %b %Y, %H:%M', time.localtime())


