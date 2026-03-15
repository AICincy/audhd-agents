import pytest
from pydantic import ValidationError
from runtime.schemas import ExecuteRequest, ExecuteResponse, EnergyLevel, SessionContext, CognitiveState, CrashStateResponse

def test_execute_request_max_length():
    with pytest.raises(ValidationError):
        ExecuteRequest(input_text="", cognitive_state=CognitiveState())
    
    with pytest.raises(ValidationError):
        ExecuteRequest(input_text="a" * 1048577, cognitive_state=CognitiveState())
        
    # Valid
    req = ExecuteRequest(input_text="hello", cognitive_state=CognitiveState())
    assert req.input_text == "hello"

def test_execute_request_skill_id_pattern():
    with pytest.raises(ValidationError):
        ExecuteRequest(input_text="hello", skill_id="../path/traversal", cognitive_state=CognitiveState())
        
    req = ExecuteRequest(input_text="hello", skill_id="valid-skill_123", cognitive_state=CognitiveState())
    assert req.skill_id == "valid-skill_123"

def test_execute_request_session_resume_validation():
    # Needs resume but no resume_from
    with pytest.raises(ValidationError, match="requires a resume_from"):
        ExecuteRequest(input_text="hello", cognitive_state=CognitiveState(session_context=SessionContext.RESUMED, resume_from=None))
        
    # Has resume_from but is NEW session
    with pytest.raises(ValidationError, match="provided but session_context is NEW"):
        ExecuteRequest(input_text="hello", cognitive_state=CognitiveState(session_context=SessionContext.NEW, resume_from="ckpt-123"))

def test_execute_response_negative_numbers():
    with pytest.raises(ValidationError):
        ExecuteResponse(energy_level=EnergyLevel.MEDIUM, input_tokens=-1)

def test_execute_response_crash_state():
    with pytest.raises(ValidationError, match="must be populated"):
        ExecuteResponse(energy_level=EnergyLevel.CRASH, crash_state=None)

    crash_obj = CrashStateResponse(checkpoint="x", resume_action="y", message="z")
    with pytest.raises(ValidationError, match="cannot be populated"):
        ExecuteResponse(energy_level=EnergyLevel.MEDIUM, crash_state=crash_obj)
        
    res = ExecuteResponse(energy_level=EnergyLevel.CRASH, crash_state=crash_obj)
    assert res.crash_state.checkpoint == "x"
