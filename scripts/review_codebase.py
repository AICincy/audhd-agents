import asyncio
import os
import json
from adapters.router import SkillRouter
from adapters.base import SkillRequest

FILES_TO_REVIEW = [
    "runtime/planner.py",
    "runtime/schemas.py",
    "adapters/router.py"
]

async def main():
    print("Initializing SkillRouter...")
    router = SkillRouter()
    
    # Check if providers are connected
    status = router.get_status()
    if not any(info.get("connected") for info in status.values()):
        print("Warning: No providers are connected. Ensure your .env is loaded correctly.")

    for file_path in FILES_TO_REVIEW:
        print(f"\n--- Reviewing {file_path} ---")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            req = SkillRequest(
                skill_id="engineering-code-reviewer",
                input_text=f"Review the following file for cognitive contract adherence, robustness, and typing:\n\n{content}",
                options={
                    "focus": "cognitive contract adherence, error handling, typing, and architecture"
                }
            )
            
            res = await router.execute(req)
            print(f"[{file_path}] Review Result (Model: {res.model_used}):")
            print(json.dumps(res.output, indent=2))
            
            if "_validation" in res.output and not res.output["_validation"].get("passed", True):
                print(f"Validation WARNING for {file_path}:", res.output["_validation"])
                
        except Exception as e:
            print(f"Failed to review {file_path}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
