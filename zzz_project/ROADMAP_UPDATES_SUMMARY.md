# MVP Roadmap Updates Summary

**Date**: 2025-11-15
**Status**: ✅ Completed - All changes applied to MVP_IMPLEMENTATION_ROADMAP.md

## Changes Required

### 1. Day 31: Add Background Summarizer
- **Current**: Only has voting + synthesis nodes
- **Add**: Background summarizer integration for hierarchical context management
- **Reason**: Prevents quadratic context growth, uses Haiku 4.5 for cost efficiency

### 2. Week 8 (Days 50-51): GDPR Compliance Enhancement
- **Current**: Has data export/deletion endpoints
- **Add**: Strong emphasis on authentication & authorization requirements
- **Note**: "MUST have permission & auth to do so" for ALL user data operations

### 3. Day 57: Admin Resume/Restart Killed Sessions
- **Current**: Runaway session detection (no resume mentioned)
- **Question**: Should we allow admin to resume or restart killed sessions?
- **Decision Needed**: Add this capability or explicitly document why not

### 4. SLO Refund/Credits Policy Revision
- **Current**: Likely mentions cash refunds
- **New**: Offer extra deliberations or extra experts instead of cash refunds
- **Reason**: Better for user engagement and platform stickiness

### 5. Day 66: Remove Pie Charts
- **Current**: Cost analytics dashboard mentions pie charts
- **Remove**: "Cost by tier (pie chart)"
- **Replace with**: Bar chart or table

### 6. Day 67: Add Promo Code Features
- **Current**: User management (view/ban/delete)
- **Add**:
  - Apply promo code to user account
  - Send email notification when promo applied

### 7. Day 79: Email Preferences for Deliberation Complete
- **Current**: "Only send if user has emails enabled"
- **Enhance**: Make it explicit that users can toggle whether emails are sent
- **Remove**: Cost metrics from email (optional, user preference)

### 8. Day 82: Remove Session State Change Emails
- **Current**: Session expired email
- **Action**: Remove this entire feature (paused/resumed/expired emails)
- **Reason**: Reduce email noise, focus on actionable notifications

### 9. Global: AI-Generated Content Disclaimer
- **Location**: Add to synthesis reports, action recommendations
- **Text**:
  - "This content is AI-generated for learning and knowledge purposes only, not advisory."
  - "Always verify using licensed legal/finance professionals for your location."
- **Apply to**: All deliberation outputs, synthesis reports, recommendations

### 10. Post-Deliberation: Action Tracking with Follow-Up
- **Reference**: zzz_project/detail/ACTION_TRACKING_FEATURE.md
- **Features**:
  - Extract actions from synthesis
  - Follow-up tracking: "How's progress going against X? Any issues? Want help?"
  - Allow replanning when situation changes
- **Timeline**: Post-MVP (Phases 2-3)

## Implementation Priority

1. **Critical (Week 4-5)**: #1 (Summarizer), #9 (Disclaimer)
2. **Important (Week 8)**: #2 (GDPR), #4 (SLO), #5 (Charts), #6 (Promo), #7 (Email prefs), #8 (Remove emails)
3. **Decision Needed**: #3 (Admin resume)
4. **Post-MVP**: #10 (Action tracking - already documented separately)

## Next Steps

1. Apply changes to MVP_IMPLEMENTATION_ROADMAP.md
2. Update relevant documentation (GDPR_COMPLIANCE.md, etc.)
3. Create decision ticket for #3 (admin resume capability)
