import copy,io,json,math,tempfile,unittest,urllib.error
from pathlib import Path
from core import *
ROOT=Path(__file__).resolve().parents[1]
DOCS=json.loads((ROOT/'data/transcripts.json').read_text())
class Counting(FixtureEmbedder):
 def __init__(self):self.calls=0;self.texts=0
 def embed(self,texts):self.calls+=1;self.texts+=len(texts);return super().embed(texts)
class CoreTests(unittest.TestCase):
 def setUp(self):self.p=Counting();self.index=Indexer(self.p).build(DOCS)
 def test_timestamps_overlap_and_no_overlap_only_tail(self):
  chunks=chunk_document(DOCS[0]);self.assertEqual(chunks[0]['start'],0)
  self.assertEqual(chunks[-1]['end'],90);self.assertLess(chunks[1]['start'],chunks[0]['end'])
  self.assertNotEqual(chunks[-1]['text'],DOCS[0]['cues'][-2]['text'])
 def test_duplicate_doc_ids_rejected(self):
  with self.assertRaises(ValueError):validate_docs([DOCS[0],DOCS[0]])
 def test_bad_timestamps_rejected(self):
  for value in [-1,float('nan'),True]:
   docs=copy.deepcopy(DOCS);docs[0]['cues'][0]['start']=value
   with self.assertRaises(ValueError):validate_docs(docs)
 def test_overlapping_cues_rejected(self):
  d=copy.deepcopy(DOCS);d[0]['cues'][1]['start']=1
  with self.assertRaises(ValueError):validate_docs(d)
 def test_unchanged_index_buys_no_vectors(self):
  self.p.calls=0;r=Indexer(self.p).build(DOCS,self.index)
  self.assertEqual(self.p.calls,0);self.assertEqual(r['stats']['changed'],0)
 def test_metadata_refresh_reuses_embeddings(self):
  d=copy.deepcopy(DOCS);d[0]['title']='Revised title';self.p.calls=0
  r=Indexer(self.p).build(d,self.index);self.assertEqual(self.p.calls,0)
  self.assertEqual(r['records'][0]['title'],'Revised title')
 def test_content_edit_reembeds_only_changed_passages(self):
  d=copy.deepcopy(DOCS);d[0]['cues'][0]['text']+=' Add mulch.';self.p.texts=0
  r=Indexer(self.p).build(d,self.index)
  self.assertGreater(self.p.texts,0);self.assertLess(self.p.texts,len(self.index['records']))
 def test_full_and_partial_deletion_scope(self):
  full=Indexer(self.p).build(DOCS[:1],self.index)
  partial=Indexer(self.p).build(DOCS[:1],self.index,full=False)
  self.assertEqual(len({r['doc_id'] for r in full['records']}),1)
  self.assertEqual(len({r['doc_id'] for r in partial['records']}),6)
 def test_partial_replacement_removes_stale_chunks(self):
  d=copy.deepcopy(DOCS[:1]);d[0]['cues']=d[0]['cues'][:1]
  result=Indexer(self.p).build(d,self.index,full=False)
  self.assertEqual(sum(r['doc_id']=='garden' for r in result['records']),1)
 def test_budget_blocks_before_provider_call(self):
  p=Counting()
  with self.assertRaises(ValueError):Indexer(p).build(DOCS,max_input_chars=1)
  self.assertEqual(p.calls,0)
 def test_dry_run_never_calls_provider(self):
  p=Counting();Indexer(p).build(DOCS,dry_run=True);self.assertEqual(p.calls,0)
 def test_provider_change_requires_fresh_index(self):
  old=copy.deepcopy(self.index);old['signature']='another-model'
  with self.assertRaises(ValueError):Indexer(self.p).build(DOCS,old)
 def test_provider_failure_does_not_mutate_previous_index(self):
  class Broken(FixtureEmbedder):
   def embed(self,t):raise RuntimeError('offline')
  before=copy.deepcopy(self.index);d=copy.deepcopy(DOCS);d[0]['cues'][0]['text']+=' Changed.'
  with self.assertRaises(RuntimeError):Indexer(Broken()).build(d,self.index)
  self.assertEqual(before,self.index)
 def test_atomic_save_roundtrip(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'index.json';save_atomic(p,self.index);self.assertEqual(json.loads(p.read_text()),self.index)
 def test_query_bounds_and_mode(self):
  s=Search(self.index,self.p)
  for q in ['', 'a','x'*201]:
   with self.assertRaises(ValueError):s.query(q)
  with self.assertRaises(ValueError):s.query('valid query','unknown')
 def test_vector_outage_keeps_keyword_results(self):
  r=Search(self.index,self.p).query('renew books',fail_vector=True)
  self.assertTrue(r['degraded']);self.assertEqual(r['results'][0]['doc_id'],'library')
 def test_query_cache_skips_second_provider_call(self):
  s=Search(self.index,self.p);s.query('garden soil');self.p.calls=0
  self.assertTrue(s.query('garden soil')['cached']);self.assertEqual(self.p.calls,0)
 def test_exact_citations_resolve_to_source(self):
  for r in Search(self.index,self.p).query('recording timestamp')['results']:
   original=next(x for x in self.index['records'] if x['id']==r['id'])
   self.assertTrue(validate_excerpt(original,r['text']))
   self.assertEqual(r['citation'],f"{r['doc_id']}@{r['start']}")
 def test_unsupported_excerpt_fails(self):
  self.assertFalse(validate_excerpt(self.index['records'][0],'A made up promise.'))
 def test_http_adapter_orders_and_validates_vectors(self):
  def transport(*a,**k):return io.BytesIO(json.dumps({'data':[{'index':1,'embedding':[0,2]},{'index':0,'embedding':[2,0]}]}).encode())
  p=OpenAIEmbedder('test-placeholder',transport=transport)
  self.assertEqual(p.embed(['a','b']),[[1,0],[0,1]])
 def test_http_adapter_retries_429_then_recovers(self):
  calls=[];sleeps=[]
  def transport(*a,**k):
   calls.append(1)
   if len(calls)==1:raise urllib.error.HTTPError('https://example.invalid',429,'limited',{},None)
   return io.BytesIO(b'{"data":[{"index":0,"embedding":[1,0]}]}')
  p=OpenAIEmbedder('test-placeholder',transport=transport,sleep=sleeps.append)
  p.embed(['x']);self.assertEqual(len(calls),2);self.assertEqual(sleeps,[0.25])
 def test_http_adapter_does_not_retry_authentication(self):
  calls=[]
  def transport(*a,**k):calls.append(1);raise urllib.error.HTTPError('https://example.invalid',401,'private error text',{},None)
  with self.assertRaisesRegex(RuntimeError,'Embedding provider request failed'):OpenAIEmbedder('test-placeholder',transport=transport).embed(['x'])
  self.assertEqual(len(calls),1)
 def test_http_adapter_rejects_nonfinite_vectors(self):
  def transport(*a,**k):return io.BytesIO(b'{"data":[{"index":0,"embedding":[NaN,0]}]}')
  with self.assertRaises(ValueError):OpenAIEmbedder('test-placeholder',transport=transport).embed(['x'])
if __name__=='__main__':unittest.main()
