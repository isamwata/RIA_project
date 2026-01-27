"""Storage for RIA assessments."""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Data directory for RIA assessments
DATA_DIR = Path("data/ria_assessments")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _get_assessment_path(assessment_id: str) -> Path:
    """Get file path for an assessment."""
    return DATA_DIR / f"{assessment_id}.json"


def create_assessment(assessment_id: str, proposal: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a new assessment record."""
    assessment = {
        "assessment_id": assessment_id,
        "proposal": proposal,
        "metadata": metadata or {},
        "status": "generating",
        "report": None,
        "review": None,
        "workflow_metadata": {},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "approved_at": None
    }
    
    path = _get_assessment_path(assessment_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(assessment, f, indent=2, ensure_ascii=False)
    
    return assessment


def get_assessment(assessment_id: str) -> Optional[Dict[str, Any]]:
    """Get an assessment by ID."""
    path = _get_assessment_path(assessment_id)
    if not path.exists():
        return None
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def update_assessment(assessment_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update an assessment with new data."""
    assessment = get_assessment(assessment_id)
    if assessment is None:
        raise ValueError(f"Assessment {assessment_id} not found")
    
    assessment.update(updates)
    assessment["updated_at"] = datetime.now().isoformat()
    
    path = _get_assessment_path(assessment_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(assessment, f, indent=2, ensure_ascii=False)
    
    return assessment


def list_assessments(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all assessments, optionally filtered by status."""
    assessments = []
    
    for path in DATA_DIR.glob("*.json"):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                assessment = json.load(f)
                if status is None or assessment.get("status") == status:
                    # Return metadata only (exclude full report for list view)
                    assessments.append({
                        "assessment_id": assessment["assessment_id"],
                        "proposal": assessment["proposal"][:200] + "..." if len(assessment["proposal"]) > 200 else assessment["proposal"],
                        "metadata": assessment.get("metadata", {}),
                        "status": assessment.get("status", "unknown"),
                        "created_at": assessment.get("created_at"),
                        "approved_at": assessment.get("approved_at"),
                        "review": assessment.get("review")
                    })
        except Exception as e:
            print(f"Error reading assessment {path}: {e}")
            continue
    
    # Sort by created_at descending (newest first)
    assessments.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return assessments


def approve_assessment(assessment_id: str, reviewer: str = "system", comments: str = "") -> Dict[str, Any]:
    """Approve an assessment and save it."""
    assessment = get_assessment(assessment_id)
    if assessment is None:
        raise ValueError(f"Assessment {assessment_id} not found")
    
    assessment["status"] = "approved"
    assessment["review"] = {
        "reviewed_at": datetime.now().isoformat(),
        "reviewer": reviewer,
        "action": "approve",
        "comments": comments
    }
    assessment["approved_at"] = datetime.now().isoformat()
    assessment["updated_at"] = datetime.now().isoformat()
    
    path = _get_assessment_path(assessment_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(assessment, f, indent=2, ensure_ascii=False)
    
    return assessment


def reject_assessment(assessment_id: str, reviewer: str = "system", comments: str = "") -> Dict[str, Any]:
    """Reject an assessment."""
    assessment = get_assessment(assessment_id)
    if assessment is None:
        raise ValueError(f"Assessment {assessment_id} not found")
    
    assessment["status"] = "rejected"
    assessment["review"] = {
        "reviewed_at": datetime.now().isoformat(),
        "reviewer": reviewer,
        "action": "reject",
        "comments": comments
    }
    assessment["updated_at"] = datetime.now().isoformat()
    
    path = _get_assessment_path(assessment_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(assessment, f, indent=2, ensure_ascii=False)
    
    return assessment
