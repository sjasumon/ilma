"""Normalize an owner-supplied incident archive; raw inputs stay private."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))
from ilma_api.incident_export import convert

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--output',type=Path,default=Path(__file__).parent/'incidents')
    parser.add_argument('--checked-on',required=True)
    args=parser.parse_args()
    result=convert(args.input,args.output,args.checked_on)
    print('Normalized approved incident data:',{key:len(value) for key,value in result.items()})
