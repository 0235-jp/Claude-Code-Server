"""
Test suite for claude-code.py OpenWebUI function

Tests session management, JSON parsing, and error handling issues
identified from session logs.
"""
import importlib.util
import pytest
import sys
import os
import re
from unittest.mock import Mock, patch

# Add the functions directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'functions'))

# Import claude-code.py as a module
import importlib.util
spec = importlib.util.spec_from_file_location("claude_code", 
    os.path.join(os.path.dirname(__file__), '..', 'functions', 'claude-code.py'))
claude_code = importlib.util.module_from_spec(spec)
spec.loader.exec_module(claude_code)

Pipe = claude_code.Pipe


class TestPipe:
    
    def setup_method(self):
        """Setup test fixtures"""
        self.pipe = Pipe()
        
    def test_pipe_initialization(self):
        """Test pipe initialization and valves setup"""
        assert self.pipe.valves.BASE_URL == "http://localhost:3000"
        
    def test_empty_messages_handling(self):
        """Test handling of empty messages"""
        body = {"messages": []}
        user = {}
        result = list(self.pipe.pipe(body, user))
        # pipe method returns a generator, need to check if it yields the error
        assert len(result) == 1 and result[0] == "Error: No messages provided"
        
    def test_session_id_extraction_from_history(self):
        """Test session ID extraction from conversation history"""
        body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "session_id=17398555-6e9c-4b13-a0b9-345589f13dda\nSome response"
                },
                {
                    "role": "user", 
                    "content": "New message"
                }
            ]
        }
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"54281ff0-bffa-497e-9526-fa641fe91478"}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            
            # Verify session_id was passed in request
            args, kwargs = mock_post.call_args
            request_data = kwargs['json']
            assert request_data['session_id'] == "17398555-6e9c-4b13-a0b9-345589f13dda"
            
    def test_settings_inheritance_from_history(self):
        """Test settings inheritance from previous messages"""
        body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": 'session_id=test-session\ndangerously-skip-permissions=true\nallowedTools=["Bash","Read"]'
                },
                {
                    "role": "user",
                    "content": "Continue with previous settings"
                }
            ]
        }
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = []
            mock_post.return_value = mock_response
            
            list(self.pipe.pipe(body, {}))
            
            args, kwargs = mock_post.call_args
            request_data = kwargs['json']
            assert request_data['dangerously-skip-permissions'] == True
            assert request_data['allowedTools'] == ["Bash", "Read"]
            
    def test_json_parsing_with_buffer(self):
        """Test JSON parsing with buffering for incomplete lines"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            # Simulate partial JSON that needs buffering
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system",',
                b'"subtype":"init","session_id":"test-id"}'
            ]
            mock_post.return_value = mock_response
            
            # This should not raise an exception despite incomplete JSON
            result = list(self.pipe.pipe(body, {}))
            
    def test_non_json_line_handling(self):
        """Test handling of non-JSON lines that cause processing issues"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"test-id"}',
                b'Non-JSON line that should be handled gracefully',
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"Final response"}],"stop_reason":"end_turn"}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            
            # Should contain session output and final response
            result_text = ''.join(result)
            assert 'session_id=test-id' in result_text
            assert 'Final response' in result_text
            assert '💩' in result_text  # Non-JSON line should be marked
            
    def test_thinking_tag_management(self):
        """Test proper opening/closing of thinking tags"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"test-id"}',
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"Thinking..."}],"stop_reason":"tool_use"}}',
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"Final answer"}],"stop_reason":"end_turn"}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should have opening and closing thinking tags
            assert '<thinking>' in result_text
            assert '</thinking>' in result_text
            
    def test_session_update_handling(self):
        """Test handling of session updates during processing"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"new-session-id"}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should output the new session ID
            assert 'session_id=new-session-id' in result_text
            
    def test_error_response_handling(self):
        """Test handling of error responses from Claude Code Server"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.json.return_value = {"error": "Internal server error"}
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            assert "500" in result_text
            assert "Internal server error" in result_text
            
    def test_content_truncation(self):
        """Test content truncation for long responses"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        long_content = "x" * 1000  # Content longer than 500 chars
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"test-id"}',
                f'data: {{"type":"assistant","message":{{"content":[{{"type":"text","text":"{long_content}"}}],"stop_reason":"tool_use"}}}}'.encode()
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Content should be truncated
            assert "(truncated)" in result_text
            assert len([line for line in result if "🤖<" in line][0]) < 600
            
    def test_tool_use_display(self):
        """Test display of tool usage information"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"test-id"}',
                b'data: {"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash","input":{"command":"ls"}}],"stop_reason":"tool_use"}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            assert "🔧 Using Bash:" in result_text
            assert "ls" in result_text
            
    def test_regex_pattern_extraction(self):
        """Test regex patterns for extracting settings from messages"""
        # Test session ID extraction
        content = "session_id=17398555-6e9c-4b13-a0b9-345589f13dda\nSome content"
        import re
        session_match = re.search(r'session_id=([a-f0-9-]+)', content)
        assert session_match.group(1) == "17398555-6e9c-4b13-a0b9-345589f13dda"
        
        # Test settings extraction
        content = 'dangerously-skip-permissions=true\nallowedTools=["Bash","Read"]'
        danger_match = re.search(r'dangerously-skip-permissions=(\w+)', content)
        allowed_match = re.search(r'allowedTools=\[([^\]]+)\]', content)
        
        assert danger_match.group(1) == "true"
        assert allowed_match.group(1) == '"Bash","Read"'


if __name__ == "__main__":
    pytest.main([__file__])