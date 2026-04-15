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
