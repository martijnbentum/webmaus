from pathlib import Path

from .connector import run_pipeline
from .utils import languages


DEFAULT_LANGUAGE = languages['dutch']


def align_text(
    transcription,
    audio_filename,
    output_filename,
    language=DEFAULT_LANGUAGE,
    pipe='G2P_MAUS_PHO2SYL',
    preseg='true',
):
    '''Align a transcription string with an audio file and save the result.
    '''
    output_path = Path(output_filename)
    response = run_pipeline(
        audio_filename=audio_filename,
        text_filename=None,
        language=language,
        output_format=_output_format_from_filename(output_path),
        pipe=pipe,
        preseg=preseg,
        text=transcription,
    )
    if response is None or not response.success:
        raise RuntimeError(f'Alignment failed for {audio_filename}')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    response.save_output(response.download(), output_path)
    return str(output_path)


def align_texts(
    transcriptions,
    audio_filenames,
    output_filenames,
    language=DEFAULT_LANGUAGE,
    pipe='G2P_MAUS_PHO2SYL',
    preseg='true',
):
    '''Align multiple transcription strings with matching audio files.
    '''
    if not (
        len(transcriptions) == len(audio_filenames) == len(output_filenames)
    ):
        raise ValueError(
            'transcriptions, audio_filenames, and output_filenames must '
            'have the same length'
        )

    output_files = []
    for transcription, audio_filename, output_filename in zip(
        transcriptions, audio_filenames, output_filenames
    ):
        output_files.append(
            align_text(
                transcription=transcription,
                audio_filename=audio_filename,
                output_filename=output_filename,
                language=language,
                pipe=pipe,
                preseg=preseg,
            )
        )
    return output_files


def _output_format_from_filename(output_filename):
    suffix = output_filename.suffix.lstrip('.')
    if not suffix:
        raise ValueError('output_filename must include a file extension')
    return suffix
