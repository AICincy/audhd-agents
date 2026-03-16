import asyncio
from adapters.router import SkillRouter
from adapters.base import SkillRequest

async def main():
    router = SkillRouter()
    print("Router initialized. Executing reality check...")
    req = SkillRequest(
        skill_id="testing-reality-checker", 
        input_text="Reality check: I fixed Pyre typings in router.py by casting dict keys to str and adding type ignores for run_in_executor arg-types."
    )
    res = await router.execute(req)
    print("Response from reality checker:")
    print(res.output)
    if "_validation" in res.output:
        print("\nValidation Failed:")
        print(res.output["_validation"])

if __name__ == "__main__":
    asyncio.run(main())
