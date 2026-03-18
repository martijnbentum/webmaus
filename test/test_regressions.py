import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webmaus.connector import Response, _main
from webmaus.pipeline import Pipeline


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


if __name__ == '__main__':
    unittest.main()
