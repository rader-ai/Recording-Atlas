import base64,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from connectors import video_id,LinkParser,public_target,validate_questions,discover,transcribe
from run import Workspace
from core import FixtureEmbedder

VTT='WEBVTT\n\n00:00.000 --> 00:10.000\nA recording archive preserves useful teaching for readers.\n'
class ConnectorTests(unittest.TestCase):
    def test_video_urls(self):
        for url in ['https://youtu.be/abcdefghijk','https://www.youtube.com/watch?v=abcdefghijk','https://youtube.com/embed/abcdefghijk']:
            self.assertEqual(video_id(url),'abcdefghijk')
        self.assertIsNone(video_id('https://youtube.com.evil.test/watch?v=abcdefghijk'))
        self.assertIsNone(video_id('https://user:password@youtube.com/watch?v=abcdefghijk'))
    def test_embed_dedup(self):
        p=LinkParser();p.feed('<iframe src="https://youtube.com/embed/abcdefghijk"></iframe><a href="https://youtu.be/abcdefghijk">same</a>')
        self.assertEqual(p.ids,['abcdefghijk'])
    def test_private_destinations_blocked(self):
        for ip in ['127.0.0.1','169.254.169.254','10.0.0.5','::1','192.168.1.1']:
            with self.assertRaises(ValueError):public_target('https://example.test',lambda *a,**k:[(2,1,6,'',(ip,443))])
    def test_url_protocol_blocked(self):
        for url in ['file:///etc/passwd','http://example.com','https://user:pass@example.com','https://example.com:8000']:
            with self.assertRaises(ValueError):public_target(url)
    def test_source_grounding(self):
        cues=[{'text':'The archive preserves context for readers.','start':2}]
        self.assertEqual(validate_questions([{'question':'What does the archive preserve?','quote':'preserves context for readers.','cue':0}],cues)[0]['start'],2)
        with self.assertRaises(ValueError):validate_questions([{'question':'Why?','quote':'Something never said','cue':0}],cues)
        with self.assertRaises(ValueError):validate_questions([{'question':'Why?','quote':'preserves context','cue':True}],cues)
    def test_playlist_requires_account(self):
        with self.assertRaises(ValueError):discover('https://youtube.com/playlist?list=PL123')
    @patch('connectors.request_json')
    def test_playlist_pagination_dedup(self,request):
        entry={'snippet':{'title':'A','resourceId':{'videoId':'abcdefghijk'}}}
        request.side_effect=[{'items':[entry],'nextPageToken':'page2'},{'items':[entry]}]
        self.assertEqual(len(discover('https://youtube.com/playlist?list=PL123','key')['items']),1)
        self.assertEqual(request.call_count,2)
    @patch('connectors.request_json')
    def test_transcription_timestamps(self,request):
        request.return_value={'segments':[{'start':0,'end':3,'text':' First '},{'start':2.9,'end':5,'text':'Second'}]}
        self.assertEqual(transcribe(b'bytes','.mp3','key')[1]['start'],3)
        body=request.call_args.args[2]
        self.assertIn(b'verbose_json',body);self.assertIn(b'whisper-1',body)

class WorkspaceTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.ws=Workspace(self.tmp.name)
    def tearDown(self):
        if self.ws.worker:self.ws.worker.join(5)
        self.tmp.cleanup()
    def test_example_and_resume_no_reembedding(self):
        self.ws.configure({'provider':'fixture'});job=self.ws.create({'example':True});self.ws.process(job)
        self.assertEqual(self.ws.jobs()[0]['status'],'complete');self.assertEqual(len(self.ws.docs()),6)
        with patch.object(FixtureEmbedder,'embed',side_effect=AssertionError('Unexpected repeat')):self.ws.process(job)
        self.assertEqual(self.ws.jobs()[0]['status'],'complete')
        self.assertTrue(self.ws.query('archive recordings')['results'])
    def test_credentials_not_written_or_exposed(self):
        self.ws.configure({'provider':'openai','openai':'fake_private_key'})
        self.assertNotIn('fake_private_key',json.dumps(self.ws.status()))
        self.assertNotIn('fake_private_key',''.join(p.read_text() for p in Path(self.tmp.name).glob('*.json')))
        self.ws.configure({'openai':''});self.assertFalse(self.ws.keys['openai'])
    def test_paid_confirmation(self):
        self.ws.configure({'provider':'openai','openai':'fake_key'})
        with self.assertRaises(ValueError):self.ws.create({'filename':'x.vtt','title':'X','file':base64.b64encode(VTT.encode()).decode()})
    def test_own_content_not_fixture(self):
        self.ws.configure({'provider':'fixture'})
        with self.assertRaises(ValueError):self.ws.create({'paid':True,'filename':'x.vtt','title':'X','file':base64.b64encode(VTT.encode()).decode()})
    def test_transcript_flow_mocked_provider(self):
        self.ws.configure({'provider':'openai','openai':'fake_key'})
        data={'paid':True,'filename':'x.vtt','title':'X','file':base64.b64encode(VTT.encode()).decode(),'questions':True}
        job=self.ws.create(data)
        with patch.object(self.ws,'provider',return_value=FixtureEmbedder()),patch('run.questions',return_value=[{'question':'What?','answer':'A recording archive','start':0,'status':'Needs human review'}]):self.ws.process(job)
        self.assertEqual(self.ws.jobs()[0]['status'],'complete');self.assertEqual(len(self.ws.docs()),1)
        self.assertEqual(self.ws.create(data)['id'],job['id'])
    def test_interrupted_job_recovered(self):
        self.ws.configure({'provider':'fixture'});job=self.ws.create({'example':True});job['status']='running';self.ws.write('job_'+job['id']+'.json',job)
        self.assertEqual(Workspace(self.tmp.name).jobs()[0]['status'],'interrupted')
    def test_model_failure_keeps_search_archive(self):
        self.ws.configure({'provider':'openai','openai':'fake_key'})
        job=self.ws.create({'paid':True,'filename':'x.vtt','title':'X','file':base64.b64encode(VTT.encode()).decode(),'questions':True})
        with patch.object(self.ws,'provider',return_value=FixtureEmbedder()),patch('run.questions',side_effect=ValueError('Temporary problem')):self.ws.process(job)
        self.assertEqual(self.ws.jobs()[0]['status'],'failed');self.assertEqual(len(self.ws.docs()),1)
        with patch.object(self.ws,'provider',return_value=FixtureEmbedder()),patch('run.questions',return_value=[]),patch.object(FixtureEmbedder,'embed',side_effect=AssertionError('Repeated paid work')):self.ws.process(job)
        self.assertEqual(self.ws.jobs()[0]['status'],'complete')
if __name__=='__main__':unittest.main()
