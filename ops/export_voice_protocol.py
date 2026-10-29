"""Export token-only provider recordings for deterministic protocol regression."""
import argparse,json,re
from pathlib import Path

def export(directory):
    records=[]
    for path in sorted(directory.glob('*.json')):
        record=json.loads(path.read_text())
        allowed=record.get('allowed_lines',[])
        # Keep only finite protocol identifiers, never token meanings or questions.
        if any(re.search(r'[^\s।.?,;⟨⟩a-zA-Z0-9:_-]',line.replace('ের','')) for line in record.get('lines',[])):continue
        records.append({'header':record.get('header'),'lines':record.get('lines',[]),
                        'allowed_keys':sorted(set(key for line in allowed for key in re.findall(r'⟨([^⟨⟩]+)⟩',line))),
                        'fact_ids':record.get('fact_ids',[]),'error':record.get('error')})
    return {'format':1,'scope':'Recorded token protocol only; source facts and semantic accuracy require separate live evaluation.','records':records}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    args.output.write_text(json.dumps(export(args.directory),ensure_ascii=False,separators=(',',':'))+'\n')
