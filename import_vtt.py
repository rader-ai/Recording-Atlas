"""Import a local WebVTT transcript as one validated sample document."""
import argparse,json,re
from pathlib import Path
from core import validate_docs

def seconds(value):
 parts=value.replace(',','.').split(':')
 if len(parts)==2:parts.insert(0,'0')
 if len(parts)!=3:raise ValueError('Invalid VTT time')
 h,m,s=float(parts[0]),float(parts[1]),float(parts[2])
 if h<0 or not 0<=m<60 or not 0<=s<60:raise ValueError('Invalid VTT time')
 return h*3600+m*60+s

def parse_vtt(text,doc_id,title):
 lines=text.replace('\r\n','\n').lstrip('\ufeff').splitlines()
 if not lines or not lines[0].startswith('WEBVTT'):raise ValueError('WEBVTT header required')
 cues=[];i=1
 while i<len(lines):
  if lines[i].startswith(('NOTE','STYLE','REGION')):
   while i<len(lines) and lines[i].strip():i+=1
   continue
  if '-->' not in lines[i]:i+=1;continue
  left,right=lines[i].split('-->',1);start=seconds(left.strip());end=seconds(right.strip().split()[0]);i+=1;body=[]
  while i<len(lines) and lines[i].strip():body.append(lines[i].strip());i+=1
  clean=re.sub(r'<[^>]*>','', ' '.join(body)).strip()
  cues.append({'start':start,'end':end,'text':clean})
 doc={'id':doc_id,'title':title,'cues':cues};validate_docs([doc]);return doc

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('path');a.add_argument('--id',required=True);a.add_argument('--title',required=True)
 args=a.parse_args();print(json.dumps(parse_vtt(Path(args.path).read_text(),args.id,args.title),indent=2))
