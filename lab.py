"""CLI and loopback only review server."""
import argparse,json,os,time,threading
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from core import FixtureEmbedder,OpenAIEmbedder,Indexer,Search,save_atomic
ROOT=Path(__file__).resolve().parent

def provider(name):
 return FixtureEmbedder() if name=='fixture' else OpenAIEmbedder(os.environ.get('OPENAI_API_KEY',''))

def evaluate(search):
 cases=json.loads((ROOT/'data/queries.json').read_text());metrics={}
 for mode in ['lexical','vector','hybrid']:
  ranks=[]
  for case in cases:
   docs=[r['doc_id'] for r in search.query(case['query'],mode)['results']]
   ranks.append(docs.index(case['expected_doc'])+1 if case['expected_doc'] in docs else 0)
  metrics[mode]={'hit_at_1':sum(r==1 for r in ranks)/len(ranks),'hit_at_3':sum(0<r<=3 for r in ranks)/len(ranks),
   'mrr_at_5':sum(1/r if r else 0 for r in ranks)/len(ranks),'queries':len(ranks)}
 return {'scope':'Small authored development set, not an independent benchmark. Fixture concepts and queries share a domain.',
  'provider':search.provider.signature,'metrics':metrics}

def serve(index,embedder,port):
 docs=json.loads((ROOT/'data/transcripts.json').read_text());search=Search(index,embedder);lock=threading.Lock();visits={}
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def send(self,status,body,mime='application/json'):
   payload=json.dumps(body).encode() if mime=='application/json' else body
   self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(payload)))
   self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(payload)
  def do_GET(self):
   # Loopback Host allowlist prevents exposing API calls through DNS rebinding.
   if self.headers.get('Host') not in [f'127.0.0.1:{port}',f'localhost:{port}']:
    self.send(403,{'error':'Local access only'});return
   u=urlparse(self.path);q=parse_qs(u.query)
   if u.path=='/':self.send(200,(ROOT/'web/index.html').read_bytes(),'text/html; charset=utf-8');return
   if u.path=='/api/source':
    doc=next((d for d in docs if d['id']==q.get('id',[''])[0]),None)
    self.send(200 if doc else 404,doc or {'error':'Source not found'});return
   if u.path=='/api/status':self.send(200,{'provider':embedder.signature,'stats':index['stats']});return
   if u.path!='/api/search':self.send(404,{'error':'Not found'});return
   with lock:
    now=time.monotonic();ip=self.client_address[0];visits[ip]=[t for t in visits.get(ip,[]) if now-t<60]
    if len(visits[ip])>=30:self.send(429,{'error':'Please wait before searching again'});return
    visits[ip].append(now)
    try:
     result=search.query(q.get('q',[''])[0],q.get('mode',['hybrid'])[0],q.get('outage',['0'])[0]=='1')
     self.send(200,result)
    except ValueError as e:self.send(400,{'error':str(e)})
    except Exception:self.send(503,{'error':'Search unavailable'})
 server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
 print(f'Open http://127.0.0.1:{port} | {embedder.signature}',flush=True)
 server.serve_forever()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('command',choices=['index','plan','search','evaluate','serve'])
 ap.add_argument('--provider',choices=['fixture','openai'],default='fixture');ap.add_argument('--index',default=str(ROOT/'build/index.json'))
 ap.add_argument('--max-input-chars',type=int,default=100000);ap.add_argument('--query',default='find recording timestamp')
 ap.add_argument('--mode',default='hybrid',choices=['lexical','vector','hybrid']);ap.add_argument('--port',type=int,default=8765)
 args=ap.parse_args();p=provider(args.provider);path=Path(args.index)
 old=json.loads(path.read_text()) if path.exists() else None
 if args.command in ['index','plan']:
  result=Indexer(p).build(json.loads((ROOT/'data/transcripts.json').read_text()),old,args.max_input_chars,dry_run=args.command=='plan')
  if args.command=='index':save_atomic(path,result);result=result['stats']
  print(json.dumps(result,indent=2));return
 if old is None:ap.error('Run index first')
 s=Search(old,p)
 if args.command=='search':print(json.dumps(s.query(args.query,args.mode),indent=2))
 if args.command=='evaluate':print(json.dumps(evaluate(s),indent=2))
 if args.command=='serve':serve(old,p,args.port)
if __name__=='__main__':main()
