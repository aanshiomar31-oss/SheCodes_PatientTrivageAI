"""
api/routes package
====================

Each clinical/operational concern gets its own route module
(`health.py` today; `triage.py`, `recommendations.py`, `audit.py`,
`overrides.py` etc. in future milestones). `api/router.py` assembles
them into the single `api_router` mounted by `app/main.py`.
"""
