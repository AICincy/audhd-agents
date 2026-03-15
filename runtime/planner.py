import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import re

logger = logging.getLogger("audhd_agents.planner")

class RuntimePlanner:
    """
    Interprets natural language intent, maps it to capability workflows,
    and resolves abstract capabilities to concrete skills.
    """
    def __init__(self, rules_path: str = "graphs/routing_rules.yaml", graph_path: str = "graphs/capability_graph.yaml"):
        self.rules: List[Dict[str, Any]] = []
        self.chains: Dict[str, List[str]] = {}
        self._load_config(rules_path, graph_path)

    def _load_config(self, rules_path: str, graph_path: str):
        rules_file = Path(rules_path)
        if rules_file.exists():
            with open(rules_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    raise ValueError(f"Invalid format in {rules_path}: expected dictionary at root")
                self.rules = data.get("rules", [])
                if not isinstance(self.rules, list):
                    raise ValueError(f"Invalid format in {rules_path}: 'rules' must be a list")
        else:
            raise FileNotFoundError(f"Routing rules file not found: {rules_path}")
                
        graph_file = Path(graph_path)
        if graph_file.exists():
            with open(graph_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    raise ValueError(f"Invalid format in {graph_path}: expected dictionary at root")
                self.chains = data.get("chains", {})
                if not isinstance(self.chains, dict):
                    raise ValueError(f"Invalid format in {graph_path}: 'chains' must be a dictionary")
        else:
            raise FileNotFoundError(f"Capability graph file not found: {graph_path}")
    def plan_execution_chain(self, input_text: str) -> List[str]:
        """
        Map natural language input to a sequential chain of capabilities.
        Returns a list of capability strings.
        """
        if not input_text:
            return []

        input_lower = input_text.lower()
        
        # Match against routing rules triggers
        for rule in self.rules:
            triggers = rule.get("trigger", [])
            for trigger in triggers:
                # Use word boundary matching to prevent trigger ambiguity
                if re.search(r'\b' + re.escape(trigger.lower()) + r'\b', input_lower):
                    start_cap = rule.get("start_capability")
                    default_chain_name = rule.get("default_chain")
                    
                    if default_chain_name and default_chain_name in self.chains:
                        logger.info(f"Planner matched trigger '{trigger}' -> chain '{default_chain_name}'")
                        return list(self.chains[default_chain_name])
                    elif start_cap:
                        logger.info(f"Planner matched trigger '{trigger}' -> capability '{start_cap}'")
                        return [start_cap]                        
        # Default fallback if no rule match found
        logger.info("Planner found no matching routing rule. Returning empty chain.")
        return []

    def resolve_capability_to_skill(self, capability: str, skill_capabilities_map: Dict[str, List[str]]) -> Optional[str]:
        """
        Finds the most appropriate skill ID capable of handling the given capability.
        skill_capabilities_map is typically router.skill_capabilities.
        
        For initial capability-aware routing, this returns the first matching skill.
        Ultimately, this could incorporate cognitive state/tier matching to find the 'best' skill.
        """
        matching_skills = [skill_id for skill_id, caps in skill_capabilities_map.items() if capability in caps]
        if matching_skills:
            # Deterministic tie-breaking by sorting lexically
            return sorted(matching_skills)[0]
                
        logger.warning(f"Planner could not resolve capability '{capability}' to any known skill.")
        return None
