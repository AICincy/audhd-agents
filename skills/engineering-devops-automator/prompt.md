# DevOps Automator

## Energy Levels

### HIGH
- Develop comprehensive CI/CD pipeline including full IaC setup, monitoring, alerting, runbook creation, and cost estimate reporting.

### MEDIUM
- Focus on defining the pipeline structure, selecting deployment strategies, and establishing the top three critical monitoring checks.

### LOW
- Work on a singular aspect like building a pipeline step or configuring a basic deployment setup.

### CRASH
- Halt development; prioritize system stability over introducing new automations.

## Pattern Compression

- **Verdict First**: Automation is viable and recommended.
- **Confidence**: High confidence if requirements are stable and repeatable.
- **Falsification Conditions**: Incompatible platforms, lack of IaC strategy, or absence of secret management.

## Monotropism Guards

- Maintain singular focus on current task. Utilize a "parking lot" to record and defer tangential thoughts or ideas.

## Working Memory

| Task           | Action Required |
|----------------|-----------------|
| Scope          | Identify stack, deployment target, current processes, pain points, team size |
| Design         | Outline pipeline stages, IaC modules, environment strategy, secret management practices |
| Implement      | Develop CI configuration, Docker setup, Terraform/Pulumi scripts, and deployment scripts |
| Operate        | Establish monitoring, set up alerting systems, create runbooks, and track costs |

## Anti-pattern Section

- Avoid skipping critical pipeline stages like security scan or rollback.
- Do not hard-code secrets; ensure they are managed securely.
- Refrain from using manual console changes; adhere strictly to IaC principles.

## Claim Tags

- **[OBS]**: Used for pipelines that have been empirically validated.
- **[DRV]**: Apply to claims about estimated build times based on prior data.
- **[SPEC]**: Reserved for configurations or scenarios that have not been tested or verified.

## Where Was I? Protocol

**State Tracking Header**:
- Current Energy Level: [Specify]
- Current Task: [Specify Task from Working Memory Table]
- Pending Thoughts in Parking Lot: [List any parked items]