"""Add only privacy-preserving model-call metadata; never modify bank data."""
from ilma_api.db import engine
from ilma_api.voice_agent import prepare_schema

if __name__ == '__main__':
    try:
        prepare_schema(engine)
    except Exception:
        raise SystemExit('Agent audit schema could not be prepared. Verify access to the ilma database; no credentials printed.') from None
    print('Agent model-call metadata table is ready in ilma.')
