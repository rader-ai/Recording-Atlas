import unittest
from import_vtt import parse_vtt
class VttTests(unittest.TestCase):
 def test_multiline_and_tags(self):
  d=parse_vtt('WEBVTT\n\n1\n00:00:01.000 --> 00:00:04.000\n<b>Hello</b>\nworld.\n','demo','Demo')
  self.assertEqual(d['cues'][0],{'start':1,'end':4,'text':'Hello world.'})
 def test_notes_ignored(self):
  d=parse_vtt('WEBVTT\n\nNOTE comment\nprivate note omitted\n\n00:01.000 --> 00:02.000\nText\n','demo','Demo')
  self.assertEqual(len(d['cues']),1)
 def test_overlap_rejected(self):
  with self.assertRaises(ValueError):parse_vtt('WEBVTT\n\n00:01.000 --> 00:03.000\nOne\n\n00:02.000 --> 00:04.000\nTwo\n','demo','Demo')
 def test_empty_corpus_rejected(self):
  with self.assertRaises(ValueError):parse_vtt('WEBVTT\n','demo','Demo')
