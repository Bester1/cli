"""Tests for --sequence mode: execute multiple requests from STDIN."""
import pytest
from io import StringIO
from unittest.mock import patch, MagicMock

from httpie.core import run_sequence_mode, program
from httpie.context import Environment
from httpie.status import ExitStatus


class TestSequenceMode:
    """Test the --sequence feature for executing multiple requests from STDIN."""

    def test_sequence_empty_stdin(self):
        """Sequence mode with empty STDIN should return error."""
        env = Environment()
        env.stdin = StringIO('')
        
        args = MagicMock()
        args.sequence = True
        
        result = run_sequence_mode(args, env)
        
        assert result == ExitStatus.ERROR

    def test_sequence_only_comments(self):
        """Sequence mode with only comments should return error."""
        env = Environment()
        env.stdin = StringIO('# This is a comment\n# Another comment\n')
        
        args = MagicMock()
        args.sequence = True
        
        result = run_sequence_mode(args, env)
        
        assert result == ExitStatus.ERROR

    def test_sequence_parses_request_lines(self):
        """Sequence mode should parse request lines from STDIN."""
        env = Environment()
        env.stdin = StringIO('GET http://example.com\nPOST http://example.com data=test\n')
        env.stdout = StringIO()
        env.stdout_isatty = False
        
        args = MagicMock()
        args.sequence = True
        
        # Mock _program to avoid actual HTTP requests
        with patch('httpie.core._program') as mock_program:
            mock_program.return_value = ExitStatus.SUCCESS
            
            result = run_sequence_mode(args, env)
            
            # Should have called _program twice (once per request)
            assert mock_program.call_count == 2
            assert result == ExitStatus.SUCCESS

    def test_sequence_skips_empty_lines(self):
        """Sequence mode should skip empty lines."""
        env = Environment()
        env.stdin = StringIO('\nGET http://example.com\n\nPOST http://example.com\n\n')
        env.stdout = StringIO()
        env.stdout_isatty = False
        
        args = MagicMock()
        args.sequence = True
        
        with patch('httpie.core._program') as mock_program:
            mock_program.return_value = ExitStatus.SUCCESS
            
            result = run_sequence_mode(args, env)
            
            # Should have called _program twice (empty lines skipped)
            assert mock_program.call_count == 2

    def test_sequence_handles_keyboard_interrupt(self):
        """Sequence mode should handle KeyboardInterrupt gracefully."""
        env = Environment()
        
        # Simulate KeyboardInterrupt during stdin read
        class InterruptingStringIO(StringIO):
            def __iter__(self):
                return self
            def __next__(self):
                raise KeyboardInterrupt()
        
        env.stdin = InterruptingStringIO()
        env.stdout = StringIO()
        
        args = MagicMock()
        args.sequence = True
        
        result = run_sequence_mode(args, env)
        
        assert result == ExitStatus.ERROR_CTRL_C

    def test_sequence_propagates_error_status(self):
        """Sequence mode should return error if any request fails."""
        env = Environment()
        env.stdin = StringIO('GET http://example.com\nPOST http://example.com\n')
        env.stdout = StringIO()
        env.stdout_isatty = False
        
        args = MagicMock()
        args.sequence = True
        
        with patch('httpie.core._program') as mock_program:
            # First call succeeds, second fails
            mock_program.side_effect = [ExitStatus.SUCCESS, ExitStatus.ERROR]
            
            result = run_sequence_mode(args, env)
            
            assert result == ExitStatus.ERROR

    def test_sequence_handles_request_exception(self):
        """Sequence mode should handle exceptions during request execution."""
        env = Environment()
        env.stdin = StringIO('GET http://example.com\n')
        env.stdout = StringIO()
        env.stdout_isatty = False
        
        args = MagicMock()
        args.sequence = True
        
        with patch('httpie.core._program') as mock_program:
            mock_program.side_effect = Exception('Request failed')
            
            result = run_sequence_mode(args, env)
            
            assert result == ExitStatus.ERROR

    def test_sequence_executes_multiple_requests(self):
        """Sequence mode should execute multiple requests sequentially."""
        env = Environment()
        env.stdin = StringIO('GET http://example.com\nPOST http://example.com\nPUT http://example.com\n')
        env.stdout = StringIO()
        env.stdout_isatty = False
        
        args = MagicMock()
        args.sequence = True
        
        with patch('httpie.core._program') as mock_program:
            mock_program.return_value = ExitStatus.SUCCESS
            
            result = run_sequence_mode(args, env)
            
            # Should have called _program 3 times for 3 requests
            assert mock_program.call_count == 3
            assert result == ExitStatus.SUCCESS
