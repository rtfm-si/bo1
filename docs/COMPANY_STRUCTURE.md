Here’s the tight, practical checklist you need as a UK Ltd building and operating **Board of One**. This is not legal or tax advice, but it sets out the real-world areas founders typically must cover.

---

# 1. **Company Structure & Governance**

### You already have a Ltd — but ensure:

- **SIC codes** match your activities (typically 62012, 62090, 63990, 63110 depending on AI/SaaS).
- **Shareholder agreements** if anyone else will ever join.
- **IP assignment**:
  _Everything you, contractors, or AI agents create must be assigned to the company._
  Use: “IP Assignment Agreement” + contractor agreements with explicit IP clauses.

---

# 2. **Intellectual Property Protection**

### You cannot “protect” an idea, but you can protect execution:

- **Trademarks**:
  Trademark “Board of One” in the UK (and optionally EU + US).
  Protect the name + logo + key wording.
- **Copyright** automatically covers your code, UX, copy, models, prompts.
- **Trade secrets**:
  Your multi-agent structure, balancers, hidden moderators, weighting logic, persona pools → keep internal.
- **Patents** (unlikely):
  Only if a _genuinely novel technical process_, not “AI decision support”.

---

# 3. **Data Protection (GDPR)**

For a SaaS that processes _problems, decisions, possibly business-sensitive information_, you must be compliant:

### Must-have

- **Privacy Policy** (clear, accessible, covers AI usage)
- **Terms of Service** (liability limits, disclaimers, advisory nature)
- **Data Processing Register (Article 30 records)**
  For your internal audit trail
- **Data Processing Agreement** with your providers:

  - OpenAI/Anthropic
  - Supabase/Xano/FastAPI
  - Payment processors (Stripe etc)

### Specifics you must cover:

- **Data residency** – where your databases and LLM processing occur.
- **RTBF / account deletion** (you already implemented).
- **Data minimisation** — only store necessary prompts & outputs.
- **Automated decision-making**

  - You must state you _do not_ make legally binding automated decisions.

- **Subprocessor list**

  - Keep this public and updated.

---

# 4. **AI-Specific Regulatory Landscape**

### Today (2025):

- **UK: Pro-innovation framework**
  No single AI Act yet, but regulators (ICO, CMA, FCA) expect risk-managed AI systems.
- **EU AI Act** (if you have EU users)
  Your system is likely _“limited-risk general-purpose AI service”_, meaning:

  - Clear disclosures
  - No deceptive UX
  - User must understand when interacting with AI

### You must:

- Provide a **“Model & AI Use Disclosure”** page (short, plain language).
- Provide **limitations & accuracy disclaimers**.
- Provide **explainability-on-request** (you can satisfy this with “Why this recommendation?” inside meetings).

---

# 5. **Liability & Disclaimers**

Board of One is advisory, so ensure:

- **“Not professional advice”** disclaimer everywhere decision guidance is shown.
- **No fiduciary duty**.
- **You are not liable for business outcomes or decisions taken based on the platform**.
- Add **limitation of liability** clauses in the ToS:

  - Cap liability at the subscription fee.

- Explicit **no guarantee of accuracy**, because you're using LLMs.

---

# 6. **Tax Considerations (UK Ltd)**

### Corporate tax + SaaS costs

- **Corporation Tax**: 25% main rate
  You can deduct:

  - Cloud hosting
  - AI API calls
  - Hardware
  - Professional fees
  - Marketing
  - Software subscriptions

### R&D Tax Credits

Board of One almost certainly qualifies:

- Multi-agent architecture
- AI-augmented decision support
- Research into model prompting, orchestration, persona design
- Pipeline optimisation

Worth **significant tax relief** (usually ~20–33%).

### VAT

- Threshold: **£90k turnover**
- SaaS is typically **standard-rated** (20% VAT).
- Consider **VAT MOSS / OSS** if serving EU consumers.

### Employment vs contractor rules

If you hire freelancers, ensure they are outside IR35 and have clear contracts with IP assignment.

---

# 7. **Cybersecurity & Operational Compliance**

Especially important since you're processing business-sensitive data:

### You need:

- **ICO registration** (~£40/year)
- **Data breach response policy**
- **Password and MFA policy**
- **Backups** with retention schedule
- **Access controls**

  - Who within the company (you) can see meeting data?

- **Logging & Audit**
  You already have an audit table conceptually — good.

### If targeting teams plan:

- **DPA for customers** (they may request it)
- **Security overview PDF** (“Trust Centre” style)
- **Pen-test** (start lightweight; later do full external)

---

# 8. **Payments, Subscriptions & Consumer Law**

If you offer a free tier → consumer protection rules apply:

### You must:

- Provide **clear cancellation process**
- Provide **clear pricing per tier**
- Avoid “dark patterns”
- If selling to consumers (not only businesses), handle:

  - **14-day cooling-off** for digital services
  - **Refund policy** (your plan for usage-based refund evaluation is fine)

For business-only customers the rules are more relaxed, but don’t rely on that unless you _explicitly_ restrict signups to businesses.

---

# 9. **If You Process “Problem Data” from Customers**

Some users will enter:

- Commercially sensitive info
- HR disputes
- Legal situations
- Medical-ish decision making
- Financial decisions

You must:

- **Prohibit illegal or sensitive data uploads** in Terms.
- Provide **confidentiality guarantees** (technical + contractual).
- Explicitly state you do not process:

  - Special category personal data
  - Criminal offence data
    unless absolutely necessary and justified in GDPR terms.

---

# 10. **Future Regulations you should anticipate**

- **UK/EU platform transparency** requirements (expected 2026)
- **Model provenance tracking**
- **AI safety disclosures** (model version, update history)
- **User data control dashboards** (download, delete, visibility)

Board of One will survive all of these with small adjustments.

---

# Summary: What You Need to Do Now

## Immediate checklist

1. **Trademark Board of One**
2. **Draft Privacy Policy + ToS**
3. **Add advisory disclaimers to all recommendations**
4. **ICO registration**
5. **DPAs with all vendors**
6. **Maintain Article 30 processing records**
7. **Implement access controls & logging**
8. **Add clear AI usage disclosure**
9. **Enable cooling-off + cancellation workflows (if selling to consumers)**
10. **Prepare R&D claim evidence while building**

---

If you want, I can generate:

- A complete **ToS + Privacy Policy pack**
- A **Trust Centre** page
- A **subprocessor list**
- A **data flow diagram**
- A **risk assessment (DPIA)**
- A **legal checklist to embed in your onboarding workflow**

Just tell me which pieces you want.
