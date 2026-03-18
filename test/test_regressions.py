import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webmaus.connector import Response, _main
from webmaus.pipeline import Pipeline
from webmaus.simple_align import DEFAULT_LANGUAGE, align_text, align_texts


class DummyHTTPResponse:
    def __init__(self, content):
        self.content = content


class ResponseTests(unittest.TestCase):
    def test_error_xml_is_parsed_without_crashing(self):
        response = Response(
            DummyHTTPResponse(
                b'<root><success>false</success><output>err</output></root>'
            )
        )

        self.assertEqual(response.type, 'pipeline')
        self.assertFalse(response.success)
        self.assertIsNone(response.download_link)
        self.assertIn('pipeline', repr(response))

    def test_load_indicator_still_reports_same_type(self):
        response = Response(DummyHTTPResponse(b'1'))

        self.assertEqual(response.type, 'load_indicator')
        self.assertEqual(response.load, 1)
        self.assertFalse(response.success)

    def test_save_alignment_uses_requested_output_format(self):
        response = Response(
            DummyHTTPResponse(
                b'<root><success>true</success>'
                b'<downloadLink>http://example.com/a.TextGrid</downloadLink>'
                b'<output>ok</output><warnings/></root>'
            )
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(response, 'download', return_value='alignment'):
                filename = response.save_alignment(
                    output_directory=tmpdir,
                    audio_filename='clip.wav',
                    output_format='json',
                )

            path = Path(filename)
            self.assertEqual(path.suffix, '.json')
            self.assertEqual(path.read_text(), 'alignment')


class PipelineTests(unittest.TestCase):
    def test_empty_pipeline_finishes_cleanly(self):
        pipeline = Pipeline([], 'out', 'eng-US')

        pipeline._run()

        self.assertTrue(pipeline.status_done)
        self.assertFalse(pipeline.running)
        self.assertEqual(pipeline.tracker.percentage_done, 0)
        self.assertEqual(pipeline.eta_seconds, 0)

    def test_run_single_passes_output_format_to_save_alignment(self):
        pipeline = Pipeline([], 'out', 'eng-US', output_format='json')
        response = unittest.mock.Mock()
        response.success = True
        response.save_alignment.return_value = 'out/clip.json'

        with patch('webmaus.pipeline.run_pipeline', return_value=response):
            pipeline._run_single('clip.wav', 'clip.txt')

        response.save_alignment.assert_called_once_with(
            output_directory='out',
            audio_filename='clip.wav',
            start_time=None,
            end_time=None,
            output_format='json',
        )
        self.assertEqual(pipeline.done[0][-1], 'out/clip.json')


class CLITests(unittest.TestCase):
    def test_main_parses_arguments_and_calls_handler(self):
        with patch('webmaus.connector._handle_pipeline_run', return_value='ok') as handle:
            with patch('sys.argv', [
                'webmaus.connector',
                'audio.wav',
                'text.txt',
                'out',
                'eng-US',
            ]):
                result = _main()

        self.assertEqual(result, 'ok')
        handle.assert_called_once()


class SimpleAlignmentTests(unittest.TestCase):
    def test_align_text_uses_dutch_default_and_writes_requested_file(self):
        response = unittest.mock.Mock()
        response.success = True
        response.download.return_value = 'alignment'

        with tempfile.TemporaryDirectory() as tmpdir:
            output_filename = Path(tmpdir) / 'result.TextGrid'
            with patch('webmaus.simple_align.run_pipeline',
                return_value=response) as run:
                result = align_text(
                    transcription='dit is een test',
                    audio_filename='clip.wav',
                    output_filename=output_filename,
                )

        self.assertEqual(result, str(output_filename))
        run.assert_called_once_with(
            audio_filename='clip.wav',
            text_filename=None,
            language=DEFAULT_LANGUAGE,
            output_format='TextGrid',
            pipe='G2P_MAUS_PHO2SYL',
            preseg='true',
            text='dit is een test',
        )
        response.save_output.assert_called_once_with(
            'alignment',
            output_filename,
        )

    def test_align_texts_handles_multiple_inputs(self):
        with patch('webmaus.simple_align.align_text',
            side_effect=['a.TextGrid', 'b.TextGrid']) as align:
            result = align_texts(
                transcriptions=['a', 'b'],
                audio_filenames=['a.wav', 'b.wav'],
                output_filenames=['a.TextGrid', 'b.TextGrid'],
                language='eng-US',
            )

        self.assertEqual(result, ['a.TextGrid', 'b.TextGrid'])
        self.assertEqual(align.call_count, 2)

    def test_align_texts_validates_input_lengths(self):
        with self.assertRaises(ValueError):
            align_texts(
                transcriptions=['a'],
                audio_filenames=['a.wav', 'b.wav'],
                output_filenames=['a.TextGrid'],
            )


if __name__ == '__main__':
    unittest.main()
