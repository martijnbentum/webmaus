import io
from pathlib import Path
import soundfile as sf

def load_partial_audio_in_bytes_buffer(filename, start_time=0.0, end_time=None, 
    format='WAV'):
    '''Load a portion of an audio file into an in-memory bytes buffer.
    filename:           path to the audio file
    start_time:        start time in seconds to load from
    end_time:          end time in seconds to load to (None to load to end)
    Returns: BytesIO buffer containing the audio data
    '''
    signal, sample_rate = load_audio(filename, start_time, end_time)
    buffer = audio_to_buffer(signal, sample_rate, format=format)
    name = Path(filename).name
    buffer.name = name
    print('Created in-memory audio buffer')
    return buffer

def load_audio(filename, start_time=0.0, end_time=None):
    '''Load an audio file and return the audio data and sample rate.
    filename:           path to the audio file
    start_time:        start time in seconds to load from
    end_time:          end time in seconds to load to (None to load to end)

    Returns: numpy array of audio data; sample rate
    '''
    m = f'Loading audio from {filename}, start_time={start_time}, '
    m += f'end_time={end_time}'
    print(m)
    sample_rate = None
    signal = None
    with sf.SoundFile(filename) as f:
        sample_rate = f.samplerate
        if start_time > 0.0:
            f.seek(int(start_time * sample_rate))
        if end_time is not None:
            num_frames = int((end_time - start_time) * sample_rate)
            signal = f.read(frames=num_frames, dtype='float32')
        else:
            signal = f.read(dtype='float32')
    if signal is None:
        raise ValueError(f'Could not load audio signal from file. {filename}')
    return signal, sample_rate

def audio_to_buffer(signal, sample_rate, format='WAV'):
    '''Convert audio signal to an in-memory buffer.
    signal:             numpy array of audio data
    sample_rate:       sample rate of the audio data
    format:            audio format (e.g., 'WAV', 'FLAC')

    Returns: BytesIO buffer containing the audio data
    '''
    buffer = io.BytesIO()
    sf.write(buffer, signal, sample_rate, format=format)
    buffer.seek(0)
    return buffer

    

