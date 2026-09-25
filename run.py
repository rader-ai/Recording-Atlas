"""Single user local onboarding and resumable content workspace."""
import argparse, base64, hashlib, json, os, secrets, shutil, subprocess, sys, tempfile, threading, time, webbrowser
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
from core import FixtureEmbedder, OpenAIEmbedder, Indexer, Search, save_atomic, validate_docs
from import_vtt import parse_vtt
from connectors import discover, transcribe, questions, request_json
ROOT=Path(__file__).resolve().parent
MAX_FILE=20_000_000

class Workspace:
    def __init__(self,path):
        self.path=Path(path);self.path.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.lock=threading.RLock();self.worker=None
        self.keys={'openai':os.environ.get('OPENAI_API_KEY',''),'youtube':os.environ.get('YOUTUBE_API_KEY','')}
        self.verified={};self.model=os.environ.get('CIL_TEXT_MODEL','gpt-4.1-mini')
        self.state=self.read('state.json',{'configured':False,'provider':'fixture'})
        for job in self.jobs():
            if job['status']=='running':job.update(status='interrupted',message='Restarted. Resume to continue completed stages.');self.write('job_'+job['id']+'.json',job)
    def read(self,name,default=None):
        p=self.path/name
        return json.loads(p.read_text()) if p.exists() else default
    def write(self,name,data):save_atomic(self.path/name,data)
    def jobs(self):return [json.loads(p.read_text()) for p in sorted(self.path.glob('job_*.json'),key=lambda p:p.stat().st_mtime,reverse=True)]
    def docs(self):return self.read('documents.json',[])
    def provider(self):return FixtureEmbedder() if self.state['provider']=='fixture' else OpenAIEmbedder(self.keys['openai'])
    def index_name(self):return 'index_'+self.state['provider']+'.json'
    def status(self):
        return {'configured':self.state['configured'],'provider':self.state['provider'],'connections':{k:{'configured':bool(v),'verified':self.verified.get(k,False)} for k,v in self.keys.items()},
                'runtime':sys.version.split()[0],'platform':sys.platform,'free_gb':round(shutil.disk_usage(self.path).free/1e9,1),
                'ffprobe':bool(shutil.which('ffprobe')),'documents':len(self.docs()),'jobs':self.jobs(),'model':self.model}
    def configure(self,data):
        with self.lock:
            if self.worker and self.worker.is_alive():raise ValueError('Wait for the current import before changing settings.')
            for name in ('openai','youtube'):
                if name in data:
                    key=data[name]
                    if not isinstance(key,str) or len(key)>500 or any(c.isspace() for c in key):raise ValueError('Invalid credential format.')
                    self.keys[name]=key;self.verified[name]=False
            provider=data.get('provider',self.state['provider'])
            if provider not in ('fixture','openai'):raise ValueError('Unknown processing mode.')
            if provider=='openai' and not self.keys['openai'] and not (self.state['configured'] and self.state['provider']=='openai'):raise ValueError('Add your OpenAI API key or choose example mode.')
            if provider!=self.state['provider'] and self.docs():raise ValueError('This archive already has a search mode. Use a separate data directory to change it.')
            self.state.update(configured=True,provider=provider);self.write('state.json',self.state)
        return self.status()
    def verify(self,service):
        key=self.keys.get(service)
        if not key:raise ValueError('Add a key first.')
        if service=='openai':request_json('https://api.openai.com/v1/models',key)
        elif service=='youtube':request_json('https://www.googleapis.com/youtube/v3/videos?part=id&id=jNQXAC9IVRw&key='+key)
        else:raise ValueError('Unknown service.')
        self.verified[service]=True
        return {'message':'Connection verified. This checks access, not paid model execution or billing. YouTube checks consume API quota.'}
    def create(self,data):
        with self.lock:
            if self.worker and self.worker.is_alive():raise ValueError('An import is already running.')
            if not self.state['configured']:raise ValueError('Complete setup first.')
            example=data.get('example') is True
            if not example and self.state['provider']=='fixture':raise ValueError('Example vectors are only suitable for supplied examples. Start a separate workspace with OpenAI for your own content.')
            if data.get('paid') is not True and not example:raise ValueError('Confirm paid processing before importing your content.')
            title=str(data.get('title','')).strip()[:200]
            if not example and not title:raise ValueError('Give this recording a title.')
            source=str(data.get('source','')).strip()
            if source and (urlsplit(source).scheme not in ('http','https') or urlsplit(source).username):raise ValueError('Use an HTTP or HTTPS source reference.')
            blob=b'';extension='';doc=None
            if not example:
                extension=Path(str(data.get('filename',''))).suffix.lower()
                if extension not in ('.vtt','.mp3','.m4a','.wav','.mp4','.webm'):raise ValueError('Upload WebVTT, MP3, M4A, WAV, MP4, or WebM.')
                try:blob=base64.b64decode(data.get('file',''),validate=True)
                except Exception:raise ValueError('Invalid upload.') from None
                if not 0<len(blob)<=MAX_FILE:raise ValueError('Upload must be between 1 byte and 20 MB.')
                if extension!='.vtt' and not shutil.which('ffprobe'):raise ValueError('Audio requires FFmpeg with ffprobe. Install it or upload a WebVTT transcript.')
            identity=hashlib.sha256(blob+json.dumps({'title':title,'source':source,'example':example,'questions':bool(data.get('questions')),'provider':self.state['provider'],'model':self.model,'pipeline':1},sort_keys=True).encode()).hexdigest()[:24]
            old=self.read('job_'+identity+'.json')
            if old:return old
            if extension=='.vtt':doc=parse_vtt(blob.decode('utf-8-sig'),identity,title)
            if example and self.state['provider']!='fixture' and data.get('paid') is not True:raise ValueError('Example content in OpenAI mode also incurs embedding charges. Confirm paid processing.')
            job={'id':identity,'title':title or 'Example archive','source':source,'example':example,'extension':extension,'questions':bool(data.get('questions')) and not example,
                 'status':'ready','stage':'uploaded','message':'Ready to process.','completed':[],'created':time.time(),'model':self.model}
            if doc:self.write('raw_'+identity+'.json',[doc])
            if blob:
                p=self.path/('upload_'+identity+extension)
                with open(p,'wb') as f:f.write(blob)
                os.chmod(p,0o600)
            self.write('job_'+identity+'.json',job)
            return job
    def start(self,jid):
        with self.lock:
            if self.worker and self.worker.is_alive():raise ValueError('An import is already running.')
            job=next((j for j in self.jobs() if j['id']==jid),None)
            if not job:raise ValueError('Import not found.')
            if job['status']=='complete':return job
            if self.state['provider']=='openai' and not self.keys['openai']:raise ValueError('Reconnect your OpenAI key before resuming.')
            self.worker=threading.Thread(target=self.process,args=(job,),daemon=True);self.worker.start()
            return {'message':'Processing started.'}
    def process(self,job):
        jid=job['id'];name='job_'+jid+'.json'
        def stage(s,message):job.update(status='running',stage=s,message=message);self.write(name,job)
        try:
            raw=self.read('raw_'+jid+'.json')
            if raw is None:
                if job['example']:raw=json.loads((ROOT/'data/transcripts.json').read_text())
                else:
                    stage('transcription','Checking media duration before sending audio.')
                    file=self.path/('upload_'+jid+job['extension'])
                    probe=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(file)],capture_output=True,timeout=20)
                    try:duration=float(json.loads(probe.stdout)['format']['duration'])
                    except Exception:raise ValueError('Could not read media duration. Export a standard audio file or upload WebVTT.') from None
                    if not 0<duration<=5400:raise ValueError('Recording must be no longer than 90 minutes.')
                    stage('transcription','Transcribing with timestamps. This may take several minutes.')
                    raw=[{'id':jid,'title':job['title'],'source':job['source'],'cues':transcribe(file.read_bytes(),job['extension'],self.keys['openai'])}]
                validate_docs(raw);self.write('raw_'+jid+'.json',raw)
            if 'transcription' not in job['completed']:job['completed'].append('transcription')
            stage('archive','Preserving the raw transcript and building a readable archive.')
            cleaned=json.loads(json.dumps(raw))
            for doc in cleaned:
                doc.setdefault('source',job['source'])
                for cue in doc['cues']:cue['text']=' '.join(cue['text'].split())
            # Cleanup is intentionally deterministic whitespace normalization, not an AI rewrite.
            self.write('clean_'+jid+'.json',cleaned)
            docs={d['id']:d for d in self.docs()};docs.update({d['id']:d for d in cleaned});docs=list(docs.values())
            stage('index','Indexing changed passages. Completed index builds are reused on resume.')
            index=Indexer(self.provider()).build(docs,self.read(self.index_name()),max_input_chars=300_000)
            self.write(self.index_name(),index);self.write('documents.json',docs)
            if 'index' not in job['completed']:job['completed'].append('index')
            if job['questions'] and self.read('draft_'+jid+'.json') is None:
                stage('questions','Drafting questions with exact source excerpts. Human review is required.')
                self.write('draft_'+jid+'.json',questions(cleaned[0]['cues'],self.keys['openai'],job['model']))
            job.update(status='complete',stage='complete',message='Archive ready. Any generated questions need human review.');self.write(name,job)
        except Exception as e:
            job.update(status='failed',message=str(e) if isinstance(e,ValueError) else 'Processing failed. Check connection and source format, then resume. A timed out provider call may still be billed.')
            self.write(name,job)
    def query(self,q):
        index=self.read(self.index_name())
        if not index:raise ValueError('Import a recording first.')
        return Search(index,self.provider()).query(q)
    def archive(self):
        return {'documents':self.docs(),'drafts':[{'title':j['title'],'items':self.read('draft_'+j['id']+'.json',[])} for j in self.jobs() if j['questions']]}

