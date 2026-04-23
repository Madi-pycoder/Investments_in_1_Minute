1. Core Architecture Layers:

Data Layer:
Responsible for fetching and structuring raw data.

Modules:
portfolio_data.py
market.py
requests.py

Responsibilities:
Load portfolio (positions, cash)
Fetch prices
Fetch stock metadata (sector, etc.)
Load user goals


Compute Layer (Brain):
Main logic of the system.

Modules:
portfolio_compute.py
goal_engine.py
riskmanagement.py
shariah_optimizer.py
sharpe_optimizer.py

Responsibilities:
Portfolio metrics (PnL, weights)
Risk calculation
Goal simulations (Monte Carlo)
Optimization (Sharpe, Shariah, Goals)
Scenario analysis


Decision Layer:
Transforms raw computations into actions.

Key Outputs:
Rebalance trades
Auto-invest plan
Goal optimization scenarios
AI nudges

Key Functions:
optimize_portfolio_for_goals
generate_auto_invest_plan
calculate_rebalance


Presentation Layer (UX)
User interaction via Telegram.

Modules:
portfolio.py
portfolio_view.py
keyboards.py

Responsibilities:
Render portfolio
Display insights
Provide buttons (actions)
Handle user flows





2. Data Flow:

User → Telegram UI
      ↓
portfolio.py (handler)
      ↓
load_portfolio_data()
      ↓
compute_portfolio_metrics()
      ↓
[goal_engine + risk + optimizers]
      ↓
metrics dict
      ↓
build_portfolio_text()
      ↓
Telegram respo





3. Goal Engine (Core Innovation)
Components:
1. Simulation Engine:
Monte Carlo
Probability of success
2. Goal Analyzer:
Difficulty classification
Monthly contribution required
3. Optimizer:
Risk vs contribution tradeoff
Multi-goal balancing
4. Behavior Layer:
Smart nudges
What-if scenarios




4. Key System Concepts

4.1 Portfolio → Goals Mapping

Portfolio is not evaluated by return only.
Instead:
"Can this portfolio achieve your goals?"

4.2 Action-Oriented Design

Every insight must lead to action:
Low probability → Increase contribution
High risk → Reduce volatility
Imbalance → Rebalance

4.3 Async Performance Model

Heavy computations run concurrently:
Risk
Sharpe optimization
Halal portfolio generation
Using:
asyncio.gather()





5. Current Weak Points
5.1 Coupling:
compute_portfolio_metrics does too much
Hard to test components independently

5.2 Implicit Contracts:
Dict-based communication (metrics[...])
No strict schema

5.3 Limited Extensibility:
Adding new strategies requires editing core logic






6. Next Evolution (Important)
6.1 Introduce Typed Models
Replace dicts with structured objects:

class GoalResult:
    probability: float
    expected: float
    worst: float

6.2 Split Compute Layer
Break into services:
  GoalService
  RiskService
  OptimizationService

6.3 Decision Engine (NEW)
Create central engine:

class DecisionEngine:
    def generate_actions(metrics):
        return actions

6.4 UX Layer Upgrade
Move from text → interactive flows:
  Buttons per insight
  Scenario switching
  Inline updates
