"""
Unit tests for new audio conversions (AIFF, WMA, AC3, AMR, Speed)
and offline Speech-to-Text transcription (TXT, SRT, DOCX).
"""
import unittest
import tempfile
from pathlib import Path
import docx

from shiftdrop.core.ffmpeg_helper import run_ffmpeg
from shiftdrop.core.audio_ops import convert_audio, change_audio_speed
from shiftdrop.core.transcribe_ops import (
    transcribe_to_txt, transcribe_to_srt, transcribe_to_docx,
    format_timestamp, transcribe_audio_segments
)
from shiftdrop.core.dispatcher import execute_action


class TestTranscribeAndAudio(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.tmp_dir.name)

        # Generate a 2-second sine wave audio file
        self.sample_wav = self.dir_path / "test_audio.wav"
        run_ffmpeg([
            "-f", "lavfi",
            "-i", "sine=frequency=440:duration=2",
            str(self.sample_wav)
        ])

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_format_timestamp(self):
        self.assertEqual(format_timestamp(65.5, srt_format=False), "00:01:05")
        self.assertEqual(format_timestamp(65.5, srt_format=True), "00:01:05,500")

    def test_convert_audio_aiff(self):
        out_aiff = convert_audio(self.sample_wav, "aiff")
        self.assertTrue(out_aiff.exists())
        self.assertGreater(out_aiff.stat().st_size, 1000)

    def test_convert_audio_wma(self):
        out_wma = convert_audio(self.sample_wav, "wma")
        self.assertTrue(out_wma.exists())
        self.assertGreater(out_wma.stat().st_size, 500)

    def test_convert_audio_ac3(self):
        out_ac3 = convert_audio(self.sample_wav, "ac3")
        self.assertTrue(out_ac3.exists())
        self.assertGreater(out_ac3.stat().st_size, 500)

    def test_convert_audio_amr(self):
        out_amr = convert_audio(self.sample_wav, "amr")
        self.assertTrue(out_amr.exists())
        self.assertGreater(out_amr.stat().st_size, 100)

    def test_change_audio_speed_fast(self):
        out_fast = change_audio_speed(self.sample_wav, speed=1.25)
        self.assertTrue(out_fast.exists())
        self.assertGreater(out_fast.stat().st_size, 500)

    def test_change_audio_speed_slow(self):
        out_slow = change_audio_speed(self.sample_wav, speed=0.75)
        self.assertTrue(out_slow.exists())
        self.assertGreater(out_slow.stat().st_size, 500)

    def test_transcribe_audio_segments(self):
        lang, duration, segments = transcribe_audio_segments(self.sample_wav)
        self.assertIsInstance(lang, str)
        self.assertAlmostEqual(duration, 2.0, delta=0.5)
        self.assertIsInstance(segments, list)

    def test_transcribe_to_txt(self):
        out_txt = transcribe_to_txt(self.sample_wav)
        self.assertTrue(out_txt.exists())
        content = out_txt.read_text(encoding="utf-8")
        self.assertIn("Transcripción ShiftDrop", content)

    def test_transcribe_to_srt(self):
        out_srt = transcribe_to_srt(self.sample_wav)
        self.assertTrue(out_srt.exists())
        content = out_srt.read_text(encoding="utf-8")
        self.assertIn("-->", content)

    def test_transcribe_to_docx(self):
        out_docx = transcribe_to_docx(self.sample_wav)
        self.assertTrue(out_docx.exists())
        self.assertGreater(out_docx.stat().st_size, 1000)
        doc = docx.Document(str(out_docx))
        full_text = " ".join([p.text for p in doc.paragraphs])
        self.assertIn("Transcripción", full_text)

    def test_dispatcher_transcribe_and_audio_actions(self):
        # 1. aud_to_aiff
        res_aiff = execute_action("aud_to_aiff", [self.sample_wav])
        self.assertTrue(res_aiff[0].exists())

        # 2. aud_to_wma
        res_wma = execute_action("aud_to_wma", [self.sample_wav])
        self.assertTrue(res_wma[0].exists())

        # 3. aud_to_ac3
        res_ac3 = execute_action("aud_to_ac3", [self.sample_wav])
        self.assertTrue(res_ac3[0].exists())

        # 4. aud_to_amr
        res_amr = execute_action("aud_to_amr", [self.sample_wav])
        self.assertTrue(res_amr[0].exists())

        # 5. aud_speed
        res_speed = execute_action("aud_speed", [self.sample_wav], params={"speed": 1.5})
        self.assertTrue(res_speed[0].exists())

        # 6. aud_transcribe_txt
        res_txt = execute_action("aud_transcribe_txt", [self.sample_wav])
        self.assertTrue(res_txt[0].exists())

        # 7. aud_transcribe_srt
        res_srt = execute_action("aud_transcribe_srt", [self.sample_wav])
        self.assertTrue(res_srt[0].exists())

        # 8. aud_transcribe_docx
        res_docx = execute_action("aud_transcribe_docx", [self.sample_wav])
        self.assertTrue(res_docx[0].exists())

    def test_video_without_audio_stream_raises_clean_error(self):
        from shiftdrop.core.ffmpeg_helper import has_audio_stream
        from shiftdrop.core.video_ops import extract_audio_from_video

        # Create video without audio
        vid_no_audio = self.dir_path / "silent_video.mp4"
        run_ffmpeg([
            "-f", "lavfi",
            "-i", "testsrc=duration=2:size=160x120:rate=10",
            "-c:v", "libx264",
            str(vid_no_audio)
        ])

        self.assertFalse(has_audio_stream(vid_no_audio))

        with self.assertRaises(ValueError) as ctx:
            transcribe_to_txt(vid_no_audio)
        self.assertIn("no contiene ninguna pista de audio", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx2:
            extract_audio_from_video(vid_no_audio, audio_format="mp3")
        self.assertIn("no contiene ninguna pista de audio", str(ctx2.exception))

    def test_transcribe_fallback_when_vad_filters_music(self):
        # Generate an audio with speech or music tone
        test_tone = self.dir_path / "music_tone.wav"
        run_ffmpeg([
            "-f", "lavfi",
            "-i", "sine=frequency=880:duration=2",
            str(test_tone)
        ])
        # Verify transcribe_audio_segments completes without error using fallback if needed
        lang, duration, segments = transcribe_audio_segments(test_tone)
        self.assertIsInstance(lang, str)
        self.assertGreater(duration, 0)


if __name__ == "__main__":
    unittest.main()
