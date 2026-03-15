import os
import sys

def main():
    commit_msg_file = sys.argv[1]
    
    with open(commit_msg_file, "r") as f:
        content = f.read()

    # Determine which commit message to use based on the content
    new_msg = ""
    if "feat: cognitive architecture (A-1 through A-6)" in content:
        new_msg = "feat(cognitive-architecture): add pipeline, hooks, schemas, and validation tests\n"
    elif "testing-reality-checker" in content:
        new_msg = "feat(skills): integrate skill architecture with cognitive framework\n"
    elif "add runtime/schemas.py with cognitive state models" in content:
        new_msg = "feat(execute): add cognitive state to request schema\n"
    elif "Introduce a comprehensive suite of 51 specialized skills" in content:
        new_msg = "feat(skills): add 51 specialized skills for task execution and validation\n"
    else:
        new_msg = content # Keep original if nothing matched

    # Clear everything else
    with open(commit_msg_file, "w") as f:
        f.write(new_msg)

if __name__ == "__main__":
    main()
