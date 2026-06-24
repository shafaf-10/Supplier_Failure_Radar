"""
Database middleware removed.

Reason:
The supplier pipeline uses SQLAlchemy engine directly.
No per-request database session is created here.
Keeping this middleware as a no-op creates dead code.
"""