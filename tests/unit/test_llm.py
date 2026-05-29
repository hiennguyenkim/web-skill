import os
from unittest.mock import patch, MagicMock
import pytest

@pytest.mark.asyncio
@patch('google.generativeai.GenerativeModel')
async def test_llm_client_gemini_success(mock_model):
    from core.llm.client import LLMClient
    
    # Mocking GenerativeModel instance and async call
    mock_instance = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Gemini Answer"
    
    async def mock_generate(*args, **kwargs):
        return mock_resp
    
    mock_instance.generate_content_async.side_effect = mock_generate
    mock_model.return_value = mock_instance
    
    with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_MODEL": "gemini-1.5-flash"}):
        client = LLMClient(system_instruction="System prompt")
        response = await client.call_llm("User query")
        
        assert response == "Gemini Answer"
        mock_model.assert_called_with(model_name="gemini-1.5-flash", system_instruction="System prompt")

@pytest.mark.asyncio
@patch('google.generativeai.GenerativeModel')
async def test_llm_client_gemini_fallback(mock_model):
    from core.llm.client import LLMClient
    
    # Test fallback to synchronous generate when async generate fails
    mock_instance = MagicMock()
    
    # Async generate raises exception
    async def mock_generate_fail(*args, **kwargs):
        raise RuntimeError("Async error")
    mock_instance.generate_content_async.side_effect = mock_generate_fail
    
    # Sync generate succeeds
    mock_resp = MagicMock()
    mock_resp.text = "Sync Gemini Answer"
    mock_instance.generate_content.return_value = mock_resp
    mock_model.return_value = mock_instance
    
    with patch.dict(os.environ, {"LLM_PROVIDER": "gemini", "GEMINI_MODEL": "gemini-1.5-flash"}):
        client = LLMClient(system_instruction="System prompt")
        response = await client.call_llm("User query")
        
        assert response == "Sync Gemini Answer"
        mock_instance.generate_content.assert_called_once_with("User query")

@pytest.mark.asyncio
@patch('core.llm.client.OpenAI')
@patch('core.llm.client.AsyncOpenAI')
async def test_llm_client_deepseek_success(mock_async_openai, mock_sync_openai):
    from core.llm.client import LLMClient
    
    # Mocking OpenAI response
    mock_async_client = MagicMock()
    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "DeepSeek Answer"
    mock_resp.choices = [mock_choice]
    
    async def mock_create(*args, **kwargs):
        return mock_resp
    
    mock_async_client.chat.completions.create.side_effect = mock_create
    mock_async_openai.return_value = mock_async_client
    
    with patch.dict(os.environ, {"LLM_PROVIDER": "deepseek", "DEEPSEEK_API_KEY": "test_key", "DEEPSEEK_MODEL": "deepseek-chat"}):
        client = LLMClient(system_instruction="System prompt")
        response = await client.call_llm("User query")
        
        assert response == "DeepSeek Answer"
