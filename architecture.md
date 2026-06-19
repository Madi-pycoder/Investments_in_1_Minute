# Architecture Overview

Investments in 1 Minute is a modular AI-powered investment platform built around multiple independent financial engines.

The system is designed to transform:

Market Data → Financial Intelligence → Investment Decisions

while maintaining high responsiveness through asynchronous processing and caching.

---

# High-Level Architecture

User
↓
Telegram Interface
↓
Application Layer
↓
Financial Intelligence Layer
↓
Data Layer
↓
External Market Sources / Database

---

# Core Architecture Layers

## 1. Presentation Layer

Responsible for user interaction.

Modules:

- markethandler.py
- portfolio_view_handler.py
- keyboards.py
- onboarding flows
- FSM states

Responsibilities:

- User interaction
- Navigation
- Rendering analytics
- Portfolio actions
- Goal management
- Auto-Invest flows

Output:

Human-readable investment decisions.

---

## 2. Application Layer

Acts as orchestration layer between UI and financial engines.

Responsibilities:

- Request routing
- Workflow coordination
- State management
- Cache interaction
- Async execution

Examples:

- Show Portfolio
- Deep Audit
- Goal Dashboard
- Auto-Invest execution

---

## 3. Financial Intelligence Layer

Core product differentiation.

Contains multiple independent engines.

---

### Stock Analyzer

Purpose:

Analyze individual stocks.

Outputs:

- fundamentals
- growth metrics
- risk profile
- Shariah status
- key takeaways

Dependencies:

- market.py
- riskmanagement.py
- shariah.py

---

### ETF Analyzer

Purpose:

Analyze ETFs.

Outputs:

- holdings exposure
- risk profile
- compliance exposure
- portfolio concentration

Dependencies:

- ETF holdings engine
- Risk engine
- Shariah engine

---

### Risk Engine

Modules:

- riskmanagement.py

Calculates:

- volatility
- beta
- sharpe ratio
- drawdown
- risk score

Used by:

- Stock Analyzer
- ETF Analyzer
- Portfolio Diagnosis
- Financial Brain

---

### Goal Engine

Purpose:

Measure portfolio ability to achieve user goals.

Components:

1. Simulation Engine

- Monte Carlo simulations
- probability of success

2. Goal Analyzer

- goal difficulty
- expected outcomes
- contribution requirements

3. Goal Insights

- milestone tracking
- personalized recommendations

Core principle:

Portfolio performance is evaluated through goals,
not returns alone.

---

### Financial Brain

Purpose:

Generate portfolio intelligence.

Inputs:

- portfolio metrics
- goals
- risk profile
- allocation structure

Outputs:

- strategic observations
- portfolio diagnostics
- recommendations
- behavioral nudges

Role:

Acts as portfolio advisor.

---

### Auto-Invest Engine

Purpose:

Convert monthly budgets into investment actions.

Flow:

Budget
↓
Target Allocation
↓
Portfolio Analysis
↓
Purchase Plan

Outputs:

Actionable monthly investment plan.

---

### Shariah Engine

Purpose:

Provide compliance screening.

Capabilities:

- Stock screening
- ETF screening
- Portfolio screening
- Compliance exposure tracking

Components:

Business Screen

Financial Ratio Screen

Portfolio Compliance Engine

Outputs:

- Passed
- Mostly Passed
- Mixed Exposure
- Limited Compliance

---

# Data Layer

Responsible for acquiring and structuring information.

Modules:

- market.py
- portfolio_data.py
- requests.py

Responsibilities:

- market prices
- fundamentals
- holdings
- portfolio data
- goal data

---

# Persistence Layer

Primary Database:

PostgreSQL

Stores:

- users
- portfolios
- transactions
- positions
- goals
- historical prices

Purpose:

Create a single source of truth for the platform.

---

# Caching Layer

Introduced to reduce expensive recomputation.

Caches:

- ticker analysis
- portfolio views
- diagnosis results
- market data

Benefits:

- lower latency
- reduced API load
- better user experience

Core principle:

Compute once.
Reuse many times.

---

# Analytics Layer

Purpose:

Track product usage and behavior.

Examples:

- stock_analyzed
- etf_analyzed
- portfolio_opened
- goal_created

Used for:

- product improvement
- feature evaluation
- user behavior analysis

---

# Data Flow Example

Portfolio View

User
↓
Portfolio Handler
↓
Load Portfolio Data
↓
Cache Check
↓
Portfolio Metrics
↓
Goal Engine
↓
Risk Engine
↓
Financial Brain
↓
Portfolio View Builder
↓
Telegram Response

---

# Key Architectural Principles

## Decision-Oriented Design

The platform does not stop at analytics.

Every insight should lead to action.

Examples:

Low probability
→ Increase contribution

High concentration
→ Rebalance

Excess cash
→ Invest

Low compliance
→ Review positions

---

## Explainability

Recommendations must be transparent.

System explains:

- what
- why
- impact

rather than producing black-box outputs.

---

## Async First

Heavy calculations execute concurrently whenever possible.

Examples:

- risk calculations
- compliance checks
- portfolio diagnostics

Built using:

asyncio

---

## Modular Engines

Each financial engine operates independently.

Benefits:

- easier testing
- easier upgrades
- lower coupling

---

# Current Technical Debt

## Large Portfolio Compute Module

Some portfolio computations remain centralized.

Potential improvement:

PortfolioService

RiskService

GoalService

---

## Dict-Based Contracts

Many engines communicate using dictionaries.

Potential improvement:

Pydantic models

Typed schemas

---

## Shared State Complexity

Some flows still depend heavily on FSM state.

Potential improvement:

Dedicated service layer.

---

# Long-Term Vision

Phase 1 — Intelligent Investment Assistant

✓ Portfolio Analysis

✓ Goal Planning

✓ Auto-Invest

✓ Shariah Screening

✓ Financial Brain

---

Phase 2 — Personalized Robo-Advisor

• Dynamic Strategies

• Rebalancing Engine

• Adaptive Risk Management

• Multi-Goal Optimization

---

Phase 3 — Autonomous Portfolio Agent

Self-improving investment system capable of:

- analyzing portfolios
- planning allocations
- optimizing toward goals
- maintaining compliance

with minimal user intervention.
