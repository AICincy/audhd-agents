import asyncio
import json
from adapters.router import SkillRouter
from runtime.schemas import ExecuteRequest

async def main():
    router = SkillRouter()
    
    with open(r"c:\Users\krass\.gemini\antigravity\brain\4aec9874-bd3b-44cf-9ed4-55b1208dce0f\walkthrough.md", "r", encoding="utf-8") as f:
        work_summary = f.read()

    req = ExecuteRequest(
        skill_id="testing-reality-checker",
        input_text=f"Please reality check the following work regarding codebase enhancements and security fixes:\n\n{work_summary}",
        model_override="C-OP46"
    )
    res = await router.execute(req)
    print(json.dumps(res.model_dump(), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
