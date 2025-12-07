# Meeting System Bug Report v2 - 2025-12-07

**Meeting ID**: `bo1_7e543528-15da-4135-b45f-d54b76f068a7`

---

## Summary

Three bugs identified from production meeting analysis:

| # | Issue | Severity | Root Cause | Fix Location |
|---|-------|----------|------------|--------------|
| 1 | Raw JSON displayed in Executive Summary | P0 | Frontend parser doesn't handle JSON format | `frontend/src/lib/utils/xml-parser.ts` |
| 2 | Metrics showing 0/NaN values | P1 | `parseInt()` returns NaN for non-matching tab names | `frontend/src/routes/(app)/meeting/[id]/+page.svelte` |
| 3 | Empty Recommended Actions section | P1 | Cascade effect of #1 - synthesis format mismatch | Same as #1 |

---

## Issue 1: Raw JSON Displayed in Executive Summary (P0)

### Symptom
The Executive Summary section shows raw JSON like:
```json
{"problem_statement":"...","sub_problems_addressed":[...],"recommended_actions":[...],"synthesis_summary":"..."}
```
instead of formatted, readable content.

### Root Cause
**Backend** (`bo1/graph/nodes/synthesis.py:449`):
```python
from bo1.prompts.reusable_prompts import META_SYNTHESIS_ACTION_PLAN_PROMPT
```

The `meta_synthesize_node` uses `META_SYNTHESIS_ACTION_PLAN_PROMPT` which outputs **structured JSON**:
```json
{
  "problem_statement": "...",
  "sub_problems_addressed": [...],
  "recommended_actions": [
    {
      "action": "...",
      "rationale": "...",
      "priority": "critical|high|medium|low",
      "timeline": "...",
      "success_metrics": [...],
      "risks": [...]
    }
  ],
  "synthesis_summary": "..."
}
```

**Frontend** (`frontend/src/lib/utils/xml-parser.ts:187-261`):
```typescript
export function parseSynthesisXML(xmlString: string): SynthesisSection {
    // ... handles XML and Markdown only

    // If still no sections, return the cleaned content as executive_summary
    if (Object.keys(sections).length === 0) {
        sections.executive_summary = cleanedContent;  // RAW JSON ENDS UP HERE!
    }
}
```

The parser only handles:
1. XML format (`<executive_summary>`, `<recommendation>`, etc.)
2. Markdown format (`## Executive Summary`, etc.)

When JSON is received, neither parser succeeds, and the raw JSON is dumped into `executive_summary`.

### Fix

Update `xml-parser.ts` to detect and parse JSON format:

```typescript
// Add new interface for JSON meta-synthesis format
export interface MetaSynthesisJSON {
    problem_statement: string;
    sub_problems_addressed: string[];
    recommended_actions: Array<{
        action: string;
        rationale: string;
        priority: string;
        timeline: string;
        success_metrics: string[];
        risks: string[];
    }>;
    synthesis_summary: string;
}

// Add JSON detection function
export function isJSONFormatted(content: string): boolean {
    const trimmed = content.trim();
    return trimmed.startsWith('{') && trimmed.endsWith('}');
}

// Add JSON parsing function
function parseMetaSynthesisJSON(content: string): SynthesisSection {
    try {
        const json: MetaSynthesisJSON = JSON.parse(content);
        const sections: SynthesisSection = {};

        // Map synthesis_summary to executive_summary
        if (json.synthesis_summary) {
            sections.executive_summary = json.synthesis_summary;
        }

        // Format recommended_actions as implementation_considerations
        if (json.recommended_actions?.length > 0) {
            const actionsList = json.recommended_actions.map((action, i) => {
                const parts = [
                    `### ${i + 1}. ${action.action.split(':')[0] || 'Action ' + (i + 1)}`,
                    '',
                    action.action,
                    '',
                    `**Priority:** ${action.priority}`,
                    `**Timeline:** ${action.timeline}`,
                    '',
                    '**Rationale:**',
                    action.rationale,
                ];

                if (action.success_metrics?.length > 0) {
                    parts.push('', '**Success Metrics:**');
                    action.success_metrics.forEach(m => parts.push(`- ${m}`));
                }

                if (action.risks?.length > 0) {
                    parts.push('', '**Risks:**');
                    action.risks.forEach(r => parts.push(`- ${r}`));
                }

                return parts.join('\n');
            });

            sections.implementation_considerations = actionsList.join('\n\n---\n\n');
        }

        // Map problem_statement to recommendation header context
        if (json.problem_statement) {
            sections.recommendation = `**Decision:** ${json.problem_statement}`;
        }

        return sections;
    } catch (e) {
        console.error('[xml-parser] Failed to parse JSON meta-synthesis:', e);
        return {};
    }
}

