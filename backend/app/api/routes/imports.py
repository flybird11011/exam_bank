from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.db.models import ExamPaper
from app.services.import_service import (
    calculate_sha256_for_bytes,
    find_existing_paper_by_source_sha256,
    import_paper,
)
from app.services.paper_lifecycle_service import hard_delete_paper


router = APIRouter(prefix="/api/papers")


def _duplicate_payload(paper: ExamPaper, source_file_sha256: str, policy: str) -> dict:
    return {
        "code": "DUPLICATE_PAPER",
        "message": "检测到重复试卷",
        "duplicate_found": True,
        "duplicate_policy": policy,
        "source_file_sha256": source_file_sha256,
        "existing_paper": {
            "paper_id": paper.id,
            "title": paper.title,
            "subject": paper.subject,
            "region": paper.region,
            "exam_year": paper.exam_year,
            "exam_type": paper.exam_type,
            "source_file_name": paper.source_file_name,
            "created_at": paper.created_at.isoformat() if paper.created_at else None,
        },
    }


@router.post("/import")
async def import_paper_endpoint(
    file: UploadFile = File(...),
    subject: str = Form(...),
    region: str = Form(...),
    exam_year: int = Form(...),
    exam_type: str = Form(...),
    duplicate_policy: Literal["ask", "replace", "keep_both"] = Form("ask"),
) -> dict:
    file_bytes = await file.read()
    source_file_sha256 = calculate_sha256_for_bytes(file_bytes)
    duplicate_paper = find_existing_paper_by_source_sha256(source_file_sha256)
    if duplicate_paper is not None and duplicate_policy == "ask":
        raise HTTPException(status_code=409, detail=_duplicate_payload(duplicate_paper, source_file_sha256, duplicate_policy))

    suffix = Path(file.filename or "upload.docx").suffix or ".docx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        imported = import_paper(
            temp_path,
            source_file_name=file.filename or "upload.docx",
            subject=subject,
            region=region,
            exam_year=exam_year,
            exam_type=exam_type,
            source_file_sha256=source_file_sha256,
        )
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    if duplicate_paper is not None and duplicate_policy == "replace":
        cleanup_result = hard_delete_paper(duplicate_paper.id)
        warnings = cleanup_result.get("warnings", [])
        if warnings:
            imported["cleanup_warnings"] = warnings
        imported["replaced_paper_id"] = duplicate_paper.id

    return imported
