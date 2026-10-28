"""Metadata-only timing logs. No question, transcript, audio, key or device ID."""
import json
import logging
import time
import uuid

class VoiceTimings:
    def __init__(self,started=None):
        self.started=started or time.monotonic();self.request_id=uuid.uuid4().hex;self.stages=[];self.pending=[]
    def mark(self,stage,started=None,ms=None):
        now=time.monotonic()
        item={'request_id':self.request_id,'stage':stage,'ms':round((now-started)*1000,2) if started is not None else (ms or 0),'elapsed_ms':round((now-self.started)*1000,2)}
        self.stages.append(item);self.pending.append(item);return item
    def events(self):
        pending,self.pending=self.pending,[]
        return ['event: progress\ndata: '+json.dumps(item)+'\n\n' for item in pending]
    def finish(self):
        present={item['stage'] for item in self.stages}
        for name in ['upload_done','ffmpeg','asr','clean+match','intent','tools','answer_text','tts_start','tts_done','sent']:
            if name not in present:self.stages.append({'request_id':self.request_id,'stage':name,'ms':0,'status':'skipped','elapsed_ms':round((time.monotonic()-self.started)*1000,2)})
        logging.getLogger('uvicorn.error').info('voice_timings %s',json.dumps({'request_id':self.request_id,'total_ms':round((time.monotonic()-self.started)*1000,2),'stages':self.stages},separators=(',',':')))
