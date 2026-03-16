import pytest
import yaml
from runtime.planner import RuntimePlanner

@pytest.fixture
def temp_configs(tmp_path):
    rules_path = tmp_path / "routing_rules.yaml"
    graph_path = tmp_path / "capability_graph.yaml"
    return rules_path, graph_path

def test_planner_missing_files(temp_configs):
    rules_path, graph_path = temp_configs
    with pytest.raises(FileNotFoundError, match="Routing rules file not found"):
        RuntimePlanner(rules_path=str(rules_path), graph_path=str(graph_path))

def test_planner_invalid_format(temp_configs):
    rules_path, graph_path = temp_configs
    rules_path.write_text("rules: not_a_list", encoding="utf-8")
    with pytest.raises(ValueError, match="'rules' must be a list"):
        RuntimePlanner(rules_path=str(rules_path), graph_path=str(graph_path))
        
def test_planner_valid_matching(temp_configs):
    rules_path, graph_path = temp_configs
    rules_path.write_text(yaml.dump({"rules": [
        {"trigger": ["deploy"], "start_capability": "devops"},
        {"trigger": ["test"], "default_chain": "test_chain"}
    ]}), encoding="utf-8")
    graph_path.write_text(yaml.dump({"chains": {
        "test_chain": ["plan", "execute"]
    }}), encoding="utf-8")
    
    planner = RuntimePlanner(rules_path=str(rules_path), graph_path=str(graph_path))
    
    # Word boundary match
    assert planner.plan_execution_chain("Please deploy my code") == ["devops"]
    assert planner.plan_execution_chain("Please run a test") == ["plan", "execute"]
    
    # Ambiguous match prevention
    assert planner.plan_execution_chain("deployment") == [] # 'deploy' is not a whole word here

def test_planner_mutation_safety(temp_configs):
    rules_path, graph_path = temp_configs
    rules_path.write_text(yaml.dump({"rules": [
        {"trigger": ["test"], "default_chain": "test_chain"}
    ]}), encoding="utf-8")
    graph_path.write_text(yaml.dump({"chains": {
        "test_chain": ["plan", "execute"]
    }}), encoding="utf-8")
    
    planner = RuntimePlanner(rules_path=str(rules_path), graph_path=str(graph_path))
    chain1 = planner.plan_execution_chain("test")
    chain1.append("mutate")
    
    chain2 = planner.plan_execution_chain("test")
    assert chain2 == ["plan", "execute"]
    assert chain1 != chain2

def test_resolve_capability_to_skill(temp_configs):
    rules_path, graph_path = temp_configs
    rules_path.write_text(yaml.dump({"rules": []}), encoding="utf-8")
    graph_path.write_text(yaml.dump({"chains": {}}), encoding="utf-8")
    
    planner = RuntimePlanner(rules_path=str(rules_path), graph_path=str(graph_path))
    
    skill_map = {
        "skill_b": ["cap1", "cap2"],
        "skill_a": ["cap2"]
    }
    
    # Tie-breaking by lexical sort: skill_a should be returned for cap2
    assert planner.resolve_capability_to_skill("cap2", skill_map) == "skill_a"
    assert planner.resolve_capability_to_skill("cap1", skill_map) == "skill_b"
    assert planner.resolve_capability_to_skill("cap3", skill_map) is None
