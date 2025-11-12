# Data Directory

This directory contains static data files used by the Board of One application.

## Files

### `personas.json`

Complete persona catalog with 45 expert personas. Each persona includes:

- `id` - Unique identifier (UUID)
- `code` - Short code for referencing (e.g., "growth_hacker")
- `name` - Full name (e.g., "Zara Morales")
- `archetype` - Role description (e.g., "Growth Hacker")
- `category` - Domain category (e.g., "marketing", "finance", "technology")
- `description` - What this persona brings to deliberations
- `emoji` - Visual identifier
- `color_hex` - UI color code
- `traits` - JSON string of personality traits
- `default_weight` - Voting weight (0.0-1.0)
- `temperature` - LLM temperature for this persona (0.0-1.0)
- `system_prompt` - **BESPOKE** persona identity (800-900 chars):
  - Contains `<system_role>` section ONLY
  - Who they are (name, description, expertise)
  - Their unique communication style
  - Their domain-specific approaches
  - **NOTE**: Generic protocols (behavioral, evidence, communication, security) are in `bo1/prompts/reusable_prompts.py` and composed at runtime
- `response_style` - Communication style (e.g., "analytical", "technical")
- `is_active` - Whether persona is available
- `persona_type` - Type classification (e.g., "standard")
- `is_visible` - Whether to show in UI
- `display_name` - Short name for UI
- `domain_expertise` - PostgreSQL array of expertise domains (e.g., "{technical,strategic}")

## Usage

### Load all personas

```python
from bo1.data import load_personas

personas = load_personas()
print(f"Loaded {len(personas)} personas")
```

### Get specific persona by code

```python
from bo1.data import get_persona_by_code

zara = get_persona_by_code("growth_hacker")
print(f"{zara['name']} - {zara['description']}")
```

### Get personas by category

```python
from bo1.data import get_personas_by_category

finance_experts = get_personas_by_category("finance")
for persona in finance_experts:
    print(f"- {persona['name']}: {persona['archetype']}")
```

### Get only active personas

```python
from bo1.data import get_active_personas

active = get_active_personas()
print(f"{len(active)} active personas available")
```

### Use persona with prompt composition

```python
from bo1.data import get_persona_by_code
from bo1.prompts.reusable_prompts import compose_persona_prompt

# Load persona (contains ONLY bespoke <system_role>)
persona = get_persona_by_code("finance_strategist")

# Compose complete prompt by combining:
# - BESPOKE: persona's system_role
# - DYNAMIC: problem statement, participants, phase
# - GENERIC: behavioral guidelines, evidence protocol, etc.
system_prompt = compose_persona_prompt(
    persona_system_role=persona["system_prompt"],  # Bespoke identity
    problem_statement="Should we invest $500K in cloud migration?",
    participant_list="Maria Santos, Tariq Osman, Aria Hoffman",
    current_phase="discussion"
)

# Use with LLM API
response = call_llm(system=system_prompt, messages=[...])
```

### Build persona Pydantic model

```python
from bo1.data import load_personas
from bo1.models.persona import PersonaProfile

personas_data = load_personas()
personas = [PersonaProfile(**p) for p in personas_data]
```

## Updating Personas

The source of truth for personas is:
- **Development**: `zzz_important/personas_filtered.json`
- **Production**: `bo1/data/personas.json`

After editing `zzz_important/personas_filtered.json`:

```bash
cp zzz_important/personas_filtered.json bo1/data/personas.json
```

Or update directly:

```bash
python -c "
from bo1.data import load_personas
import json

personas = load_personas()
# ... make changes to personas list ...

with open('bo1/data/personas.json', 'w') as f:
    json.dump(personas, f, indent=2, ensure_ascii=False)
"
```

## Data Integrity & Architecture

All personas in this file:
- ✓ Contain ONLY bespoke persona identity (<system_role>)
- ✓ Include all required fields
- ✓ Follow PROMPT_ENGINEERING_FRAMEWORK.md guidelines
- ✓ Have unique codes and IDs
- ✓ Have domain expertise assigned
- ✓ 0% duplication - generic protocols in reusable_prompts.py

**Modular Architecture:**
- **Bespoke content** (879 chars avg): `personas.json` → `system_prompt` field
- **Generic protocols** (2,500 chars): `bo1/prompts/reusable_prompts.py`
- **Dynamic context** (runtime): Problem statement, participants, phase
- **Total composed prompt**: ~5,800 chars (~1,450 tokens) at runtime

**Benefits:**
- Update behavioral guidelines once → affects all 45 personas
- Personas contain only their unique identity
- Easy to customize protocols per deliberation phase
- No duplication = smaller file size, easier maintenance