// Update parseSynthesisXML to try JSON first
export function parseSynthesisXML(xmlString: string): SynthesisSection {
    let cleanedContent = stripThinkingTags(xmlString);
    const { content: contentWithoutWarning, warning } = extractWarning(cleanedContent);
    cleanedContent = contentWithoutWarning;

    let sections: SynthesisSection = {};

    // NEW: Try JSON parsing first (for meta-synthesis)
    if (isJSONFormatted(cleanedContent)) {
        sections = parseMetaSynthesisJSON(cleanedContent);
        if (Object.keys(sections).length > 0) {
            if (warning) sections.warning = warning;
            return sections;
        }
    }

    // ... rest of existing XML/Markdown parsing
}
```

---

## Issue 2: Metrics Showing 0/NaN Values (P1)

### Symptom
DecisionMetrics component shows:
- "Sub-Problem NaN" indicator
- All metrics showing 0

### Root Cause
**File**: `frontend/src/routes/(app)/meeting/[id]/+page.svelte:895-897`

```typescript
activeSubProblemIndex={view.activeSubProblemTab
    ? parseInt(view.activeSubProblemTab.replace('subproblem-', ''))
    : null}
```

When `activeSubProblemTab` is `"summary"` or another non-matching string:
- `"summary".replace('subproblem-', '')` → `"summary"`
- `parseInt("summary")` → `NaN`

The `DecisionMetrics` component then filters events by `NaN` index, finding nothing.

### Fix

Add NaN check in `+page.svelte`:

```typescript
activeSubProblemIndex={view.activeSubProblemTab?.startsWith('subproblem-')
    ? parseInt(view.activeSubProblemTab.replace('subproblem-', ''))
    : null}
```

Or more robustly:

```typescript
activeSubProblemIndex={(() => {
    if (!view.activeSubProblemTab?.startsWith('subproblem-')) return null;
    const index = parseInt(view.activeSubProblemTab.replace('subproblem-', ''));
    return Number.isNaN(index) ? null : index;
})()}
```

---

## Issue 3: Empty Recommended Actions (P1)

### Symptom
The "Recommended Actions" section shows "No actions extracted from this decision."

### Root Cause
This is a **cascade effect** of Issue #1. The `ActionableTasks.svelte` component:

1. Calls `apiClient.extractTasks(sessionId)`
2. Which calls `sync_extract_tasks_from_synthesis()` in `bo1/agents/task_extractor.py`
3. Which sends the synthesis to Claude (Haiku) for task extraction

The task extractor passes the raw synthesis to Claude, which should handle JSON. However:
- If the synthesis is malformed JSON (with trailing content)
- Or if there's an API error
- The extraction fails silently

**Additional issue**: The JSON meta-synthesis already contains `recommended_actions` array - we shouldn't need to re-extract tasks! The frontend could directly parse and display them.

### Fix Options

**Option A (Preferred)**: Update frontend to directly use `recommended_actions` from JSON synthesis:
- Modify `SynthesisComplete.svelte` to detect JSON format
- Parse and display `recommended_actions` directly
- Skip the task extraction API call for meta-synthesis

**Option B**: Fix task extractor to handle JSON synthesis:
- The extractor should work as Claude can parse JSON
- Debug why it's returning empty results

---

## Files to Change

1. **`frontend/src/lib/utils/xml-parser.ts`** (Issue #1)
   - Add `isJSONFormatted()` function
   - Add `parseMetaSynthesisJSON()` function
   - Update `parseSynthesisXML()` to try JSON first

2. **`frontend/src/routes/(app)/meeting/[id]/+page.svelte`** (Issue #2)
   - Add NaN check for `activeSubProblemIndex` calculation

3. **`frontend/src/lib/components/events/SynthesisComplete.svelte`** (Issue #3, Option A)
   - Detect JSON meta-synthesis
   - Display `recommended_actions` directly as structured cards

---

## Testing Checklist

After fixes, verify:
- [ ] Meta-synthesis displays formatted summary (not raw JSON)
- [ ] Recommended actions render as structured cards with priority, timeline, metrics
- [ ] Metrics show correct values on Summary tab
- [ ] Metrics show correct values when switching between sub-problem tabs
- [ ] No console errors related to NaN or JSON parsing

---

## Alternative Fix: Backend Prompt Change

Instead of fixing the frontend parser, we could change the backend to output XML:

**File**: `bo1/graph/nodes/synthesis.py:449`

Change from:
```python
from bo1.prompts.reusable_prompts import META_SYNTHESIS_ACTION_PLAN_PROMPT
```

To:
```python
from bo1.prompts.meta_synthesis import META_SYNTHESIS_PROMPT_TEMPLATE
```

**Pros**: Simpler frontend, no parser changes needed
**Cons**: Loses structured JSON benefits, less machine-readable output

**Recommendation**: Fix frontend to handle JSON - it's more valuable to have structured data.
