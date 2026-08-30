"""
app/services package
=======================

Shared business logic used by more than one route module — extracted
here specifically to avoid the class of bug this project has hit before:
the same computation (CPS, feature building, patient dict construction)
re-implemented slightly differently in two places and silently drifting
apart. If two routes need the same logic, it belongs here, not copied.
"""
