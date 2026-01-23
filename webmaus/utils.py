import time
import progressbar

transcription_set= ['sampa', 'ipa', 'manner', 'place']

languages = {
    'australian english': 'eng-AU',
    'south african afrikaans': 'afr-ZA',
    'albanian': 'sqi-AL',
    'arabic': 'arb',
    'basque (spain)': 'eus-ES',
    'basque (france)': 'eus-FR',
    'catalan': 'cat-ES',
    'czech': 'cze-CZ',
    'dutch': 'nld-NL',
    'british english': 'eng-GB',
    'new zealand english': 'eng-NZ',
    'american english': 'eng-US',
    'estonian': 'ekk-EE',
    'finnish': 'fin-FI',
    'french': 'fra-FR',
    'georgian': 'kat-GE',
    'german': 'deu-DE',
    'swiss german': 'gsw-CH',
    'swiss german (bern)': 'gsw-CH-BE',
    'swiss german (basel)': 'gsw-CH-BS',
    'swiss german (graubünden)': 'gsw-CH-GR',
    'swiss german (st. gallen)': 'gsw-CH-SG',
    'swiss german (zurich)': 'gsw-CH-ZH',
    'haitian creole': 'hat-HT',
    'hungarian': 'hun-HU',
    'icelandic': 'isl-IS',
    'italian': 'ita-IT',
    'japanese': 'jpn-JP',
    'guugu yimithirr': 'gup-AU',
    'luxembourgish': 'ltz-LU',
    'maltese': 'mlt-MT',
    'norwegian': 'nor-NO',
    'persian': 'fas-IR',
    'polish': 'pol-PL',
    'romanian': 'ron-RO',
    'russian': 'rus-RU',
    'slovak': 'slk-SK',
    'spanish': 'spa-ES',
    'swedish': 'swe-SE',
    'thai': 'tha-TH',
    'gungabula': 'guf-AU',
    'unknown': 'und',
}


class LoopETA:
    def __init__(self, total, show_progress=False):
        self.total = total
        self.show_progress = show_progress
        self.eta = None
        self._start = time.time()
        self._bar = None
        self._i = None

        if show_progress:
            self._bar = progressbar.ProgressBar(
                max_value=total,
            )
            self._bar.start()

    def update(self, i):  # i = 1..total
        if self._bar is not None:
            self._bar.update(i)
        self._i = i
        elapsed = time.time() - self._start
        rate = elapsed / max(i, 1)
        self.eta = rate * (self.total - i)

    def finish(self):
        if self._bar is not None:
            self._bar.finish()

    @property
    def pretty_eta(self):
        if self.eta is None:
            return 'N/A'
        return seconds_to_dd_hh_mm_ss(self.eta)

    @property
    def percentage_done(self):
        return self._i / self.total * 100

def seconds_to_dd_hh_mm_ss(seconds):
    seconds = int(seconds)

    days, seconds = divmod(seconds, 24 * 3600)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    return f'{days:02d}:{hours:02d}:{minutes:02d}:{seconds:02d}'

