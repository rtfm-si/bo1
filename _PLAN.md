# Plan: Dashboard Consolidation - Key Metrics + Research Headlines

## Summary

- Convert `/context/key-metrics` to redirect to `/context/metrics`
- Update ValueMetricsPanel link from `/context/key-metrics` to `/context/metrics`
- Redesign ResearchInsightsWidget as newspaper-style headlines (from scatter plot)
- Populate insights from meetings, mentor conversations, and data analysis

## Implementation Steps

1. **Convert context/key-metrics to redirect**
   - Replace full page content with redirect to `/context/metrics`
   - Comment explaining consolidation

2. **Update ValueMetricsPanel link**
   - Change `/context/key-metrics` to `/context/metrics` (line 184-185)

3. **Create ResearchHeadlinesWidget**
   - New component: `$lib/components/dashboard/ResearchHeadlinesWidget.svelte`
   - Newspaper-style layout: headlines with taglines
   - Source types: meetings (key takeaways), mentor (insights), analysis (findings)
   - Clickable links to source (meeting/mentor/analysis)
   - Empty state for no insights
   - Loading skeleton

4. **Update dashboard to use ResearchHeadlinesWidget**
   - Replace ResearchInsightsWidget with ResearchHeadlinesWidget
   - Keep ResearchInsightsWidget file (may reuse scatter plot elsewhere)

5. **Add API endpoint for research headlines**
   - Create `/api/v1/context/research-headlines` endpoint
   - Query: last 10 insights from sessions + mentor + analysis
   - Return: headline, tagline, source_type, source_id, created_at

## Tests

- Type check: `npm run check`
- Manual validation:
  - /context/key-metrics redirects to /context/metrics
  - Dashboard ValueMetricsPanel "View all" links to /context/metrics
  - Dashboard shows newspaper-style headlines
  - Headlines link to their source correctly
  - Empty state when no insights

## Dependencies & Risks

- Dependencies:
  - API needs new endpoint for headlines aggregation
  - Existing session/mentor data structures

- Risks/edge cases:
  - Large number of insights (limit to 10)
  - Missing source links (graceful handling)
