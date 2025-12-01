# Documentation - Current System

This directory contains documentation for the **current v2 production system** at boardof.one.

## Purpose

User-facing documentation, architecture guides, and technical references for understanding and maintaining the active production system.

## What Belongs Here

- **System Architecture**: How the current system works (graph flow, deliberation, persistence)
- **Technical Implementation**: Database schema, API design, event streaming
- **Developer Guides**: Getting started, testing, deployment processes
- **User Documentation**: Demo guides, troubleshooting, support materials
- **Configuration Reference**: Environment variables, feature flags, settings

## What Does NOT Belong Here

- ❌ Build/deployment infrastructure details → See `/zzz_project/detail/`
- ❌ Historical implementation notes → See `/zzz_project/archive/`
- ❌ Speculative/future features → See `/zzz_project/archive/`
- ❌ Project meta-documents (company structure, etc.) → See `/zzz_project/archive/`

## Key Documents

**Start Here:**
- `QUICKSTART.md` - Get the system running locally
- `DEMO.md` - User walkthrough
- `CLAUDE.md` (in root) - System overview and critical patterns

**Architecture:**
- `PLATFORM_ARCHITECTURE.md` - Overall system design
- `GRAPH_FLOW_IMPLEMENTATION.md` - LangGraph deliberation flow
- `LOOP_PREVENTION.md` - Safety mechanisms
- `COMPLEXITY_SCORING.md` - Adaptive deliberation parameters

**Current Issues & Fixes:**
- `MEETING_SYSTEM_AUDIT_REPORT.md` - Latest audit (2025-11-30) with priority fixes
- `PARALLEL_SUBPROBLEMS_EVENT_EMISSION_FIX.md` - Known issue implementation plan

**Technical References:**
- `DATABASE_SCHEMA.md` - PostgreSQL schema + persistence architecture
- `REDIS_KEY_PATTERNS.md` - Redis data structures
- `ENVIRONMENT_VARIABLES.md` - Configuration reference
- `DOCKER_ARCHITECTURE.md` - Container setup

**Deployment:**
- `BLUE_GREEN_DEPLOYMENT.md` - Production deployment process
- `MIGRATIONS_GUIDE.md` - Database migration workflow
- `PRODUCTION_DEPLOYMENT_QUICKSTART.md` - Deploy checklist

**Development:**
- `CODE_REVIEW_GUIDELINES.md` - Review standards
- `TESTING.md` - Test strategy and commands
- `TROUBLESHOOTING.md` - Common issues and solutions
- `AI_OVERRIDE_GUIDE.md` - Model selection override for testing

## Document Maintenance

**When to Add Documents:**
- New features implemented and deployed to production
- Architecture changes that affect current system
- New operational procedures or runbooks
- Updated troubleshooting guidance

**When to Remove Documents:**
- Features removed from production
- Architecture superseded by new design
- Outdated procedures or guides

**When to Archive Documents:**
- Completed implementation work (move to `/zzz_project/archive/`)
- Superseded by newer documentation (consolidate or archive)
- Historical reference value but not current (move to `/zzz_project/archive/`)

---

**Last Updated:** 2025-12-01
**System Version:** v2 Production
