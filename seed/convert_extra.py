"""Read private extra-data CSVs and a previously supplied source document map."""
import argparse,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'api'))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1]/'.env')
from ilma_api.extra_data import convert
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input',nargs='?',default=os.environ.get('EXPORT_DIR'))
    p.add_argument('--documents',required=True,type=Path);p.add_argument('--checked-on',required=True)
    p.add_argument('--output',type=Path,default=Path(__file__).parent/'extra');a=p.parse_args()
    if not a.input:p.error('Provide input or EXPORT_DIR')
    print(convert(a.input,a.output,a.documents,a.checked_on))
