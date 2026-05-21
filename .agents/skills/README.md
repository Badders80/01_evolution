# Evolution — Agent Skills

This directory contains specialized skills for AI coding agents working on the Evolution Stables codebase.

## Available Skills

| Skill | Purpose | When to Use |
|-------|---------|-------------|
| [`api-development.md`](api-development.md) | Create and test Cloud Functions API endpoints | Adding/modifying API routes, Pydantic models, or API tests |
| [`frontend-development.md`](frontend-development.md) | Build Next.js pages and components | Creating admin pages, forms, or integrating with the API |
| [`deployment-operations.md`](deployment-operations.md) | Deploy and manage GCP infrastructure | Deploying Cloud Functions, managing Firestore, configuring GCS |
| [`schema-validation.md`](schema-validation.md) | Manage JSON Schemas and validation | Adding fields, ensuring frontend/backend consistency |

## How to Use

Reference these skills in your agent prompts:

```
Use the api-development skill to create a new endpoint for updating horse status.
```

Or invoke directly (depending on your agent configuration):

```
/gsd-start api-development
```

## Core Principles

All skills follow the **Evolution Core Laws** from [`AGENTS.md`](../AGENTS.md):

1. **`api/` is the only data writer** — App never writes to Firestore directly
2. **Microchip is the durable anchor** — 15-digit natural key from loveracing.nz
3. **HLT status is a state machine** — `draft → reviewed → publish_ready → published`
4. **Assets are organized by entity** — `horse/{microchip}/` in GCS
5. **DNA schemas are the contract** — Pydantic + React forms validate against same JSON Schema
6. **No bi-directional sync** — Downstream systems are clients only

## Related Documentation

- **Main Instructions:** [`AGENTS.md`](../AGENTS.md)
- **Conventions:** [`dna/conventions/CONVENTIONS.md`](../dna/conventions/CONVENTIONS.md)
- **Why Rules Exist:** [`dna/outcomes/WHY.md`](../dna/outcomes/WHY.md)
- **Current Status:** [`docs/PROGRESS.md`](../docs/PROGRESS.md)
- **Build Plan:** [`GAME_PLAN.md`](../GAME_PLAN.md)

## Creating New Skills

When you encounter a recurring task or pattern that isn't covered by existing skills:

1. Create a new `.md` file in this directory
2. Include: Purpose, When to use, Workflow, Examples, Common Pitfalls
3. Reference existing files and conventions
4. Link back to core laws in `AGENTS.md`

**Template:**
```markdown
# Evolution — [Skill Name]

**Purpose:** [One sentence]

**When to use:**
- [Scenario 1]
- [Scenario 2]

## Workflow

### Step 1: [Action]
[Instructions with code examples]

## Common Pitfalls

❌ **Never [anti-pattern]** — [Reason]

## Related Files

- **Location:** `path/to/files`
```

## Updating Skills

Keep skills current:
- ✅ Update when conventions change
- ✅ Add examples from real implementations
- ✅ Document common errors and solutions
- ✅ Link to new files when architecture evolves

**Before changing any rule**, read [`dna/outcomes/WHY.md`](../dna/outcomes/WHY.md) to understand why it exists.
