# 🏗️ Stock Picker — Agent Command Center

> **Project:** Stock Picker — AI-Powered Indian Financial Expert & Investment Planner
> **Status:** Active Development
> **Created:** 2026-04-21

This folder is the **brain** of the Stock Picker project. It contains project-specific context, objectives, agent personas, memory, ideas, and performance tracking — all tailored to *this* codebase.

## Folder Structure

```
.agents/
├── README.md                  ← You are here
├── OBJECTIVE.md               ← North star, mission, current phase
├── ARCHITECTURE.md            ← System architecture & tech stack reference
├── context/
│   ├── project-state.md       ← Current state snapshot (update regularly)
│   ├── codebase-map.md        ← File-by-file map of what does what
│   └── data-dictionary.md     ← Schema, data sources, quality notes
├── agents/
│   ├── brainstormer.md        ← Creative ideation & research
│   ├── product-manager.md     ← Requirements, prioritization, roadmap
│   ├── backend-engineer.md    ← Python/FastAPI/SQLite → Postgres
│   ├── frontend-engineer.md   ← Next.js/React/TypeScript/Tailwind
│   ├── data-engineer.md       ← Pipelines, data quality, ingestion
│   └── ai-ml-engineer.md      ← Agent intelligence, recommendations, risk models
├── memory/
│   ├── decisions.md           ← Key decisions made and rationale
│   ├── learnings.md           ← What worked, what didn't
│   └── session-log.md         ← Brief log of each work session
├── planning/
│   ├── roadmap.md             ← Phased feature roadmap
│   ├── todos.md               ← Active task list (all agents)
│   ├── ideas.md               ← Feature ideas & brainstorms (backlog)
│   └── sprint.md              ← Current sprint / focus period
└── tracking/
    ├── performance.md         ← Platform performance metrics
    ├── data-quality.md        ← Data freshness, completeness, accuracy
    └── tech-debt.md           ← Known issues, shortcuts, debt to repay
```

## How to Use

1. **Starting a session?** → Read `OBJECTIVE.md` + `context/project-state.md`
2. **Need an expert?** → Reference the relevant agent in `agents/`
3. **Making a decision?** → Log it in `memory/decisions.md`
4. **Had an insight?** → Drop it in `planning/ideas.md`
5. **Finished work?** → Update `memory/session-log.md` + `planning/todos.md`

## Agent Coordination Protocol

When working on a task:
1. **Check** `OBJECTIVE.md` for current phase & priorities
2. **Read** `context/project-state.md` for latest state
3. **Consult** the relevant agent persona for domain expertise
4. **Log** decisions in `memory/decisions.md`
5. **Update** `planning/todos.md` when tasks complete
6. **Track** any data/performance issues in `tracking/`
