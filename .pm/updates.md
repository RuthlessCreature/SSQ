## 2026-04-23
- Documented the stable backtest v2 design for SSQ
- Added an implementation plan focused on tune/validate backtesting and portfolio-based scoring
- Created initial `.pm` project metadata for future maintenance
- Ran smoke validation for portfolio scoring, tune/validate backtesting, config coverage, deterministic ticket generation, and Flask rendering
- Updated project metadata to reflect stable backtest v2 implementation and validation status
- Changed parameter ranking to maximize validation expected value lower-confidence-bound (EV-LCB) instead of coverage-oriented score
- Added UI metrics for validation EV, risk-adjusted EV, per-ticket EV, and standard error
