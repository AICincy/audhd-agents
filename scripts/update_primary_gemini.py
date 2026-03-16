import os
import glob
import re

for filepath in glob.glob('skills/*/skill.yaml'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Determine capabilities
    caps_match = re.search(r'capabilities:\s*\n((?:\s+-\s+\w+\s*\n)+)', content)
    caps = []
    if caps_match:
        caps_list_str = caps_match.group(1)
        caps = re.findall(r'-\s+(\w+)', caps_list_str)

    primary = 'G-PRO31'
    fallback = '[G-PRO, O-54P]'

    if 'analyze' in caps:
        primary = 'G-PRO31'
    elif 'synthesize' in caps or 'draft' in caps or 'generate' in caps:
        primary = 'G-PRO31'
    elif 'triage' in caps:
        primary = 'G-FLA31'
        fallback = '[G-PRO, O-O4M]'
    elif 'research' in caps:
        primary = 'G-PRO31' # OSINT
    elif 'orchestrate' in caps:
        primary = 'G-PRO31'

    # Regex search and replace for primary and fallback
    content = re.sub(r'(?<=primary:).*$', f' {primary}', content, flags=re.MULTILINE)
    content = re.sub(r'(?<=fallback:).*$', f' {fallback}', content, flags=re.MULTILINE)

    # Delete openai, gemini, anthropic keys if they exist under models:
    content = re.sub(r'^\s*openai:.*?$\n?', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\s*gemini:.*?$\n?', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\s*anthropic:.*?$\n?', '', content, flags=re.MULTILINE)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Properly updated skill models to Gemini 3.1 as primary.")
