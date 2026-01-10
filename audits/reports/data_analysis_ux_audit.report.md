# Data Analysis Feature - UX Audit Report

**Date:** January 9, 2026
**Tested URL:** https://boardof.one/advisor/analyze
**Test Dataset:** business.retailsales.csv (1,775 rows, 6 columns, 46.2 KB)

---

## Executive Summary

The data analysis feature provides a comprehensive guided experience for data exploration with AI-powered insights. The core functionality works well, particularly the chat-based Q&A feature which delivers excellent, actionable business insights. However, several UX issues impact the guided experience, particularly around button feedback and navigation between features.

**Overall Assessment:** Good foundation with room for improvement in UX polish and feature connectivity.

---

## Features Tested

### 1. Data Upload (Upload Page)
**Status:** Working Well

**What Works:**
- Clean drag-and-drop interface with clear file type restrictions
- Quick upload with success notification
- Dataset list shows key metadata (rows, columns, size, date)
- "Compare Datasets" feature visible after multiple uploads
- Google Sheets import option available

**Improvements Suggested:**
- Add upload progress indicator for larger files
- Show preview of first few rows before navigating to dataset

---

### 2. Overview Tab
**Status:** Working Well

**What Works:**
- "About This Data" section provides clear summary
- "Suggested Charts" with 2 smart recommendations (bar, scatter)
- Chart preview with mini-stats (Latest, Average, Min, Max)
- Expandable chart modal with interactive Plotly tools (Zoom, Pan, Download PNG)
- Data Quality score prominently displayed (99% completeness, 70% consistency)
- "Explore Further" suggested questions

**Content Quality:**
- Suggestions are relevant to the dataset
- Stats provide actionable quick insights

**Improvements Suggested:**
- The "Generate a full profile to receive detailed business insights" message persists even after profile is generated - should update dynamically
- Consider adding data preview table snippet

---

### 3. Analyse Tab
**Status:** Excellent

**What Works:**
- "Key Insights" header with quick stats (6 Columns, 5 Metrics, 1 Dimension, 85% Quality)
- 8 collapsible analysis sections:
  1. **Column Roles** - Interactive tags to change metric/dimension classification
  2. **Missingness & Cardinality** - 1 column with nulls identified
  3. **Descriptive Statistics** - 5 numeric, 1 categorical breakdown
  4. **Outliers** - 4 columns affected with specific counts and ranges
  5. **Correlations** - 1 highly correlated pair identified
  6. **Time Series Readiness** - Correctly identified as not time-series
  7. **Segmentation Opportunities** - 3 found
  8. **Data Quality** - 85% overall with detailed breakdown
- Column Profiles table with Type, Nulls, Unique, Min, Max, Mean
- Actionable advice in each section (e.g., "Consider: verify data accuracy, filter outliers...")

**Content Quality:**
- Outstanding depth of automated analysis
- Very useful for both novice and advanced users
- Clearly identifies 512 duplicate rows (28.8%) - actionable insight

**Improvements Suggested:**
- Add "Export Analysis" button to download as PDF/CSV
- Add quick-fix actions (e.g., "Remove duplicates" button)

---

### 4. Clarify Tab
**Status:** Working Well

**What Works:**
- Clear explanation of why business context helps
- Comprehensive form fields:
  - Business Goal (with helpful placeholder)
  - Key Metrics (comma-separated)
  - KPIs (target values)
  - Industry dropdown (15 options)
  - Current Objectives
  - Additional Context (pre-filled with user profile data)

**Improvements Suggested:**
- Add "Save & Apply" to immediately see how context changes insights
- Show examples of how context improves analysis
- Add "Import from previous dataset" option

---

### 5. Charts Tab
**Status:** Needs Work

**What Works:**
- Chart type selector (bar, line, scatter, pie) with icons
- Axis dropdowns populated with column names correctly
- "Favourites" sub-tab for saved charts
- "Save as Favourite" button

**Issues Found:**
- **Critical:** Preview button does not generate chart preview - no visible feedback or error
- Chart preview area remains empty after clicking Preview with valid axes selected

**Improvements Suggested:**
- Fix Preview functionality
- Add loading spinner when generating chart
- Add aggregation options (sum, average, count) for Y-axis
- Add color/group-by option for categorical dimensions
- Show error message if chart cannot be generated

---

### 6. Insights Tab
**Status:** Partially Working

**What Works:**
- "Suggested Next Steps" section with AI recommendations
- "Ask a Question" section with 6 pre-built questions
- Shows relevant suggestions based on analysis (correlations, segmentation)

