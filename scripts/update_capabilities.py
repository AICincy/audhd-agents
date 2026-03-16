import os
import yaml
from pathlib import Path

# Mapping of primary capabilities to skill directories
CAPABILITY_MAP = {
    "research": [
        "design-ux-researcher", 
        "product-trend-researcher", 
        "testing-evidence-collector"
    ],
    "analyze": [
        "engineering-code-reviewer", 
        "engineering-incident-response-commander", 
        "product-behavioral-nudge-engine", 
        "testing-test-results-analyzer"
    ],
    "synthesize": [
        "product-feedback-synthesizer", 
        "support-analytics-reporter", 
        "support-executive-summary-generator"
    ],
    "generate": [
        "engineering-rapid-prototyper", 
        "engineering-frontend-developer", 
        "engineering-devops-automator", 
        "engineering-git-workflow-master", 
        "engineering-ai-engineer", 
        "engineering-technical-writer", 
        "corporate-training", 
        "design-image-prompt-engineer", 
        "design-inclusive-visuals-specialist", 
        "design-ui-designer", 
        "design-visual-storyteller", 
        "marketing-content-creator", 
        "marketing-linkedin-content-creator", 
        "specialized-developer-advocate", 
        "specialized-document-generator", 
        "specialized-mcp-builder"
    ],
    "transform": [
        "engineering-ai-data-remediation", 
        "engineering-data-engineer", 
        "lsp-index-engineer"
    ],
    "evaluate": [
        "testing-api-tester", 
        "testing-performance-benchmarker", 
        "testing-reality-checker", 
        "testing-tool-evaluator", 
        "specialized-model-qa", 
        "project-management-experiment-tracker", 
        "design-brand-guardian"
    ],
    "plan": [
        "engineering-software-architect", 
        "engineering-backend-architect", 
        "product-sprint-prioritizer", 
        "project-management-project-shepherd", 
        "project-manager-senior", 
        "design-ux-architect"
    ],
    "orchestrate": [
        "agents-orchestrator"
    ],
    "audit": [
        "compliance-auditor", 
        "automation-governance", 
        "engineering-security-engineer", 
        "testing-accessibility-auditor", 
        "support-legal-compliance-checker"
    ],
    "optimize": [
        "engineering-autonomous-optimization", 
        "engineering-database-optimizer", 
        "testing-workflow-optimizer"
    ]
}

def main():
    skill_to_cap = {}
    for cap, skills in CAPABILITY_MAP.items():
        for skill in skills:
            skill_to_cap[skill] = cap

    skills_dir = Path("skills")
    updated_count = 0
    
    for skill_yaml_path in skills_dir.rglob("skill.yaml"):
        if "_base" in skill_yaml_path.parts:
            continue
            
        skill_dir_name = skill_yaml_path.parent.name
        primary_cap = skill_to_cap.get(skill_dir_name)
        
        if not primary_cap:
            print(f"Warning: No capability mapping found for {skill_dir_name}")
            continue

        with open(skill_yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
            # yaml.safe_load will mess up the formatting / block strings, so we will just do string replacement
            # we need to replace the whole `capabilities: ...` block until the next top-level key like `models:`
            
        import re
        
        # Match `capabilities:` followed by lines that are indented
        pattern = r"capabilities:\n(?:  - .*\n)*"
        replacement = f"capabilities:\n  - {primary_cap}\n"
        
        new_content = re.sub(pattern, replacement, content)
        
        if new_content != content:
            with open(skill_yaml_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            updated_count += 1
            print(f"Updated {skill_dir_name} -> [{primary_cap}]")
            
    print(f"Successfully updated {updated_count} skill.yaml files.")

if __name__ == "__main__":
    main()
