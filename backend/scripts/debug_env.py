from pathlib import Path
import os

dotenv = Path(__file__).resolve().parent.parent / '.env'
print('dotenv path:', dotenv, 'exists=', dotenv.exists())
try:
    with dotenv.open('rb') as f:
        for i, line in enumerate(f, 1):
            print(f'LINE {i}:', repr(line))
except Exception as e:
    print('read error', e)

print('\nENV from os.environ:')
print('ODDS_API_URL:', repr(os.environ.get('ODDS_API_URL')))
print('ODDS_API_KEY:', repr(os.environ.get('ODDS_API_KEY')))

from dotenv import load_dotenv
load_dotenv(dotenv)
print('\nAfter load_dotenv:')
print('ODDS_API_URL:', repr(os.environ.get('ODDS_API_URL')))
print('ODDS_API_KEY:', repr(os.environ.get('ODDS_API_KEY')))
