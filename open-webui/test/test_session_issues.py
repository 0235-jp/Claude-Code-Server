"""
Specific tests for session management issues identified in logs

Tests edge cases that occur during real usage, particularly:
- Session ID updates during processing
- Non-JSON line handling  
- Buffer management for partial JSON
- Error recovery scenarios
"""
import json
import pytest
import os
import importlib.util
from unittest.mock import Mock, patch

# Import claude-code.py as a module
spec = importlib.util.spec_from_file_location("claude_code", 
    os.path.join(os.path.dirname(__file__), '..', 'functions', 'claude-code.py'))
claude_code = importlib.util.module_from_spec(spec)
spec.loader.exec_module(claude_code)

Pipe = claude_code.Pipe


class TestSessionIssues:
    
    def setup_method(self):
        self.pipe = Pipe()
        
    def test_session_resume_scenario(self):
        """
        Test scenario from logs: session update during resume
        Updating session after resume: 17398555-6e9c-4b13-a0b9-345589f13dda -> 54281ff0-bffa-497e-9526-fa641fe91478
        """
        body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "session_id=17398555-6e9c-4b13-a0b9-345589f13dda\nPrevious response"
                },
                {
                    "role": "user",
                    "content": "OpenWebUIのThinking表示ってデフォルトで開いてるけどデフォルトを閉じるようにすることってできる?"
                }
            ]
        }
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            # Simulate the exact sequence from logs
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"54281ff0-bffa-497e-9526-fa641fe91478","tools":["Task","Bash"],"mcp_servers":[]}',
                b'data: {"type":"assistant","message":{"id":"msg_test","content":[{"type":"text","text":"I\'ll search for information about changing the default state"}]}}',
                b'data: {"type":"assistant","message":{"content":[{"type":"tool_use","id":"tool_test","name":"WebSearch","input":{"query":"OpenWebUI thinking display"}}]}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should handle session update properly
            assert 'session_id=54281ff0-bffa-497e-9526-fa641fe91478' in result_text
            assert 'WebSearch' in result_text
            
            # Verify original session was sent in request
            args, kwargs = mock_post.call_args
            assert kwargs['json']['session_id'] == '17398555-6e9c-4b13-a0b9-345589f13dda'
            
    def test_non_json_line_from_logs(self):
        """
        Test handling of exact non-JSON line from logs:
        'Non-JSON line: "💭 Thought for X seconds" panels'
        """
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"test-id"}',
                '"💭 Thought for X seconds" panels\n\nCurrently, there isn\'t a native setting'.encode('utf-8'),
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"response"}],"stop_reason":"end_turn"}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Non-JSON content should be handled and marked
            assert '💩' in result_text
            assert '💭 Thought for X seconds' in result_text
            assert 'response' in result_text
            
    def test_partial_json_buffering(self):
        """Test JSON buffering for complete JSON responses"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            # Test normal JSON processing (the current implementation handles complete JSON per line)
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"test-session","tools":["Task","Bash"]}',
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"Complete response"}],"stop_reason":"end_turn"}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should properly handle complete JSON 
            assert 'session_id=test-session' in result_text
            assert 'Complete response' in result_text
            
    def test_error_recovery_during_streaming(self):
        """Test error recovery when JSON parsing fails mid-stream"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"test-id"}',
                b'data: {"malformed": invalid json}',  # Malformed JSON
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"Recovery response"}],"stop_reason":"end_turn"}}'
            ]
            mock_post.return_value = mock_response
            
            # Should not crash, should continue processing
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            assert 'session_id=test-id' in result_text
            # The implementation should recover and process the valid JSON after the error
            assert 'Recovery response' in result_text
            assert '⚠️' in result_text  # Error indicator should be present
            
    def test_thinking_mode_breaking_issue(self):
        """
        Test the issue mentioned in logs:
        '<thinking> breaks the current thinking feature'
        'the closing </thinking> does not end the thinking mode'
        """
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"test-id"}',
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"Thinking content"}],"stop_reason":"tool_use"}}',
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"More thinking"}],"stop_reason":"tool_use"}}',
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"Final answer"}],"stop_reason":"end_turn"}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should properly close thinking tag
            thinking_opens = result_text.count('<thinking>')
            thinking_closes = result_text.count('</thinking>')
            assert thinking_opens == thinking_closes == 1
            
    def test_settings_inheritance_complex_scenario(self):
        """Test complex settings inheritance from conversation history"""
        body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": 'session_id=old-session\ndangerously-skip-permissions=false\nallowedTools=["Read","Write"]'
                },
                {
                    "role": "user",
                    "content": "intermediate message"
                },
                {
                    "role": "assistant", 
                    "content": 'session_id=newer-session\ndisallowedTools=["Bash"]'
                },
                {
                    "role": "user",
                    "content": "allowedTools=[\"Grep\"] test command"
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
            
            # Should use most recent session ID from assistant messages  
            # The code searches from the end backwards, so it finds newer-session first
            assert request_data['session_id'] == 'newer-session'
            assert request_data['dangerously-skip-permissions'] == False
            assert request_data['allowedTools'] == ['Grep']  # Current message overrides
            assert request_data['disallowedTools'] == ['Bash']  # Inherited
            
    def test_unicode_handling_in_streaming(self):
        """Test Unicode character handling in streaming responses"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"test-id"}',
                'data: {"type":"assistant","message":{"content":[{"type":"text","text":"🛠️ Troubleshooting"}],"stop_reason":"tool_use"}}'.encode('utf-8'),
                'data: {"type":"assistant","message":{"content":[{"type":"text","text":"⭐ Features"}],"stop_reason":"end_turn"}}'.encode('utf-8')
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should handle Unicode properly
            assert '🛠️' in result_text
            assert '⭐' in result_text