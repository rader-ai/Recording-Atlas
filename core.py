"""Portable retrieval pipeline. Standard library only; no private source copied."""
from __future__ import annotations
import concurrent.futures as futures
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
import urllib.request
import urllib.error
from collections import Counter

STOP = set('a an the i we you they it is are was to of in on for with and or how what can do does my our'.split())
# Transparent fixture concepts, deliberately not a learned embedding model.
CONCEPTS = [
 set('garden gardening water watering irrigation soil beds drought dry mulch'.split()),
 set('library borrowing borrow books checkout renew renewal overdue late loan'.split()),
 set('workshop maker tools goggles eyes eye protection safety soldering heat'.split()),
 set('volunteer volunteers onboarding orientation welcome newcomer new induction'.split()),
 set('archive recordings transcripts captions search timestamp passage audio'.split()),
 set('events event access accessible wheelchair ramp entry entrance accommodation'.split()),
]

def tokens(text):
 return [x for x in re.findall(r"[a-z0-9]+", text.lower()) if x not in STOP]

def digest(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def validate_docs(docs):
 seen=set()
 for d in docs:
  if not isinstance(d.get('id'),str) or not re.fullmatch(r'[a-z0-9_]+',d['id']) or d['id'] in seen:
   raise ValueError('Document IDs must be unique safe slugs')
  seen.add(d['id'])
  if not isinstance(d.get('title'),str) or not d['title'].strip(): raise ValueError('Title required')
  if not d.get('cues'): raise ValueError('Cues required')
  last=0
  for c in d['cues']:
   start,end=c.get('start'),c.get('end')
   if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in [start,end]):
    raise ValueError('Finite timestamps required')
   if start<last or end<=start: raise ValueError('Cues must be ordered and nonoverlapping')
   if not isinstance(c.get('text'),str) or not c['text'].strip() or len(c['text'])>2000: raise ValueError('Invalid cue text')
   last=end
 return docs

def chunk_document(doc,target_words=45,overlap_cues=1):
 if target_words<10 or overlap_cues not in (0,1,2): raise ValueError('Invalid chunk settings')
 chunks=[]; buf=[]; fresh=False
 def emit():
  text=' '.join(c['text'] for c in buf)
  chunks.append({'id':f"{doc['id']}:{len(chunks)}",'doc_id':doc['id'],'title':doc['title'],
   'start':buf[0]['start'],'end':buf[-1]['end'],'text':text,'content_hash':digest(text)})
 for cue in doc['cues']:
  buf.append(cue); fresh=True
  if sum(len(c['text'].split()) for c in buf)>=target_words:
   emit();buf=buf[-overlap_cues:] if overlap_cues else [];fresh=False
 if fresh:emit()
 return chunks

def normalize(v):
 norm=math.sqrt(sum(x*x for x in v))
 return [x/norm for x in v] if norm else v

class FixtureEmbedder:
 signature='fixture-concepts-v1'
 def embed(self,texts):
  result=[]
  for text in texts:
   counts=Counter(tokens(text)); v=[sum(counts[t] for t in concept) for concept in CONCEPTS]
   # Small lexical dimensions break ties; stable hashes, never Python's salted hash.
   extra=[0.0]*64
   for t,count in counts.items():extra[int(hashlib.sha256(t.encode()).hexdigest()[:8],16)%64]+=count*0.08
   result.append(normalize(v+extra))
  return result

class OpenAIEmbedder:
 def __init__(self,key,model='text-embedding-3-small',transport=None,sleep=time.sleep):
  if not key:raise ValueError('OPENAI_API_KEY required')
  self.key=key;self.model=model;self.signature='openai:'+model
  self.transport=transport or urllib.request.urlopen;self.sleep=sleep
 def embed(self,texts):
  body=json.dumps({'model':self.model,'input':texts,'encoding_format':'float'}).encode()
  req=urllib.request.Request('https://api.openai.com/v1/embeddings',data=body,
   headers={'Content-Type':'application/json','Authorization':'Bearer '+self.key})
  for attempt in range(3):
   try:
    with self.transport(req,timeout=5) as response: payload=json.load(response)
    data=sorted(payload['data'],key=lambda x:x['index'])
    if [d['index'] for d in data]!=list(range(len(texts))):raise ValueError('Embedding response count or indices invalid')
    vectors=[d['embedding'] for d in data]
    width=len(vectors[0]) if vectors else 0
    if not width or any(len(v)!=width or any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in v) for v in vectors):
     raise ValueError('Invalid embedding vectors')
    return [normalize(v) for v in vectors]
   except urllib.error.HTTPError as e:
    if e.code not in (429,500,502,503,504) or attempt==2:raise RuntimeError('Embedding provider request failed') from None
    self.sleep(0.25*2**attempt)
   except (urllib.error.URLError,TimeoutError):
    if attempt==2:raise RuntimeError('Embedding provider unavailable') from None
    self.sleep(0.25*2**attempt)

