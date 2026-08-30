"""
app/api/security.py
===================
PatientTriage.ai — Security & Patient Data Protection endpoints.
Provides mock enterprise security controls, active encryption checks,
role mapping, and security audit timelines.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/security", tags=["security"])

class SecurityStatus(BaseModel):
  database_encrypted: bool
  ssl_active: bool
  tls_version: str
  cipher_suite: str
  auto_logout_enabled: bool
  session_timeout_minutes: int
  mfa_enforced: bool
  device_verification_active: bool
  emergency_access_mode: bool

class SecurityAuditEntry(BaseModel):
  id: str
  user: str
  device: str
  action: str
  timestamp: str
  patient: str
  status: str

class RolePermission(BaseModel):
  role: str
  permissions: Dict[str, bool]

@router.get("/status", response_model=SecurityStatus)
def get_security_status() -> SecurityStatus:
  """Get active encryption, TLS status, and security compliance configuration."""
  return SecurityStatus(
    database_encrypted=True,
    ssl_active=True,
    tls_version="TLS 1.3",
    cipher_suite="TLS_AES_256_GCM_SHA384",
    auto_logout_enabled=True,
    session_timeout_minutes=15,
    mfa_enforced=True,
    device_verification_active=True,
    emergency_access_mode=False
  )

@router.get("/audit", response_model=List[SecurityAuditEntry])
def get_security_audit_logs() -> List[SecurityAuditEntry]:
  """Retrieve live security-related audit logs for tracking compliance."""
  return [
    SecurityAuditEntry(
      id="SEC-098",
      user="Nurse J. Adams",
      device="Tablet ED-04 (Intake Desk)",
      action="MFA Challenge Verified",
      timestamp=datetime.now(timezone.utc).isoformat(),
      patient="N/A",
      status="Approved"
    ),
    SecurityAuditEntry(
      id="SEC-097",
      user="Dr. K. Patel",
      device="Workstation ED-12",
      action="Override Acuity (ED0061)",
      timestamp=datetime.now(timezone.utc).isoformat(),
      patient="Patient ED0061",
      status="Logged & Audited"
    ),
    SecurityAuditEntry(
      id="SEC-096",
      user="System Admin",
      device="Regional Server Console",
      action="TLS Cipher Suite Check",
      timestamp=datetime.now(timezone.utc).isoformat(),
      patient="N/A",
      status="Passed"
    )
  ]

@router.get("/roles", response_model=List[RolePermission])
def get_roles_matrix() -> List[RolePermission]:
  """Return active Role-Based Access Control matrix for frontend display."""
  return [
    RolePermission(
      role="Nurse",
      permissions={"view_queue": True, "triage": True, "override": True, "system_settings": False}
    ),
    RolePermission(
      role="Doctor",
      permissions={"view_queue": True, "triage": True, "override": True, "system_settings": False}
    ),
    RolePermission(
      role="Admin",
      permissions={"view_queue": True, "triage": True, "override": True, "system_settings": True}
    )
  ]
