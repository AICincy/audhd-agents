#!/usr/bin/env python3
"""syntax_audit.py - Comprehensive syntax analysis for audhd-agents.

Performs:
  1. Python compile checks on all .py files
  2. AST analysis (bare excepts, mutable defaults, unreachable code)
  3. YAML/JSON validation on all config/skill files
  4. Cross-reference checks:
     - Model aliases vs adapters/config.yaml
     - Hook names vs HOOK_REGISTRY
     - Schema $ref resolution
  5. Import consistency checks
  6. Schema alignment (agents CognitiveState vs skills schema_base.json)

Usage:
    python scripts/syntax_audit.py [--json]
"""

from __future__ import annotations

import ast
import json
import os
import py_compile
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Directories to skip during traversal
SKIP_DIRS = {".git", "node_modules", "dist", "__pycache__", ".agents"}

# Ensure project root is importable for cross-reference checks
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def walk_py(root: Path):
    """Yield .py file paths under *root*, skipping unwanted dirs."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.endswith(".py"):
                yield Path(dirpath) / f


def walk_ext(root: Path, ext: str):
    """Yield files matching *ext* under *root*."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.endswith(ext):
                yield Path(dirpath) / f


# ---------------------------------------------------------------------------
# 1. Python compile checks
# ---------------------------------------------------------------------------

def check_compile(root: Path) -> tuple[int, list[str]]:
    errors: list[str] = []
    count = 0
    for path in walk_py(root):
        count += 1
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(str(exc))
    return count, errors


# ---------------------------------------------------------------------------
# 2. AST analysis
# ---------------------------------------------------------------------------

