"""
Test suite for large content handling issues identified in session logs

Tests specific problems with:
- Very long tool results from WebSearch
- Content truncation and splitting
- Non-JSON line processing
- Session updates with large content
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


class TestLargeContentHandling:
    
    def setup_method(self):
        """Setup test fixtures"""
        self.pipe = Pipe()
        
    def test_large_websearch_tool_result(self):
        """Test handling of very large WebSearch tool results like in the session log"""
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": "OpenWebUIのThinking表示ってデフォルトで開いてるけどデフォルトを閉じるようにすることってできる?"
                }
            ]
        }
        
        # Create a very long tool result similar to the one in the session log
        large_tool_result = """Web search results for query: "OpenWebUI thinking display default closed collapse settings"

I'll search for information about OpenWebUI thinking display settings, specifically about default closed/collapse settings.

Links: [{"title":"How to set OpenWebUI to automatically expand the chain-of-thought by default? · open-webui/open-webui · Discussion #9706","url":"https://github.com/open-webui/open-webui/discussions/9706"},{"title":"Collapsible Thought Filter Function • Open WebUI Community","url":"https://openwebui.com/f/projectmoon/collapsible_thought_filter"},{"title":"<thinking> breaks the current thinking feature. · Issue #9421 · open-webui/open-webui","url":"https://github.com/open-webui/open-webui/issues/9421"},{"title":"Better <think> block rendering for DeepSeek-R1 and similar · Issue #8706 · open-webui/open-webui","url":"https://github.com/open-webui/open-webui/issues/8706"},{"title":"Functions • Open WebUI Community","url":"https://openwebui.com/functions"},{"title":"How to set OpenWebUI to automatically expand the chain-of-thought by default? · Issue #9694 · open-webui/open-webui","url":"https://github.com/open-webui/open-webui/issues/9694"},{"title":"Releases · open-webui/open-webui","url":"https://github.com/open-webui/open-webui/releases"},{"title":"ThinkingUI Function • Open WebUI Community","url":"https://openwebui.com/f/rjalynski/thinkingui"},{"title":"Thinking Filter Function • Open WebUI Community","url":"https://openwebui.com/f/trollek/thinking_filter"},{"title":"Thinking and Output Tag Function • Open WebUI Community","url":"https://openwebui.com/f/yuchen4645/Think_And_Generate"}]

Based on the search results, I found relevant information about OpenWebUI's thinking display settings and how it handles collapsed/expanded states by default.

By default, the chain-of-thought is collapsed and requires a click to expand. This is a common issue that users have been discussing in the OpenWebUI community.

The search results reveal several key points about OpenWebUI's thinking display behavior:

1. **Default Behavior**: By default, the chain-of-thought is collapsed and requires a click to expand. How can I set it to be expanded by default?

2. **Collapsible Thought Filters**: There are community-created filters available, such as the "Collapsible Thought Filter Function" that can "Collapse AI thought processes for readability." This filter appears to be "Disabled by default."

3. **Proposed Solutions**: In the GitHub discussions, there are suggestions for better handling of thinking blocks. The proposed solution includes rendering the <think> block distinctly from the normal response, with the block being collapsible. By default, the block could be collapsed, with an indicator to expand it for users who are interested in understanding the detailed reasoning process.

4. **Configuration Options**: Some users have suggested using a toggle option in the settings to enable or disable <think> block rendering entirely, or highlighting <think> blocks with simple visual markers (e.g., italics or a different font) instead of full collapsibility.

5. **Technical Implementation**: The search results show that users have been trying to modify the behavior by editing files like "/app/build/_app/immutable/chunks/Collapsible.an7Zv-qh.js", though users reported that even after finding and modifying the file, "the thinking process is still folded and not opened directly."

