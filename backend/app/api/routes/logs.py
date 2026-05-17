from fastapi import APIRouter

from app.services.log_service import list_parse_warnings, list_review_logs


router = APIRouter()


@router.get("/api/review-logs")
def review_logs() -> list[dict]:
    return list_review_logs()


@router.get("/api/parse-runs/{parse_run_id}/warnings")
def parse_warnings(parse_run_id: str) -> list[dict]:
    return list_parse_warnings(parse_run_id)

