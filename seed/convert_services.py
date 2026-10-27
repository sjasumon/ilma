import argparse
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'api'))
from ilma_api.export_seed import convert
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1]/'.env')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', nargs='?', type=Path, default=os.environ.get('EXPORT_DIR'))
    parser.add_argument('--output', type=Path, default=Path(__file__).parent)
    parser.add_argument('--version', help='Export version, otherwise inferred from input directory name')
    args = parser.parse_args()
    if args.input is None:parser.error('Provide an input directory or EXPORT_DIR')
    convert(args.input, args.output, services=True, services_version=args.version)
