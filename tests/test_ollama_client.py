# tests/test_ollama_client.py
import pytest
import pytest_asyncio
from backend.ollama_client import OllamaClient

@pytest.mark.asyncio
async def test_chat_stream_returns_tokens(ollama_base_url):
    client = OllamaClient(base_url=ollama_base_url, model="dolphin3")
    tokens = []
    async for token in client.chat_stream([{"role": "user", "content": "Say hello in one word"}]):
        tokens.append(token)
    assert len(tokens) > 0
    full = "".join(tokens)
    assert len(full) > 0

@pytest.mark.asyncio
async def test_generate_returns_string(ollama_base_url):
    client = OllamaClient(base_url=ollama_base_url, model="dolphin3")
    result = await client.generate("Respond with only the word 'yes'")
    assert isinstance(result, str)
    assert len(result) > 0

@pytest.mark.asyncio
async def test_chat_stream_with_system_prompt(ollama_base_url):
    client = OllamaClient(base_url=ollama_base_url, model="dolphin3")
    messages = [
        {"role": "system", "content": "You only respond with numbers."},
        {"role": "user", "content": "What is 2+2?"},
    ]
    tokens = []
    async for token in client.chat_stream(messages):
        tokens.append(token)
    assert len(tokens) > 0