def serve(workspace,port,open_browser=False):
    token=secrets.token_urlsafe(32);origin=f'http://127.0.0.1:{port}';gate=threading.BoundedSemaphore(4)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def setup(self):super().setup();self.connection.settimeout(30)
        def send(self,status,data,mime='application/json'):
            body=json.dumps(data).encode() if mime=='application/json' else data
            self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers();self.wfile.write(body)
        def allowed(self):
            if self.headers.get('Host')!=f'127.0.0.1:{port}':self.send(403,{'error':'Open the exact local address printed in your terminal.'});return False
            return True
        def do_GET(self):
            if not self.allowed():return
            u=urlsplit(self.path)
            files={'/':('onboarding.html','text/html; charset=utf-8'),'/app.js':('onboarding.js','application/javascript'),'/app.css':('onboarding.css','text/css')}
            if u.path in files:
                file,mime=files[u.path];body=(ROOT/'web'/file).read_bytes()
                if u.path=='/':body=body.replace(b'__TOKEN__',token.encode())
                self.send(200,body,mime);return
            if not secrets.compare_digest(self.headers.get('X-Setup-Token',''),token):self.send(403,{'error':'Reload the local application.'});return
            if u.path=='/api/status':self.send(200,workspace.status())
            elif u.path=='/api/archive':self.send(200,workspace.archive())
            else:self.send(404,{'error':'Not found'})
        def do_POST(self):
            if not self.allowed():return
            if self.headers.get('Origin')!=origin or not secrets.compare_digest(self.headers.get('X-Setup-Token',''),token):self.send(403,{'error':'Reload the local application.'});return
            if self.headers.get('Content-Type')!='application/json':self.send(415,{'error':'JSON required'});return
            if not gate.acquire(blocking=False):self.send(429,{'error':'Too many requests. Try again shortly.'});return
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=28_000_000:raise ValueError('Request exceeds upload limit.')
                data=json.loads(self.rfile.read(size))
                if not isinstance(data,dict):raise ValueError('Object required.')
                route=urlsplit(self.path).path
                if route=='/api/configure':result=workspace.configure(data)
                elif route=='/api/verify':result=workspace.verify(data.get('service'))
                elif route=='/api/discover':result=discover(str(data.get('url','')),workspace.keys['youtube'])
                elif route=='/api/create':result=workspace.create(data)
                elif route=='/api/start':result=workspace.start(data.get('id'))
                elif route=='/api/search':result=workspace.query(data.get('query',''))
                else:self.send(404,{'error':'Not found'});return
                self.send(200,result)
            except (ValueError,UnicodeError) as e:self.send(400,{'error':str(e)})
            except Exception:self.send(503,{'error':'Operation failed. Check your connection and configuration.'})
            finally:gate.release()
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print('Open '+origin+' | Data: '+str(workspace.path),flush=True)
    if open_browser:webbrowser.open(origin)
    server.serve_forever()

if __name__=='__main__':
    if sys.version_info<(3,11):raise SystemExit('Python 3.11 or newer required.')
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--data-dir',default=str(Path.home()/'.local/share/content-intelligence-lab'));parser.add_argument('--open',action='store_true')
    args=parser.parse_args();os.umask(0o077)
    serve(Workspace(args.data_dir),args.port,args.open)