The search results indicate that OpenWebUI's default behavior is to collapse thinking/chain-of-thought sections, and while there are ongoing discussions and feature requests to make this configurable or change the default behavior, there doesn't appear to be a built-in setting to change this default in the current version. Users are exploring various workarounds including custom filters and direct file modifications."""

        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            # Simulate the exact sequence from the problematic session log
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"c21f5147-a6e3-4a7f-85e8-aa86198672d6","tools":["Task","Bash","Glob","Grep","LS","Read","Edit","MultiEdit","Write","NotebookRead","NotebookEdit","WebFetch","TodoRead","TodoWrite","WebSearch"],"mcp_servers":[]}',
                b'data: {"type":"assistant","message":{"id":"msg_013ruqULi7gTBVv5SBqGXaJ8","content":[{"type":"text","text":"I\'ll search for information about OpenWebUI\'s thinking display default settings and how to change them."}],"stop_reason":"tool_use"}}',
                b'data: {"type":"assistant","message":{"content":[{"type":"tool_use","id":"toolu_01WUiziAbkorko374UcgUx9s","name":"WebSearch","input":{"query":"OpenWebUI thinking display default closed collapse settings"}}]}}',
                f'data: {{"type":"user","message":{{"role":"user","content":[{{"tool_use_id":"toolu_01WUiziAbkorko374UcgUx9s","type":"tool_result","content":"{large_tool_result}"}}]}}}}'.encode('utf-8'),
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"Final response content"}],"stop_reason":"end_turn"}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should handle large content without "Non-JSON line" errors
            assert 'session_id=c21f5147-a6e3-4a7f-85e8-aa86198672d6' in result_text
            assert 'WebSearch' in result_text
            assert 'Final response content' in result_text
            # Should NOT contain error indicators for properly formatted JSON
            assert '💩' not in result_text or result_text.count('💩') == 0
            
    def test_session_id_update_with_large_content(self):
        """Test session ID updates when processing large content"""
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
            # Simulate session update during large content processing
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"c21f5147-a6e3-4a7f-85e8-aa86198672d6","tools":["WebSearch"]}',
                b'data: {"type":"assistant","message":{"content":[{"type":"tool_use","name":"WebSearch","input":{"query":"large query"}}]}}',
                f'data: {{"type":"user","message":{{"content":[{{"type":"tool_result","content":"{"x" * 2000}"}}]}}}}'.encode('utf-8'),
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"Final answer"}],"stop_reason":"end_turn"}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should update session ID correctly
            assert 'session_id=c21f5147-a6e3-4a7f-85e8-aa86198672d6' in result_text
            # Should handle large content properly
            assert 'Final answer' in result_text
            # Verify original session was sent in request
            args, kwargs = mock_post.call_args
            assert kwargs['json']['session_id'] == '17398555-6e9c-4b13-a0b9-345589f13dda'
            
    def test_truncation_of_very_long_tool_results(self):
        """Test that very long tool results are truncated appropriately"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        # Create content longer than truncation limit (500 chars)
        very_long_content = "x" * 1000
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"test-id"}',
                f'data: {{"type":"user","message":{{"content":[{{"type":"tool_result","content":"{very_long_content}"}}]}}}}'.encode('utf-8')
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should contain truncation indicator
            assert '(truncated)' in result_text
            # Should not contain the full long content
            lines_with_content = [line for line in result if 'xxxxxxxx' in line]
            if lines_with_content:
                assert len(lines_with_content[0]) < 600  # Should be truncated
                
    def test_handling_of_split_json_content(self):
        """Test handling when JSON content appears to be split across lines"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            # Simulate content that looks like it might be split JSON
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"test-id"}',
                b'data: {"type":"user","message":{"content":[{"type":"tool_result","content":"Some very long content that appears to be truncated and might cause issues by de',
                b'fault. This continuation should be handled properly."}]}}',
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"Response"}],"stop_reason":"end_turn"}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should handle the sequence without errors
            assert 'session_id=test-id' in result_text
            # Should show appropriate error handling for invalid JSON
            error_indicators = result_text.count('⚠️')
            assert error_indicators >= 1  # Should detect JSON parsing errors
            
    def test_websearch_with_unicode_content(self):
        """Test WebSearch results containing Unicode characters"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        unicode_content = "Web search results: 🛠️ Troubleshooting | Open WebUI ⭐ Features | 💭 Thought processing"
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"test-id"}',
                f'data: {{"type":"user","message":{{"content":[{{"type":"tool_result","content":"{unicode_content}"}}]}}}}'.encode('utf-8'),
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"Response with unicode"}],"stop_reason":"end_turn"}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should handle Unicode properly
            assert '🛠️' in result_text
            assert '⭐' in result_text  
            assert '💭' in result_text
            assert 'Response with unicode' in result_text
            
    def test_multiple_tool_results_processing(self):
        """Test processing multiple consecutive tool results"""
        body = {"messages": [{"role": "user", "content": "test"}]}
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"test-id"}',
                b'data: {"type":"assistant","message":{"content":[{"type":"tool_use","name":"WebSearch","input":{"query":"query1"}}]}}',
                b'data: {"type":"user","message":{"content":[{"type":"tool_result","content":"First search result"}]}}',
                b'data: {"type":"assistant","message":{"content":[{"type":"tool_use","name":"WebSearch","input":{"query":"query2"}}]}}',
                b'data: {"type":"user","message":{"content":[{"type":"tool_result","content":"Second search result"}]}}',
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"Final answer"}],"stop_reason":"end_turn"}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should process all tool results
            assert 'WebSearch' in result_text
            assert 'First search result' in result_text
            assert 'Second search result' in result_text
            assert 'Final answer' in result_text
            
    def test_dangerously_skip_permissions_with_large_content(self):
        """Test dangerously-skip-permissions setting with large content processing"""
        body = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "session_id=test-session\ndangerously-skip-permissions=false"
                },
                {
                    "role": "user", 
                    "content": "Process large content"
                }
            ]
        }
        
        large_content = "x" * 800  # Large but under truncation limit
        
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"new-session"}',
                f'data: {{"type":"user","message":{{"content":[{{"type":"tool_result","content":"{large_content}"}}]}}}}'.encode('utf-8'),
                b'data: {"type":"assistant","message":{"content":[{"type":"text","text":"Processed"}],"stop_reason":"end_turn"}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should inherit and use the dangerously-skip-permissions setting
            assert 'dangerously-skip-permissions=false' in result_text
            assert 'session_id=new-session' in result_text
            # Verify settings were passed to request
            args, kwargs = mock_post.call_args
            assert kwargs['json']['dangerously-skip-permissions'] == False

    def test_actual_session_log_scenario(self):
        """Test the exact scenario from the problematic session log"""
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
        
        # Recreate the exact problematic sequence from the session log
        with patch.object(claude_code.requests, 'post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.iter_lines.return_value = [
                b'data: {"type":"system","subtype":"init","session_id":"c21f5147-a6e3-4a7f-85e8-aa86198672d6","tools":["Task","Bash","Glob","Grep","LS","Read","Edit","MultiEdit","Write","NotebookRead","NotebookEdit","WebFetch","TodoRead","TodoWrite","WebSearch"],"mcp_servers":[]}',
                b'data: {"type":"assistant","message":{"id":"msg_013ruqULi7gTBVv5SBqGXaJ8","type":"message","role":"assistant","model":"claude-opus-4-20250514","content":[{"type":"text","text":"I\'ll search for information about OpenWebUI\'s thinking display default settings and how to change them."}],"stop_reason":"tool_use","stop_sequence":null,"usage":{"input_tokens":4,"cache_creation_input_tokens":14889,"cache_read_input_tokens":0,"output_tokens":81,"service_tier":"standard"},"ttftMs":5102},"session_id":"c21f5147-a6e3-4a7f-85e8-aa86198672d6"}',
                b'data: {"type":"assistant","message":{"id":"msg_013ruqULi7gTBVv5SBqGXaJ8","type":"message","role":"assistant","model":"claude-opus-4-20250514","content":[{"type":"tool_use","id":"toolu_01WUiziAbkorko374UcgUx9s","name":"WebSearch","input":{"query":"OpenWebUI thinking display default closed collapse settings"}}],"stop_reason":"tool_use","stop_sequence":null,"usage":{"input_tokens":4,"cache_creation_input_tokens":14889,"cache_read_input_tokens":0,"output_tokens":81,"service_tier":"standard"},"ttftMs":5102},"session_id":"c21f5147-a6e3-4a7f-85e8-aa86198672d6"}',
                # Simulate the actual problem: JSON split across multiple data: lines
                b'data: {"type":"user","message":{"role":"user","content":[{"tool_use_id":"toolu_01WUiziAbkorko374UcgUx9s","type":"tool_result","content":"Web search results with links by de',
                b'data: fault. Default behavior: collapsed. Multiple solutions available."}],"session_id":"c21f5147-a6e3-4a7f-85e8-aa86198672d6"}}',
                b'data: {"type":"assistant","message":{"id":"msg_01CuRgTiNvCo7NdJYvUj5EN7","content":[{"type":"text","text":"Final response"}],"stop_reason":"end_turn"}}'
            ]
            mock_post.return_value = mock_response
            
            result = list(self.pipe.pipe(body, {}))
            result_text = ''.join(result)
            
            # Should handle the session update properly
            assert 'session_id=c21f5147-a6e3-4a7f-85e8-aa86198672d6' in result_text
            # Should process the WebSearch tool
            assert 'WebSearch' in result_text  
            # Should handle the final response
            assert 'Final response' in result_text
            
            # With the buffering fix, this should now work properly:
            # - JSON should be successfully parsed across multiple lines
            # - Tool result should be displayed properly
            assert '✅ Tool Result:' in result_text  # Should show tool result
            assert 'Web search results' in result_text  # Tool result content
            assert 'Default behavior: collapsed' in result_text  # Full content
            # Should NOT have parsing errors with proper buffering
            parsing_errors = result_text.count('⚠️ JSON parse error:')
            assert parsing_errors == 0  # Should be 0 with working buffering


if __name__ == "__main__":
    pytest.main([__file__])