class _ASTChecker(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.findings: list[str] = []

    # -- bare except --
    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.findings.append(
                f"BARE_EXCEPT: {self.filename}:{node.lineno}"
            )
        self.generic_visit(node)

    # -- mutable defaults --
    def _check_defaults(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        for arg in node.args.defaults + node.args.kw_defaults:
            if arg is not None and isinstance(arg, (ast.List, ast.Dict, ast.Set)):
                self.findings.append(
                    f"MUTABLE_DEFAULT: {self.filename}:{node.lineno} "
                    f'function "{node.name}"'
                )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_defaults(node)
        self._check_unreachable(node.body)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_defaults(node)
        self._check_unreachable(node.body)
        self.generic_visit(node)

    # -- unreachable code --
    def _check_unreachable(self, body: list[ast.stmt]) -> None:
        for i, stmt in enumerate(body):
            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                for r in body[i + 1:]:
                    if not isinstance(r, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        self.findings.append(
                            f"UNREACHABLE: {self.filename}:{r.lineno} "
                            f"after {type(stmt).__name__} at line {stmt.lineno}"
                        )
                        break
                break

    def visit_If(self, node: ast.If) -> None:
        self._check_unreachable(node.body)
        self._check_unreachable(node.orelse)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._check_unreachable(node.body)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._check_unreachable(node.body)
        self.generic_visit(node)

    def visit_Module(self, node: ast.Module) -> None:
        self._check_unreachable(node.body)
        self.generic_visit(node)


def check_ast(root: Path) -> tuple[int, list[str]]:
    findings: list[str] = []
    count = 0
    for path in walk_py(root):
        count += 1
        try:
            source = path.read_text()
            tree = ast.parse(source, filename=str(path))
            checker = _ASTChecker(str(path))
            checker.visit(tree)
            findings.extend(checker.findings)
        except SyntaxError as exc:
            findings.append(f"SYNTAX_ERROR: {path}:{exc.lineno} - {exc.msg}")
    return count, findings


# ---------------------------------------------------------------------------
# 3. YAML / JSON validation
# ---------------------------------------------------------------------------

def check_yaml_json(root: Path) -> dict[str, tuple[int, list[str]]]:
    results: dict[str, tuple[int, list[str]]] = {}

    yaml_count, yaml_errors = 0, []
    for path in walk_ext(root, ".yaml"):
        yaml_count += 1
        try:
            yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            yaml_errors.append(f"{path}: {exc}")
    for path in walk_ext(root, ".yml"):
        yaml_count += 1
        try:
            yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            yaml_errors.append(f"{path}: {exc}")
    results["yaml"] = (yaml_count, yaml_errors)

    json_count, json_errors = 0, []
    for path in walk_ext(root, ".json"):
        json_count += 1
        try:
            json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            json_errors.append(f"{path}: {exc}")
    results["json"] = (json_count, json_errors)

    return results


# ---------------------------------------------------------------------------
# 4a. Cross-reference: model aliases vs config.yaml
# ---------------------------------------------------------------------------

def check_aliases(root: Path) -> dict:
    config_path = root / "adapters" / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    alias_map: dict[str, str] = config.get("alias_map", {})

    used: set[str] = set()
    skills_dir = root / "skills"
    for skill_yaml in sorted(skills_dir.glob("*/skill.yaml")):
        skill = yaml.safe_load(skill_yaml.read_text())
        models = skill.get("models", {})
        if models.get("primary"):
            used.add(models["primary"])
        for fb in models.get("fallback") or []:
            used.add(fb)

    # root skill.yaml
    root_skill = yaml.safe_load((root / "skill.yaml").read_text())
    root_models = root_skill.get("models", {})
    if root_models.get("primary"):
        used.add(root_models["primary"])
    for fb in root_models.get("fallback") or []:
        used.add(fb)

    missing = used - set(alias_map)
    unused = set(alias_map) - used

    return {
        "defined": len(alias_map),
        "used": len(used),
        "missing": sorted(missing),
        "unused": sorted(unused),
        "all_resolved": len(missing) == 0,
    }


# ---------------------------------------------------------------------------
# 4b. Cross-reference: hook names vs HOOK_REGISTRY
# ---------------------------------------------------------------------------

def check_hooks(root: Path) -> dict:
    from runtime.init_hooks import HOOK_REGISTRY, ALWAYS_ON_HOOKS
    from runtime.hooks import _resolve_hook_name

    always_on = list(ALWAYS_ON_HOOKS)

    # Collect hook names referenced in skill YAMLs and resolve them
    skills_dir = root / "skills"
    unresolved: set[str] = set()
    for skill_yaml in sorted(skills_dir.glob("*/skill.yaml")):
        skill = yaml.safe_load(skill_yaml.read_text())
        for h in skill.get("sk_hooks") or []:
            resolved = _resolve_hook_name(h)
            if resolved not in HOOK_REGISTRY:
                unresolved.add(h)

    return {
        "total": len(HOOK_REGISTRY),
        "always_on": always_on,
        "registry": {name: func.__name__ for name, func in sorted(HOOK_REGISTRY.items())},
        "unregistered_refs": sorted(unresolved),
    }


# ---------------------------------------------------------------------------
# 4c. Cross-reference: schema $ref resolution
# ---------------------------------------------------------------------------

def check_schema_refs(root: Path) -> tuple[int, list[str]]:
    errors: list[str] = []
    checked = 0

    for schema_file in sorted((root / "skills").glob("*/schema.json")):
        checked += 1
        schema = json.loads(schema_file.read_text())

        def _walk_refs(obj, base_dir: Path) -> None:
            if isinstance(obj, dict):
                if "$ref" in obj:
                    ref = obj["$ref"]
                    if not ref.startswith("#"):
                        ref_path = (base_dir / ref).resolve()
                        if not ref_path.exists():
                            errors.append(f"{schema_file}: $ref \"{ref}\" -> {ref_path} NOT FOUND")
                for v in obj.values():
                    _walk_refs(v, base_dir)
            elif isinstance(obj, list):
                for item in obj:
                    _walk_refs(item, base_dir)

        _walk_refs(schema, schema_file.parent)

    return checked, errors


# ---------------------------------------------------------------------------
# 5. Import consistency
# ---------------------------------------------------------------------------

def check_imports(root: Path) -> dict:
    count = 0
    ext_deps: dict[str, int] = {}
    known_stdlib = {
        "os", "sys", "json", "yaml", "ast", "hashlib", "hmac", "uuid",
        "datetime", "time", "pathlib", "typing", "enum", "dataclasses",
        "collections", "re", "unittest", "asyncio", "logging", "functools",
        "io", "secrets", "textwrap", "abc", "copy", "importlib",
        "traceback", "inspect", "contextlib", "warnings", "http",
        "base64", "urllib", "string", "itertools", "subprocess", "glob",
        "shutil", "tempfile", "math", "argparse", "py_compile", "struct",
        "random", "pprint", "signal", "socket", "threading", "multiprocessing",
        "concurrent", "csv", "zipfile", "gzip", "operator", "types",
        "weakref", "heapq", "bisect", "array", "decimal", "fractions",
        "statistics", "builtins", "codecs", "locale",
    }
    known_internal = {
        "runtime", "adapters", "scripts", "graphs", "capabilities",
        "cli", "tests", "build",
    }

    for path in walk_py(root):
        count += 1
        try:
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base = alias.name.split(".")[0]
                        if base not in known_stdlib and base not in known_internal and base != "__future__":
                            ext_deps[base] = ext_deps.get(base, 0) + 1
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    base = module.split(".")[0]
                    if base not in known_stdlib and base not in known_internal and base != "__future__":
                        ext_deps[base] = ext_deps.get(base, 0) + 1
        except SyntaxError:
            pass

    return {"files": count, "external_deps": dict(sorted(ext_deps.items(), key=lambda x: -x[1]))}


# ---------------------------------------------------------------------------
# 6. Schema alignment
# ---------------------------------------------------------------------------

def check_schema_alignment(root: Path) -> dict:
    from runtime.schemas import CognitiveState

    agents_fields = sorted(CognitiveState.model_fields.keys())

    base_path = root / "skills" / "_base" / "schema_base.json"
    base = json.loads(base_path.read_text())
    cs_def = base.get("definitions", {}).get("cognitive_state", {})
    skills_fields = sorted(cs_def.get("properties", {}).keys())

    return {
        "agents_fields": agents_fields,
        "skills_fields": skills_fields,
        "agents_count": len(agents_fields),
        "skills_count": len(skills_fields),
        "aligned": agents_fields == skills_fields,
    }


# ---------------------------------------------------------------------------
# 7. Skill validation
# ---------------------------------------------------------------------------

def check_skills(root: Path) -> tuple[int, list[dict]]:
    skills_dir = root / "skills"
    results = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
            continue
        entry: dict = {"name": skill_dir.name}
        entry["yaml"] = (skill_dir / "skill.yaml").exists()
        entry["prompt"] = (skill_dir / "prompt.md").exists()
        entry["schema"] = (skill_dir / "schema.json").exists()
        entry["examples"] = (skill_dir / "examples.json").exists()

        if entry["yaml"]:
            try:
                skill = yaml.safe_load((skill_dir / "skill.yaml").read_text())
                entry["hooks"] = bool(skill.get("sk_hooks"))
                entry["yaml_valid"] = True
            except yaml.YAMLError:
                entry["yaml_valid"] = False
                entry["hooks"] = False
        else:
            entry["yaml_valid"] = False
            entry["hooks"] = False

        if entry["prompt"]:
            entry["prompt_size"] = (skill_dir / "prompt.md").stat().st_size

        if entry["schema"]:
            try:
                json.loads((skill_dir / "schema.json").read_text())
                entry["schema_valid"] = True
            except json.JSONDecodeError:
                entry["schema_valid"] = False
        else:
            entry["schema_valid"] = False

        results.append(entry)
    return len(results), results


# ---------------------------------------------------------------------------
# Main report
# ---------------------------------------------------------------------------

def _sep(char: str = "=", width: int = 80) -> str:
    return char * width


def main() -> int:
    root = PROJECT_ROOT
    json_mode = "--json" in sys.argv
    issues: list[str] = []

    # 1. Compile
    py_count, compile_errors = check_compile(root)
    # 2. AST
    ast_count, ast_findings = check_ast(root)
    # 3. YAML/JSON
    yj = check_yaml_json(root)
    yaml_count, yaml_errors = yj["yaml"]
    json_count, json_errors = yj["json"]
    # 4a. Aliases
    alias_info = check_aliases(root)
    # 4b. Hooks
    hook_info = check_hooks(root)
    # 4c. Schema refs
    ref_count, ref_errors = check_schema_refs(root)
    # 5. Imports
    import_info = check_imports(root)
    # 6. Schema alignment
    alignment = check_schema_alignment(root)
    # 7. Skills
    skill_count, skill_results = check_skills(root)

    issues.extend(compile_errors)
    issues.extend(ast_findings)
    issues.extend(yaml_errors)
    issues.extend(json_errors)
    issues.extend(ref_errors)
    if alias_info["missing"]:
        issues.append(f"Missing aliases: {alias_info['missing']}")
    if hook_info["unregistered_refs"]:
        issues.append(f"Unregistered hooks: {hook_info['unregistered_refs']}")
    if not alignment["aligned"]:
        issues.append("Schema misalignment between agents and skills")

    if json_mode:
        report = {
            "compile": {"files": py_count, "errors": compile_errors},
            "ast": {"files": ast_count, "findings": ast_findings},
            "yaml": {"files": yaml_count, "errors": yaml_errors},
            "json": {"files": json_count, "errors": json_errors},
            "aliases": alias_info,
            "hooks": hook_info,
            "schema_refs": {"checked": ref_count, "errors": ref_errors},
            "imports": import_info,
            "schema_alignment": alignment,
            "skills": {"count": skill_count, "results": skill_results},
            "issues": issues,
            "healthy": len(issues) == 0,
        }
        print(json.dumps(report, indent=2))
        return 0 if not issues else 1

    # Text report
    print(_sep())
    print("          AUDHD-AGENTS SYNTAX AUDIT REPORT")
    print(_sep())
    print()

    # 1
    print(_sep())
    print("1. PYTHON COMPILE CHECKS")
    print(_sep())
    print(f"  Files checked:  {py_count}")
    print(f"  Status:         {'PASS' if not compile_errors else 'FAIL'}")
    if compile_errors:
        for e in compile_errors:
            print(f"    {e}")
    print()

    # 2
    print(_sep())
    print("2. AST ANALYSIS")
    print(_sep())
    print(f"  Files analyzed:   {ast_count}")
    print(f"  Bare excepts:     {sum(1 for f in ast_findings if 'BARE_EXCEPT' in f)}")
    print(f"  Mutable defaults: {sum(1 for f in ast_findings if 'MUTABLE_DEFAULT' in f)}")
    print(f"  Unreachable code: {sum(1 for f in ast_findings if 'UNREACHABLE' in f)}")
    print(f"  Status:           {'PASS' if not ast_findings else 'FAIL'}")
    if ast_findings:
        for f in ast_findings:
            print(f"    {f}")
    print()

    # 3
    print(_sep())
    print("3. YAML/JSON VALIDATION")
    print(_sep())
    print(f"  YAML files: {yaml_count}  {'PASS' if not yaml_errors else 'FAIL'}")
    print(f"  JSON files: {json_count}  {'PASS' if not json_errors else 'FAIL'}")
    if yaml_errors:
        for e in yaml_errors:
            print(f"    {e}")
    if json_errors:
        for e in json_errors:
            print(f"    {e}")
    print()

    # 4
    print(_sep())
    print("4. CROSS-REFERENCE CHECKS")
    print(_sep())
    print()
    print("  4a. Model aliases vs config.yaml")
    print(f"      Defined: {alias_info['defined']}  Used: {alias_info['used']}")
    print(f"      All resolved: {'YES' if alias_info['all_resolved'] else 'NO'}")
    if alias_info["missing"]:
        print(f"      Missing: {alias_info['missing']}")
    if alias_info["unused"]:
        print(f"      Unused:  {alias_info['unused']}")
    print()
    print("  4b. Hook names vs HOOK_REGISTRY")
    print(f"      Total hooks:  {hook_info['total']}")
    print(f"      Always-on:    {len(hook_info['always_on'])} ({', '.join(hook_info['always_on'])})")
    if hook_info["unregistered_refs"]:
        print(f"      Unregistered: {hook_info['unregistered_refs']}")
    else:
        print("      All skill hook refs resolve: YES")
    print()
    for name, func in hook_info["registry"].items():
        ao = "  YES" if name in hook_info["always_on"] else ""
        print(f"      {name:24s} {func:20s}{ao}")
    print()
    print("  4c. Schema $ref resolution")
    print(f"      Schemas checked: {ref_count}")
    print(f"      Status:          {'PASS' if not ref_errors else 'FAIL'}")
    if ref_errors:
        for e in ref_errors:
            print(f"        {e}")
    print()

    # 5
    print(_sep())
    print("5. IMPORT CONSISTENCY")
    print(_sep())
    print(f"  Files analyzed: {import_info['files']}")
    print(f"  External deps:  {len(import_info['external_deps'])}")
    for dep, cnt in import_info["external_deps"].items():
        print(f"    {dep}: {cnt} imports")
    print()

    # 6
    print(_sep())
    print("6. SCHEMA ALIGNMENT (agents vs skills)")
    print(_sep())
    print(f"  Agents CognitiveState fields ({alignment['agents_count']}):")
    print(f"    {', '.join(alignment['agents_fields'])}")
    print(f"  Skills cognitive_state fields ({alignment['skills_count']}):")
    print(f"    {', '.join(alignment['skills_fields'])}")
    print(f"  ALIGNED: {'YES' if alignment['aligned'] else 'NO'} ({alignment['agents_count']}/{alignment['skills_count']})")
    print()

    # 7
    print(_sep())
    print(f"7. SKILL VALIDATION: {skill_count} SKILLS")
    print(_sep())
    all_ok = True
    hdr = f"  {'Skill':<48s} {'YAML':>6s} {'Hooks':>7s} {'Prompt':>14s} {'Schema':>8s} {'Examples':>10s}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for s in skill_results:
        y = "OK" if s.get("yaml_valid") else "MISS"
        h = "OK" if s.get("hooks") else "NONE"
        p = f"OK ({s['prompt_size']}b)" if s.get("prompt") else "MISS"
        sc = "OK" if s.get("schema_valid") else "MISS"
        ex = "OK" if s.get("examples") else "---"
        if y != "OK" or not s.get("prompt") or sc != "OK":
            all_ok = False
        print(f"  {s['name']:<48s} {y:>6s} {h:>7s} {p:>14s} {sc:>8s} {ex:>10s}")
    print()
    if all_ok:
        print(f"  ALL {skill_count} SKILLS VALIDATED SUCCESSFULLY")
    else:
        print(f"  VALIDATION ISSUES in {skill_count} skills")
    print()

    # Summary
    print(_sep())
    print("8. OVERALL")
    print(_sep())
    if issues:
        print(f"  ISSUES FOUND: {len(issues)}")
        for i in issues:
            print(f"    - {i}")
    else:
        print("  STATUS: HEALTHY - No syntax issues found")
    print(_sep())

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
