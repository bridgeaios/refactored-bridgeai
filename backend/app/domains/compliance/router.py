"""Compliance domain router — legal docs upload/download and AI suggestions."""
from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.domains.compliance.deps import get_compliance
from app.domains.compliance.services import ComplianceService
from app.domains.crm.deps import get_crm
from app.domains.crm.services import CrmService
from app.domains.infra.deps import require_jwt

log = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["compliance"])

ComplianceDep = Annotated[ComplianceService, Depends(get_compliance)]
CrmDep        = Annotated[CrmService,        Depends(get_crm)]

_MAX_DOC_SIZE = 10 * 1024 * 1024  # 10 MB


# ------------------------------------------------------------------ #
# Legal docs                                                          #
# ------------------------------------------------------------------ #

@router.get("/docs")
async def list_docs(
    svc: ComplianceDep,
    _: dict = Depends(require_jwt),
    contact_id: str = "",
) -> dict[str, Any]:
    docs = await svc.list_docs(contact_id=contact_id)
    return {"ok": True, "docs": docs, "count": len(docs)}


@router.post("/docs/upload")
async def upload_doc(
    svc: ComplianceDep,
    claims: dict = Depends(require_jwt),
    file: UploadFile = File(...),
    doc_type: str = Form("other"),
    notes: str = Form(""),
    contact_id: str = Form(""),
) -> dict[str, Any]:
    content = await file.read()
    if len(content) > _MAX_DOC_SIZE:
        raise HTTPException(413, detail="File exceeds 10 MB limit")

    allowed_ext = {".pdf", ".docx", ".doc", ".txt", ".xlsx", ".csv", ".png", ".jpg"}
    filename = file.filename or "document"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed_ext:
        raise HTTPException(415, detail=f"File type '{ext}' not allowed")

    record = await svc.save_doc(
        filename=filename,
        content=content,
        doc_type=doc_type,
        notes=notes,
        contact_id=contact_id,
        uploader=claims.get("sub", ""),
    )
    return {"ok": True, "doc": record}


@router.get("/docs/{doc_id}/download")
async def download_doc(
    doc_id: str,
    svc: ComplianceDep,
    _: dict = Depends(require_jwt),
) -> Response:
    result = await svc.get_doc_bytes(doc_id)
    if not result:
        raise HTTPException(404, detail="Document not found")
    content, filename = result
    media_type = "application/octet-stream"
    if filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".csv"):
        media_type = "text/csv"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/docs/{doc_id}")
async def delete_doc(
    doc_id: str,
    svc: ComplianceDep,
    _: dict = Depends(require_jwt),
) -> dict[str, Any]:
    deleted = await svc.delete_doc(doc_id)
    if not deleted:
        raise HTTPException(404, detail="Document not found")
    return {"ok": True}


# ------------------------------------------------------------------ #
# AI suggestions                                                       #
# ------------------------------------------------------------------ #

@router.get("/ai-suggestions")
async def ai_suggestions(
    svc: ComplianceDep,
    crm: CrmDep,
    _: dict = Depends(require_jwt),
    contact_id: str = "",
    context: str = "",
) -> dict[str, Any]:
    contact: dict[str, Any] | None = None
    if contact_id:
        contact = await crm.get_lead(contact_id)

    docs = await svc.list_docs(contact_id=contact_id)
    existing_types = [d.get("doc_type", "other") for d in docs]

    suggestions = await svc.ai_suggestions(
        contact=contact,
        existing_doc_types=existing_types,
        extra_context=context,
    )
    return {"ok": True, "suggestions": suggestions, "contact_id": contact_id}
