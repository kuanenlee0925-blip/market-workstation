"""Offline SDK tool wiring and captured-context checks; no provider calls."""
import asyncio
import base64
import json
from types import SimpleNamespace

from agents.tool_context import ToolContext
from backend import chart_agent as agent
from backend.store import Store


def snapshot(symbol='AAPL', mode='replay'):
    return agent.ChartSnapshot(symbol=symbol, mode=mode, interval='1m', chart_time='2026-11-09T14:32:00Z',
        image='data:image/png;base64,' + base64.b64encode(b'\x89PNG\r\n\x1a\nfixture').decode(),
        bars=[dict(timestamp='2026-11-09T14:30:00Z', complete=True), dict(timestamp='2026-11-09T14:31:00Z', complete=True)])


def test_tool_metadata_and_rule_only():
    assert [tool.name for tool in agent.assistant.tools] == ['read_decision_rules', 'assess_chart']
    context = dict(rules=agent.RULES, snapshot={}, tools=[], assessment=None)
    result = asyncio.run(agent.read_decision_rules.on_invoke_tool(ToolContext(context, tool_name='fixture_tool', tool_call_id='fixture', tool_arguments='{}'), '{}'))
    assert result == agent.RULES
    assert context['assessment'] is None
    assert [t['name'] for t in context['tools']] == ['read_decision_rules']
    assert agent.assess_chart.params_json_schema['properties'] == {}


def test_assessment_failure_is_not_wait(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    context = dict(rules=agent.RULES, snapshot=agent.snapshot_record(snapshot()), tools=[], assessment=None)
    result = asyncio.run(agent.assess_chart.on_invoke_tool(ToolContext(context, tool_name='fixture_tool', tool_call_id='fixture', tool_arguments='{}'), '{}'))
    assert result['status'] == 'error'
    assert 'choice' not in result
    assert result['snapshot_id'] == context['snapshot']['id']
    assert len(context['tools']) == 1


def test_conversation_context_and_persistence(monkeypatch, tmp_path):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only-not-a-credential')
    seen = []
    async def run(assistant, inputs, context, **kwargs):
        seen.append(inputs)
        await agent.read_decision_rules.on_invoke_tool(ToolContext(context, tool_name='fixture_tool', tool_call_id='fixture', tool_arguments='{}'), '{}')
        return SimpleNamespace(final_output='Controlled test response')
    monkeypatch.setattr(agent.Runner, 'run', run)
    store = Store(tmp_path/'chat.sqlite'); agent.init_chat(store)
    first = asyncio.run(agent.chat(store, agent.ChatRequest(message='What does WAIT mean?', snapshot=snapshot())))
    second = asyncio.run(agent.chat(store, agent.ChatRequest(message='Compare', conversation_id=first['conversation_id'], snapshot=snapshot())))
    assert len(seen[-1]) == 3
    assert second['tools'][0]['name'] == 'read_decision_rules'
    asyncio.run(agent.chat(store, agent.ChatRequest(message='Compare', conversation_id=first['conversation_id'], snapshot=snapshot('MSFT'))))
    assert len(seen[-1]) == 1
    assert store.db.execute('SELECT count(*) FROM chat_turns').fetchone()[0] == 3
    store.db.close()


def test_decision_provider_contract_and_failure(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'test-only-not-a-credential')
    captured = []
    class Client:
        def __init__(self, **kwargs): self.decisions = self
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def create(self, **kwargs):
            captured.append(kwargs)
            return SimpleNamespace(id='controlled-provider-fixture', answers=[SimpleNamespace(type='choice', name='chart_assessment', choice='WAIT', confidence=.44)])
    monkeypatch.setattr(agent, 'AsyncOpenAI', Client)
    result = asyncio.run(agent.request_decision(agent.snapshot_record(snapshot()), agent.RULES))
    assert result['choice'] == 'WAIT' and result['probability'] == .44
    assert captured[0]['input'][0]['content'][1]['type'] == 'input_image'
    assert captured[0]['questions'][0]['choices'] == agent.RULES['choices']
    async def fail(**kwargs): raise TimeoutError()
    monkeypatch.setattr(Client, 'create', lambda self, **kwargs: fail(**kwargs))
    result = asyncio.run(agent.request_decision(agent.snapshot_record(snapshot()), agent.RULES))
    assert result['status'] == 'error' and 'choice' not in result