**Issues Found:**
- **Critical:** "View correlations" button doesn't navigate or show content
- **Critical:** "View segments" button doesn't navigate or show content
- **Critical:** Pre-built question buttons don't trigger the chat or show answers
- Buttons show "active" state but no action occurs

**Improvements Suggested:**
- Connect action buttons to appropriate views (e.g., navigate to Analyse tab correlations section)
- Make pre-built questions populate and submit to chat automatically
- Add visual feedback when buttons are processing

---

### 7. Chat Feature (Bottom Bar)
**Status:** Excellent

**What Works:**
- Persistent "Ask a question about your data..." bar across all tabs
- Expandable chat panel with conversation history
- Excellent AI responses with:
  - Natural language explanations
  - Formatted data breakdowns with bullet points
  - Business context interpretations
  - Chart generation from natural language
  - Follow-up question suggestions
- "6 columns available" quick reference
- Conversation history with timestamps and message counts
- "Clear" button and "+ New" conversation option

**Response Quality Example:**
Question: "What is the total sales by category?"
Response included:
- Sales breakdown by 8 categories with $ values and percentages
- Business interpretation ("While Baskets have the most transactions, Art & Sculpture is nearly matching them in revenue")
- Strategic question ("Are Baskets lower-priced impulse buys?")
- Generated bar chart suggestion
- 4 follow-up question buttons

**This is the standout feature** - the AI provides genuinely useful business insights, not just raw data.

**Improvements Suggested:**
- Allow pinning chat open while browsing tabs
- Add "Copy response" button
- Add "Export conversation" option
- Show typing indicator while generating response

---

### 8. Analysis History
**Status:** Working Well

**What Works:**
- Shows previously generated charts with thumbnails
- Metadata includes chart type, title, timestamp
- Clickable to re-view charts

---

## UX Issues Summary

### Critical (Blocking User Flow)
1. **Charts Preview doesn't work** - Users cannot build custom charts
2. **Insights action buttons non-functional** - "View correlations", "View segments", pre-built questions don't trigger actions

### Medium Priority
3. **Profile generation stuck in loading state** - Initially showed loading spinners for extended period
4. **404 error on investigation endpoint** - Console error may indicate backend issue
5. **Stale messaging** - "Generate a full profile" message persists after profile exists

### Low Priority
6. **Chat panel overlaps content** - Can block interaction with suggested charts
7. **No export options** - Cannot download analysis or insights

---

## Recommendations for Guided Experience

### For Novice Users
The current flow works reasonably well:
1. Upload CSV ✓
2. Generate Profile ✓
3. View Overview for quick insights ✓
4. Use Chat to ask questions ✓✓ (Excellent)

**Missing:**
- Onboarding wizard/tour
- "Start here" guidance
- Progress indicator showing analysis completeness

### For Advanced Users
- Analyse tab provides excellent depth ✓
- Column role customization ✓
- Manual chart builder needs fixing
- Would benefit from SQL-like query interface

---

## Quality of Information by Tab

| Tab | Usefulness | Actionability | Novice-Friendly |
|-----|------------|---------------|-----------------|
| Overview | High | Medium | Yes |
| Analyse | Very High | High | Moderate |
| Clarify | Medium | High (potential) | Yes |
| Charts | Low (broken) | Low | Yes |
| Insights | Medium | Low (broken buttons) | Yes |
| Chat | Very High | Very High | Yes |

---

## Top 5 Priority Fixes

1. **Fix Charts Preview** - Core functionality broken
2. **Connect Insights buttons** - Pre-built questions should open chat with answer
3. **Fix "View correlations/segments"** - Should navigate to Analyse tab sections
4. **Add loading/progress states** - Throughout the application
5. **Profile messaging update** - Dynamic text based on profile state

---

## Screenshots Captured

1. `overview-tab-initial.png` - Overview tab with profile loaded
2. `chart-modal-expanded.png` - Interactive chart in modal
3. `analyse-tab.png` - Analyse tab with Key Insights
4. `clarify-tab.png` - Business context form
5. `charts-tab.png` - Chart builder (showing non-working preview)
6. `insights-tab.png` - AI recommendations section

---

## Conclusion

The data analysis feature has **excellent AI-powered insights** at its core. The chat feature delivers genuinely valuable business intelligence that can take users from raw data to actionable insights. The Analyse tab provides comprehensive automated analysis that would save hours of manual exploration.

However, the **guided experience is fragmented** by non-functional buttons and missing connections between features. The pre-built questions in Insights should be the easiest on-ramp for novice users, but they currently do nothing.

**Priority:** Fix the button connectivity issues to unlock the full value of the existing AI capabilities.
