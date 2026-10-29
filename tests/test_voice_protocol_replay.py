"""Replay recorded finite tokens against synthetic meanings, with no paid APIs."""
import asyncio,json
from pathlib import Path
import httpx
from ilma_api.human_stream import generate
from ilma_api.human_tokens import FactToken,fill,TOKEN

def test_recorded_provider_protocol_is_free_and_bank_bound():
    bundle=json.loads(Path(__file__).with_name('voice_protocol_recordings.json').read_text())
    assert len(bundle['records'])>=350
    async def replay():
        rejected=0;sentences=0
        for record in bundle['records']:
            if record['error']:continue
            body=json.dumps({'header':record['header'],'lines':record['lines'],'question':'More?'},ensure_ascii=False)
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'choices':[{'message':{'content':body}}]}))) as client:
                draft=await generate({'line_choices':record['lines'],'fact_ids':record['fact_ids'],'question_choices':['More?']},[],client)
            assert not draft.error
            registry={}
            for key in record['allowed_keys']:
                # Handwritten stand-in meanings, not exported bank values.
                if key.startswith('bank:'):registry[key]=FactToken('Example bank',(),int(key.split(':')[1]),'bank')
                else:
                    fid=key.split(':',1)[1] if ':' in key else key
                    ids=(fid,) if fid in record['fact_ids'] else ()
                    registry[key]=FactToken('has an example sourced fact',ids,None)
            for line in draft.lines:
                sentences+=1
                assert all(key in registry for key in TOKEN.findall(line))
                try:fill(line,registry,draft.header.used,insurance=draft.header.intent=='insurance')
                except ValueError as error:
                    # Preserve recorded provider mistakes: CHECK must reject
                    # undeclared tokens rather than silently accepting them.
                    assert str(error)=='undeclared_fact'
                    rejected+=1
        assert sentences>350 and rejected/sentences<.05
    asyncio.run(replay())