class Indexer:
 def __init__(self,provider):self.provider=provider
 def build(self,docs,previous=None,max_input_chars=100000,full=True,dry_run=False):
  validate_docs(docs)
  old=previous or {'records':[],'signature':self.provider.signature}
  if old.get('signature')!=self.provider.signature:raise ValueError('Provider changed: choose a fresh index path')
  records=[r for d in docs for r in chunk_document(d)]
  before={r['id']:r for r in old['records']}
  changed=[r for r in records if before.get(r['id'],{}).get('content_hash')!=r['content_hash']]
  input_chars=sum(len(r['text']) for r in changed)
  stats={'documents':len(docs),'chunks':len(records),'changed':len(changed),'unchanged':len(records)-len(changed),
   'input_characters':input_chars,'estimated_tokens':math.ceil(input_chars/4),
   'deleted':len(set(before)-{r['id'] for r in records}) if full else 0,'mode':'full' if full else 'partial'}
  if input_chars>max_input_chars:raise ValueError('Embedding input budget exceeded before provider call')
  if dry_run:return stats
  vectors={}
  # Small bounded batches. Commit happens only after every batch succeeds.
  for offset in range(0,len(changed),16):
   batch=changed[offset:offset+16]; values=self.provider.embed([r['text'] for r in batch])
   if len(values)!=len(batch):raise ValueError('Provider returned wrong vector count')
   vectors.update(zip((r['id'] for r in batch),values))
  for r in records:r['vector']=vectors[r['id']] if r['id'] in vectors else before[r['id']]['vector']
  if not full:
   included={d['id'] for d in docs};records += [r for r in old['records'] if r['doc_id'] not in included]
  return {'signature':self.provider.signature,'records':records,'stats':stats,'revision':digest(records)}

def save_atomic(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.NamedTemporaryFile('w',dir=path.parent,delete=False) as f:
  json.dump(value,f);f.flush();os.fsync(f.fileno());name=f.name
 os.replace(name,path)

def lexical(records,q):
 terms=tokens(q); n=len(records); results=[]
 lengths=[len(tokens(r['text'])) for r in records]; avg=sum(lengths)/max(n,1)
 docfreq={t:sum(t in tokens(r['text']) for r in records) for t in terms}
 for r,length in zip(records,lengths):
  tf=Counter(tokens(r['text']));score=0
  for t in terms:
   count=tf[t]
   idf=math.log(1+(n-docfreq[t]+0.5)/(docfreq[t]+0.5))
   if count:score+=idf*(count*2.2)/(count+1.2*(0.25+0.75*length/max(avg,1)))
  if score>0:results.append((r['id'],score))
 return sorted(results,key=lambda x:(-x[1],x[0]))

def vector_search(records,q,provider):
 v=provider.embed([q])[0]
 if any(len(r['vector'])!=len(v) for r in records):raise ValueError('Vector dimensions mismatch')
 return sorted([(r['id'],sum(a*b for a,b in zip(v,r['vector']))) for r in records],key=lambda x:(-x[1],x[0]))

class Search:
 def __init__(self,index,provider):
  if index['signature']!=provider.signature:raise ValueError('Index and query provider must match')
  self.index=index;self.provider=provider;self.cache={}
 def query(self,q,mode='hybrid',fail_vector=False):
  if not isinstance(q,str) or not 2<=len(q.strip())<=200:raise ValueError('Enter 2 to 200 characters')
  if mode not in ['hybrid','lexical','vector']:raise ValueError('Unknown retrieval mode')
  q=' '.join(q.lower().split());key=(q,mode,fail_vector,self.index['revision'])
  if key in self.cache:return dict(self.cache[key],cached=True)
  records=self.index['records']; lex=[]; vec=[];degraded=False
  def vector_lane():
   if fail_vector:raise RuntimeError('Simulated outage')
   return vector_search(records,q,self.provider)
  with futures.ThreadPoolExecutor(max_workers=2) as pool:
   lf=pool.submit(lexical,records,q) if mode!='vector' else None
   vf=pool.submit(vector_lane) if mode!='lexical' else None
   if lf:lex=lf.result()
   if vf:
    try:vec=[v for v in vf.result() if v[1]>=0.18]
    except Exception:degraded=True
  if degraded and not lex:lex=lexical(records,q)
  scores={};lanes={}
  for lane,ranking in [('lexical',lex),('vector',vec)]:
   for rank,(rid,score) in enumerate(ranking[:20],1):
    scores[rid]=scores.get(rid,0)+1/(60+rank);lanes.setdefault(rid,[]).append(lane)
  byid={r['id']:r for r in records};results=[];seen=set()
  for rid in sorted(scores,key=lambda x:(-scores[x],x)):
   r=byid[rid]
   if r['doc_id'] in seen:continue
   seen.add(r['doc_id']);results.append({k:v for k,v in r.items() if k not in ['vector','content_hash']})
   results[-1].update(score=round(scores[rid],6),lanes=lanes[rid],citation=f"{r['doc_id']}@{r['start']}")
   if len(results)==5:break
  answer={'query':q,'mode':mode,'degraded':degraded,'cached':False,'provider':self.provider.signature,'results':results}
  if len(self.cache)>=128:self.cache.pop(next(iter(self.cache)))
  if not degraded:self.cache[key]=answer
  return answer

def validate_excerpt(record,excerpt):
 # Exact source anchoring is intentionally narrower than a factuality judgment.
 return bool(excerpt.strip()) and excerpt in record['text']
