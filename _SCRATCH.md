http://localhost:5173/meeting/bo1_4eefdf7e-4b0e-474a-9df4-032c5a879386

0. framework - incorporate conciseness into prompts for meetings?

1. meeting 'failed' but looks like it mostly completed

Error Type: AttributeError
Message:
'dict' object has no attribute 'sub_problems'

2. Discussion quality should show the latest 'quality' marker, dont overwrite with 'Discussion Complete Complete
   Experts have concluded their deliberation and reached recommendations.'

3. ntfy alert shows 0 saved contributions

4. If i refresh the meeting page, some meeting shows events that should be masked:
   subproblem_started
   research_results

5. research_results event shows cached and non cached results. Double check and make sure the results are being stored, and embeddings generated etc so they can be searched and reused later. are these research items properly indexed and partitioned for performance?
