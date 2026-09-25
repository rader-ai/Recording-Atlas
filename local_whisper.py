"""Optional local whisper.cpp transcription through its command line tool."""
from pathlib import Path
import os, shutil, subprocess, tempfile
from import_vtt import parse_vtt

def prerequisites(model_path=None, cli_path=None):
 model=Path(model_path or os.environ.get('WHISPER_MODEL_PATH','')).expanduser() if (model_path or os.environ.get('WHISPER_MODEL_PATH')) else None
 cli=cli_path or os.environ.get('WHISPER_CLI_PATH','whisper-cli')
 binary=shutil.which(cli)
 return {'ffmpeg':bool(shutil.which('ffmpeg')),'ffprobe':bool(shutil.which('ffprobe')),
         'whisper_cli':bool(binary),'model':bool(model and model.is_file()),
         'model_path':str(model) if model and model.is_file() else None}

def transcribe_local(source,doc_id,title,workdir,model_path=None,cli_path=None):
 checks=prerequisites(model_path,cli_path)
 if not all(checks[k] for k in ('ffmpeg','ffprobe','whisper_cli','model')):
  raise ValueError('Local transcription needs FFmpeg, whisper-cli, and WHISPER_MODEL_PATH pointing to a ggml model. See the Mac setup guide.')
 source=Path(source);model=checks['model_path'];cli=cli_path or os.environ.get('WHISPER_CLI_PATH','whisper-cli')
 with tempfile.TemporaryDirectory(prefix='recording-',dir=workdir) as temp:
  temp=Path(temp);wav=temp/'audio.wav';output=temp/'transcript'
  try:
   subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-i',str(source),'-ar','16000','-ac','1','-c:a','pcm_s16le',str(wav)],
                  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=300)
   if not wav.is_file() or not wav.stat().st_size:raise ValueError('Audio conversion produced no WAV file.')
   subprocess.run([cli,'--model',model,'--file',str(wav),'--output-vtt','--output-file',str(output),'--no-prints'],
                  stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=7200)
  except subprocess.TimeoutExpired:raise ValueError('Local transcription timed out. The import can be resumed.') from None
  except subprocess.CalledProcessError:raise ValueError('Local transcription failed. Check the model, media format, and available memory.') from None
  vtt=output.with_suffix('.vtt')
  if not vtt.is_file() or not vtt.stat().st_size:raise ValueError('Whisper produced no timed transcript. Check the audio and model.')
  return parse_vtt(vtt.read_text(encoding='utf-8'),doc_id,title)
