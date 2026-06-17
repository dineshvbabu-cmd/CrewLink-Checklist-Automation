from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from io import BytesIO
from typing import Any, Dict, List, Literal, Optional
import asyncio
import os
import secrets

import anthropic
import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from persistence import (
    authenticate_user,
    create_session,
    data_dir,
    db_path,
    delete_session,
    get_attachment,
    get_user_by_token,
    init_database,
    load_state,
    reset_state,
    save_attachment,
    save_state,
)

AIStatus = Literal["green", "yellow", "red", "grey"]

app = FastAPI(title="Crewlink AI-ACE Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REFERENCE_DATE = "17-Jun-2026"
TOKEN_SECURITY = HTTPBearer(auto_error=False)
ROLE_ADMIN = "admin"
ROLE_RC = "rc"
ROLE_OPS = "ops"

SEED_USERS = [
    {
        "user_id": "u_admin",
        "username": "admin",
        "full_name": "Aparna Menon",
        "role": ROLE_ADMIN,
        "password": "CrewlinkAdmin!23",
    },
    {
        "user_id": "u_rc",
        "username": "rc",
        "full_name": "Prazy Jandyal",
        "role": ROLE_RC,
        "password": "CrewlinkRC!23",
    },
    {
        "user_id": "u_ops",
        "username": "ops",
        "full_name": "Shital Patil",
        "role": ROLE_OPS,
        "password": "CrewlinkOps!23",
    },
]


def now_stamp() -> str:
    return datetime.now(UTC).strftime("%d-%b-%Y %H:%M UTC")


@app.get("/api/health")
def healthcheck():
    return {"ok": True, "service": "crewlink-ace-api"}


BASE_VESSEL = {
    "id": "v001",
    "name": "ALKEBULAN",
    "type": "OIL TANKER",
    "imo": "IMO 9248423",
    "flag": "Marshall Islands",
    "totalCrew": 24,
    "reliefOverdue": 1,
    "dueOneMonth": 1,
    "extraCrew": 0,
    "extendedContract": 0,
    "reducedContract": 0,
}

BASE_CREW = [
    {
        "id": "c001",
        "srNo": 1,
        "rank": "MST",
        "name": "Hilton Henry Barreto",
        "empNo": "A6227",
        "nationality": "Indian",
        "travelDate": "25-Jul-2026",
        "signOnDate": "28-Jul-2026",
        "reliefDue": "28-Jan-2027",
        "relieverRank": "MST",
        "relieverName": "R. Sharma",
        "relieverApproved": True,
        "aiStatus": "green",
        "complianceIssue": False,
        "status": "planned",
    },
    {
        "id": "c002",
        "srNo": 2,
        "rank": "A3O",
        "name": "Francis Zamani Duniya",
        "empNo": "A5743",
        "nationality": "Nigerian",
        "travelDate": "20-Jul-2026",
        "signOnDate": "23-Jul-2026",
        "reliefDue": "23-Jan-2027",
        "relieverRank": "A3O",
        "relieverName": "P. Kumar",
        "relieverApproved": False,
        "aiStatus": "red",
        "complianceIssue": True,
        "status": "planned",
    },
    {
        "id": "c003",
        "srNo": 3,
        "rank": "CO",
        "name": "Anish Ranjan Singh",
        "empNo": "A0806",
        "nationality": "Indian",
        "travelDate": "10-Jul-2026",
        "signOnDate": "13-Jul-2026",
        "reliefDue": "16-Jul-2026",
        "relieverRank": "CO",
        "relieverName": "M. Patel",
        "relieverApproved": True,
        "aiStatus": "yellow",
        "complianceIssue": False,
        "status": "onboard",
    },
]

BASE_DOCUMENTS: Dict[str, Dict[str, Any]] = {
    "c001": {
        "sections": [
            {
                "title": "Travel Documents",
                "items": [
                    {"srNo": 1, "name": "Passport", "docNo": "N8724561", "type": "Travel", "issueDate": "12-Mar-2021", "expiryDate": "11-Mar-2031", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 2, "name": "CDC (Continuous Discharge Certificate)", "docNo": "IND-CDC-A6227", "type": "Travel", "issueDate": "05-Jan-2020", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 3, "name": "Yellow Fever Certificate", "docNo": "YF2024-A6227", "type": "Medical", "issueDate": "10-Feb-2024", "expiryDate": "Unlimited", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
            {
                "title": "License (National & Flag)",
                "items": [
                    {"srNo": 4, "name": "Certificate of Competency (Master)", "docNo": "IND-COC-MST-2019", "type": "II/2", "issueDate": "15-Jun-2019", "expiryDate": "14-Jun-2029", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 5, "name": "GMDSS Radio Operator Certificate IV/2", "docNo": "GMDSS-IND-2020", "type": "IV/2", "issueDate": "22-Aug-2020", "expiryDate": "21-Aug-2025", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 6, "name": "Flag CDC I/10 (Marshall Islands)", "docNo": "MI-CDC-MST-2023", "type": "I/10", "issueDate": "08-Apr-2023", "expiryDate": "07-Apr-2028", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
            {
                "title": "STCW Basic Courses",
                "items": [
                    {"srNo": 7, "name": "Security Training For Seafarers (STSDSD)", "docNo": "STSDSD-2022-A6227", "type": "STCW-Basic", "issueDate": "03-Mar-2022", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 8, "name": "Personal Safety and Social Responsibilities", "docNo": "PSSR-2022-A6227", "type": "STCW-Basic", "issueDate": "03-Mar-2022", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 9, "name": "PSSR Amendment 2026", "docNo": "PSSR26-2026-A6227", "type": "STCW-Basic", "issueDate": "15-Jan-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
            {
                "title": "STCW Courses",
                "items": [
                    {"srNo": 10, "name": "ECDIS - Generic", "docNo": "ECDIS-GEN-2021", "type": "STCW", "issueDate": "10-Nov-2021", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 11, "name": "Advance Fire Fighting", "docNo": "AFF-2020-A6227", "type": "STCW", "issueDate": "20-Sep-2020", "expiryDate": "19-Sep-2025", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 12, "name": "Radar Observer Simulator", "docNo": "RADAR-2022-A6227", "type": "STCW", "issueDate": "05-Dec-2022", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 13, "name": "Medical First Aid", "docNo": "MFA-2021-A6227", "type": "STCW", "issueDate": "18-Jul-2021", "expiryDate": "17-Jul-2026", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
            {
                "title": "Company Courses (Vessel Specific)",
                "items": [
                    {"srNo": 14, "name": "ECDIS - JRC (Type Specific)", "docNo": "JRC-2023-A6227", "type": "Vessel Specific", "issueDate": "12-Feb-2023", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 15, "name": "Advance Training for Oil Tanker Cargo Operations", "docNo": "ATOT-2022-A6227", "type": "Vessel Specific", "issueDate": "28-Jun-2022", "expiryDate": "27-Jun-2027", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
            {
                "title": "Other Documents / Pre-joining Docs",
                "items": [
                    {"srNo": 16, "name": "Interview Sheet (FP01D)", "docNo": "FP01D-A6227-2026", "type": "Company", "issueDate": "01-Jul-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 17, "name": "Offer Letter (FP01A)", "docNo": "FP01A-A6227-2026", "type": "Company", "issueDate": "01-Jul-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
            {
                "title": "Post Departure Documents",
                "items": [
                    {"srNo": 18, "name": "Briefing Prior Crew Travel (FP06F)", "docNo": "FP06F-A6227-2026", "type": "Company", "issueDate": "24-Jul-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 19, "name": "Seafarer's Employment Agreement", "docNo": "SEA-A6227-2026", "type": "Company", "issueDate": "24-Jul-2026", "expiryDate": "28-Jan-2027", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 20, "name": "Terms of Employment for Seafarers (FP01C)", "docNo": "FP01C-A6227-2026", "type": "Company", "issueDate": "01-Jul-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 21, "name": "Undertaking by Seafarer (FP02C)", "docNo": "FP02C-A6227-2026", "type": "Company", "issueDate": "01-Jul-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
        ]
    },
    "c002": {
        "sections": [
            {
                "title": "Travel Documents",
                "items": [
                    {"srNo": 1, "name": "Passport", "docNo": "A12345678", "type": "Travel", "issueDate": "20-May-2022", "expiryDate": "19-May-2032", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 2, "name": "CDC (Continuous Discharge Certificate)", "docNo": "NGA-CDC-A5743", "type": "Travel", "issueDate": "10-Mar-2021", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 3, "name": "Yellow Fever Certificate", "docNo": "YF2023-A5743", "type": "Medical", "issueDate": "05-Jan-2023", "expiryDate": "Unlimited", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
            {
                "title": "License (National & Flag)",
                "items": [
                    {"srNo": 4, "name": "Officer in Charge of Navigational Watch II/1", "docNo": "NGA-COC-II1-2020", "type": "II/1", "issueDate": "15-Aug-2020", "expiryDate": "14-Aug-2025", "verifiedRC": True, "verifiedOps": False, "aiStatus": "yellow", "remark": "Pending portal verification", "missing": False},
                    {"srNo": 5, "name": "GMDSS Radio Operator Certificate IV/2", "docNo": "GMDSS-NGA-2021", "type": "IV/2", "issueDate": "10-Nov-2021", "expiryDate": "09-Nov-2026", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 6, "name": "Flag CDC I/10 (Marshall Islands)", "docNo": "", "type": "I/10", "issueDate": "", "expiryDate": "NA", "verifiedRC": False, "verifiedOps": False, "aiStatus": "red", "remark": "to be review by OPS", "missing": True},
                ],
            },
            {
                "title": "STCW Basic Courses",
                "items": [
                    {"srNo": 7, "name": "Security Training For Seafarers (STSDSD)", "docNo": "STSDSD-2021-A5743", "type": "STCW-Basic", "issueDate": "20-Apr-2021", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 8, "name": "Personal Safety and Social Responsibilities", "docNo": "PSSR-2021-A5743", "type": "STCW-Basic", "issueDate": "20-Apr-2021", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 9, "name": "PSSR Amendment 2026", "docNo": "", "type": "STCW-Basic", "issueDate": "", "expiryDate": "NA", "verifiedRC": False, "verifiedOps": False, "aiStatus": "red", "remark": "Will check", "missing": True},
                ],
            },
            {
                "title": "STCW Courses",
                "items": [
                    {"srNo": 10, "name": "ECDIS - Generic", "docNo": "ECDIS-GEN-2022-A5743", "type": "STCW", "issueDate": "15-Mar-2022", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 11, "name": "Advance Fire Fighting", "docNo": "AFF-2021-A5743", "type": "STCW", "issueDate": "08-Nov-2021", "expiryDate": "07-Nov-2026", "verifiedRC": True, "verifiedOps": False, "aiStatus": "yellow", "remark": "Portal check pending", "missing": False},
                    {"srNo": 12, "name": "Automatic Radar Plotting Aids", "docNo": "ARPA-2021-A5743", "type": "STCW", "issueDate": "12-Oct-2021", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 13, "name": "Radar Observer Simulator", "docNo": "", "type": "STCW", "issueDate": "", "expiryDate": "NA", "verifiedRC": False, "verifiedOps": False, "aiStatus": "red", "remark": "ARPA", "missing": True},
                    {"srNo": 14, "name": "Medical First Aid", "docNo": "MFA-2022-A5743", "type": "STCW", "issueDate": "25-Jul-2022", "expiryDate": "24-Jul-2027", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
            {
                "title": "Company Courses (Vessel Specific)",
                "items": [
                    {"srNo": 15, "name": "ECDIS - JRC (Type Specific)", "docNo": "JRC-2023-A5743", "type": "Vessel Specific", "issueDate": "05-Feb-2023", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": False, "aiStatus": "yellow", "remark": "Awaiting ops verification", "missing": False},
                    {"srNo": 16, "name": "Advance Training for Oil Tanker Cargo Operations", "docNo": "ATOT-2022-A5743", "type": "Vessel Specific", "issueDate": "15-Apr-2022", "expiryDate": "14-Apr-2027", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
            {
                "title": "Other Documents / Pre-joining Docs",
                "items": [
                    {"srNo": 17, "name": "Interview Sheet (FP01D)", "docNo": "FP01D-A5743-2026", "type": "Company", "issueDate": "05-Jul-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 18, "name": "Offer Letter (FP01A)", "docNo": "FP01A-A5743-2026", "type": "Company", "issueDate": "05-Jul-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 19, "name": "DCE Oil/Chemical (Basic) V/1-1-1", "docNo": "", "type": "STCW", "issueDate": "", "expiryDate": "NA", "verifiedRC": False, "verifiedOps": False, "aiStatus": "red", "remark": "Required for oil tanker - not submitted", "missing": True},
                ],
            },
            {
                "title": "Post Departure Documents",
                "items": [
                    {"srNo": 20, "name": "Seafarer's Employment Agreement", "docNo": "SEA-A5743-2026", "type": "Company", "issueDate": "", "expiryDate": "23-Jan-2027", "verifiedRC": False, "verifiedOps": False, "aiStatus": "red", "remark": "Pending signature", "missing": False},
                    {"srNo": 21, "name": "Terms of Employment for Seafarers (FP01C)", "docNo": "FP01C-A5743-2026", "type": "Company", "issueDate": "05-Jul-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
        ]
    },
    "c003": {
        "sections": [
            {
                "title": "Travel Documents",
                "items": [
                    {"srNo": 1, "name": "Passport", "docNo": "P7654321", "type": "Travel", "issueDate": "18-Jun-2020", "expiryDate": "17-Jun-2030", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 2, "name": "CDC (Continuous Discharge Certificate)", "docNo": "IND-CDC-A0806", "type": "Travel", "issueDate": "22-Feb-2019", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 3, "name": "Yellow Fever Certificate", "docNo": "YF2022-A0806", "type": "Medical", "issueDate": "14-Apr-2022", "expiryDate": "Unlimited", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
            {
                "title": "License (National & Flag)",
                "items": [
                    {"srNo": 4, "name": "Certificate of Competency (Chief Officer)", "docNo": "IND-COC-CO-2018", "type": "II/2", "issueDate": "08-Jan-2018", "expiryDate": "07-Jan-2028", "verifiedRC": True, "verifiedOps": False, "aiStatus": "yellow", "remark": "MMD portal verification pending", "missing": False},
                    {"srNo": 5, "name": "GMDSS Radio Operator Certificate IV/2", "docNo": "GMDSS-IND-2019", "type": "IV/2", "issueDate": "30-Oct-2019", "expiryDate": "29-Oct-2024", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 6, "name": "Flag CDC I/10 (Marshall Islands)", "docNo": "MI-CDC-CO-2022", "type": "I/10", "issueDate": "12-Aug-2022", "expiryDate": "11-Aug-2027", "verifiedRC": True, "verifiedOps": False, "aiStatus": "yellow", "remark": "Marshall Islands portal down, retrying", "missing": False},
                ],
            },
            {
                "title": "STCW Basic Courses",
                "items": [
                    {"srNo": 7, "name": "Security Training For Seafarers (STSDSD)", "docNo": "STSDSD-2020-A0806", "type": "STCW-Basic", "issueDate": "10-Feb-2020", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 8, "name": "Personal Safety and Social Responsibilities", "docNo": "PSSR-2020-A0806", "type": "STCW-Basic", "issueDate": "10-Feb-2020", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 9, "name": "PSSR Amendment 2026", "docNo": "PSSR26-2026-A0806", "type": "STCW-Basic", "issueDate": "20-Jan-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": False, "aiStatus": "yellow", "remark": "Awaiting DG Shipping portal response", "missing": False},
                ],
            },
            {
                "title": "STCW Courses",
                "items": [
                    {"srNo": 10, "name": "ECDIS - Generic", "docNo": "ECDIS-GEN-2020-A0806", "type": "STCW", "issueDate": "25-Sep-2020", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 11, "name": "Advance Fire Fighting", "docNo": "AFF-2019-A0806", "type": "STCW", "issueDate": "15-Jul-2019", "expiryDate": "14-Jul-2024", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 12, "name": "Radar Observer Simulator", "docNo": "RADAR-2021-A0806", "type": "STCW", "issueDate": "30-Nov-2021", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 13, "name": "Medical First Aid", "docNo": "MFA-2020-A0806", "type": "STCW", "issueDate": "22-Aug-2020", "expiryDate": "21-Aug-2025", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
            {
                "title": "Company Courses (Vessel Specific)",
                "items": [
                    {"srNo": 14, "name": "ECDIS - JRC (Type Specific)", "docNo": "JRC-2022-A0806", "type": "Vessel Specific", "issueDate": "20-Jan-2022", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 15, "name": "Advance Training for Oil Tanker Cargo Operations", "docNo": "ATOT-2021-A0806", "type": "Vessel Specific", "issueDate": "10-Sep-2021", "expiryDate": "09-Sep-2026", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
            {
                "title": "Other Documents / Pre-joining Docs",
                "items": [
                    {"srNo": 16, "name": "Interview Sheet (FP01D)", "docNo": "FP01D-A0806-2026", "type": "Company", "issueDate": "01-Jun-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 17, "name": "Offer Letter (FP01A)", "docNo": "FP01A-A0806-2026", "type": "Company", "issueDate": "01-Jun-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
            {
                "title": "Post Departure Documents",
                "items": [
                    {"srNo": 18, "name": "Seafarer's Employment Agreement", "docNo": "SEA-A0806-2026", "type": "Company", "issueDate": "10-Jun-2026", "expiryDate": "16-Jul-2026", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 19, "name": "Terms of Employment for Seafarers (FP01C)", "docNo": "FP01C-A0806-2026", "type": "Company", "issueDate": "01-Jun-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                    {"srNo": 20, "name": "Undertaking by Seafarer (FP02C)", "docNo": "FP02C-A0806-2026", "type": "Company", "issueDate": "01-Jun-2026", "expiryDate": "NA", "verifiedRC": True, "verifiedOps": True, "aiStatus": "green", "remark": "", "missing": False},
                ],
            },
        ]
    },
}

BASE_CONFIRMATION = {
    "c001": [
        {"srNo": 1, "description": "Air Ticket, Letter to Immigration, Okay to Board / Letter of Guarantee / Visas (as applicable)", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": "Received"},
        {"srNo": 2, "description": "Flag Documents / CRA", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": "Confirmed"},
        {"srNo": 3, "description": "Original Medical Report", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": ""},
        {"srNo": 4, "description": "Original PP and CDC (and any other original seafarer's document kept in office)", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": ""},
        {"srNo": 5, "description": "Seafarer's Employment Agreement", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": "Signed"},
        {"srNo": 6, "description": "Seafarer's Declarations", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": ""},
        {"srNo": 7, "description": "Terms of Employment for Seafarers", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": "Acknowledged"},
        {"srNo": 8, "description": "Working Gear", "verifyOps": True, "officeRemark": "Issued on 24-Jul-2026", "verifyCrew": True, "seafarerRemark": "Received"},
    ],
    "c002": [
        {"srNo": 1, "description": "Air Ticket, Letter to Immigration, Okay to Board / Letter of Guarantee / Visas (as applicable)", "verifyOps": True, "officeRemark": "", "verifyCrew": False, "seafarerRemark": ""},
        {"srNo": 2, "description": "Flag Documents / CRA", "verifyOps": False, "officeRemark": "Flag CDC pending - see Pre-Departure remarks", "verifyCrew": False, "seafarerRemark": ""},
        {"srNo": 3, "description": "Original Medical Report", "verifyOps": True, "officeRemark": "", "verifyCrew": False, "seafarerRemark": ""},
        {"srNo": 4, "description": "Original PP and CDC (and any other original seafarer's document kept in office)", "verifyOps": True, "officeRemark": "", "verifyCrew": False, "seafarerRemark": ""},
        {"srNo": 5, "description": "Seafarer's Employment Agreement", "verifyOps": False, "officeRemark": "Pending signature", "verifyCrew": False, "seafarerRemark": ""},
        {"srNo": 6, "description": "Seafarer's Declarations", "verifyOps": True, "officeRemark": "", "verifyCrew": False, "seafarerRemark": ""},
        {"srNo": 7, "description": "Terms of Employment for Seafarers", "verifyOps": True, "officeRemark": "", "verifyCrew": False, "seafarerRemark": ""},
        {"srNo": 8, "description": "Working Gear", "verifyOps": False, "officeRemark": "To be collected at port", "verifyCrew": False, "seafarerRemark": ""},
    ],
    "c003": [
        {"srNo": 1, "description": "Air Ticket, Letter to Immigration, Okay to Board / Letter of Guarantee / Visas (as applicable)", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": "Received"},
        {"srNo": 2, "description": "Flag Documents / CRA", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": ""},
        {"srNo": 3, "description": "Original Medical Report", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": "Confirmed"},
        {"srNo": 4, "description": "Original PP and CDC (and any other original seafarer's document kept in office)", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": ""},
        {"srNo": 5, "description": "Seafarer's Employment Agreement", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": "Signed"},
        {"srNo": 6, "description": "Seafarer's Declarations", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": ""},
        {"srNo": 7, "description": "Terms of Employment for Seafarers", "verifyOps": True, "officeRemark": "", "verifyCrew": True, "seafarerRemark": "Acknowledged"},
        {"srNo": 8, "description": "Working Gear", "verifyOps": True, "officeRemark": "Issued", "verifyCrew": True, "seafarerRemark": "Received"},
    ],
}

VESSEL_MATRIX = {
    "MST": [
        "Passport",
        "CDC (Continuous Discharge Certificate)",
        "Yellow Fever Certificate",
        "Certificate of Competency (Master)",
        "GMDSS Radio Operator Certificate IV/2",
        "Flag CDC I/10 (Marshall Islands)",
        "Security Training For Seafarers (STSDSD)",
        "Personal Safety and Social Responsibilities",
        "PSSR Amendment 2026",
        "ECDIS - Generic",
        "Advance Fire Fighting",
        "Radar Observer Simulator",
        "Medical First Aid",
        "ECDIS - JRC (Type Specific)",
        "Advance Training for Oil Tanker Cargo Operations",
        "Interview Sheet (FP01D)",
        "Offer Letter (FP01A)",
        "Briefing Prior Crew Travel (FP06F)",
        "Seafarer's Employment Agreement",
        "Terms of Employment for Seafarers (FP01C)",
        "Undertaking by Seafarer (FP02C)",
    ],
    "A3O": [
        "Passport",
        "CDC (Continuous Discharge Certificate)",
        "Yellow Fever Certificate",
        "Officer in Charge of Navigational Watch II/1",
        "GMDSS Radio Operator Certificate IV/2",
        "Flag CDC I/10 (Marshall Islands)",
        "Security Training For Seafarers (STSDSD)",
        "Personal Safety and Social Responsibilities",
        "PSSR Amendment 2026",
        "ECDIS - Generic",
        "Advance Fire Fighting",
        "Automatic Radar Plotting Aids",
        "Radar Observer Simulator",
        "Medical First Aid",
        "ECDIS - JRC (Type Specific)",
        "Advance Training for Oil Tanker Cargo Operations",
        "Interview Sheet (FP01D)",
        "Offer Letter (FP01A)",
        "DCE Oil/Chemical (Basic) V/1-1-1",
        "Seafarer's Employment Agreement",
        "Terms of Employment for Seafarers (FP01C)",
    ],
    "CO": [
        "Passport",
        "CDC (Continuous Discharge Certificate)",
        "Yellow Fever Certificate",
        "Certificate of Competency (Chief Officer)",
        "GMDSS Radio Operator Certificate IV/2",
        "Flag CDC I/10 (Marshall Islands)",
        "Security Training For Seafarers (STSDSD)",
        "Personal Safety and Social Responsibilities",
        "PSSR Amendment 2026",
        "ECDIS - Generic",
        "Advance Fire Fighting",
        "Radar Observer Simulator",
        "Medical First Aid",
        "ECDIS - JRC (Type Specific)",
        "Advance Training for Oil Tanker Cargo Operations",
        "Interview Sheet (FP01D)",
        "Offer Letter (FP01A)",
        "Seafarer's Employment Agreement",
        "Terms of Employment for Seafarers (FP01C)",
        "Undertaking by Seafarer (FP02C)",
    ],
}


class PortalVerifyRequest(BaseModel):
    docName: str
    docNo: str
    issueAuthority: Optional[str] = None


class RemarkRequest(BaseModel):
    remark: str
    actor: str = "RC Officer"


class OverrideRequest(BaseModel):
    status: Literal["green", "yellow", "red"]
    reason: str
    actor: str = "RC Officer"


class SendApprovalRequest(BaseModel):
    sentBy: str = "RC Officer"


class SelfServiceItemSubmission(BaseModel):
    srNo: int
    verifyCrew: bool
    seafarerRemark: str


class SelfServiceSubmitRequest(BaseModel):
    seafarerName: str
    items: List[SelfServiceItemSubmission]


class LoginRequest(BaseModel):
    username: str
    password: str


class ConfirmationUpdateRequest(BaseModel):
    verifyOps: bool
    officeRemark: str = ""


class ManualVerificationRequest(BaseModel):
    verified: bool = True
    remark: str = ""


STATE: Dict[str, Any] = {}
DEFAULT_STATE: Dict[str, Any] = {
    "vessel": deepcopy(BASE_VESSEL),
    "crew": deepcopy(BASE_CREW),
    "documents": deepcopy(BASE_DOCUMENTS),
    "confirmation": deepcopy(BASE_CONFIRMATION),
    "audit_logs": {crew["id"]: [] for crew in BASE_CREW},
    "self_service_links": {},
    "latest_link_by_crew": {},
    "learning_feedback": {crew["id"]: [] for crew in BASE_CREW},
}


def persist_state() -> None:
    save_state(STATE)


def _unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


def require_user(roles: Optional[set[str]] = None):
    def dependency(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(TOKEN_SECURITY),
    ) -> Dict[str, Any]:
        if not credentials or credentials.scheme.lower() != "bearer":
            raise _unauthorized()

        user = get_user_by_token(credentials.credentials)
        if not user:
            raise _unauthorized("Session expired or invalid")
        if roles and user["role"] not in roles:
            raise HTTPException(status_code=403, detail="You do not have access to this action")
        return user

    return dependency


def _portal_configuration() -> Dict[str, Any]:
    provider = os.environ.get("PORTAL_PROVIDER", "mock")
    base_url = os.environ.get("PORTAL_API_BASE_URL", "").rstrip("/")
    return {
        "provider": provider,
        "configured": bool(base_url),
        "baseUrl": base_url,
        "storagePath": data_dir(),
        "databasePath": db_path(),
    }


def reset_demo_state() -> None:
    STATE.clear()
    seeded_state = deepcopy(DEFAULT_STATE)
    STATE.update(seeded_state)

    for crew in STATE["crew"]:
        _recalculate_crew(crew["id"])
        _append_audit(
            crew["id"],
            actor="System",
            action="seeded",
            target="Checklist",
            message=f"Demo state prepared for {crew['name']} on {REFERENCE_DATE}.",
        )
    reset_state(STATE)


def _find_crew_member(crew_id: str) -> Dict[str, Any]:
    crew = next((item for item in STATE["crew"] if item["id"] == crew_id), None)
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")
    return crew


def _find_document(crew_id: str, sr_no: int) -> Dict[str, Any]:
    sections = STATE["documents"].get(crew_id, {}).get("sections", [])
    for section in sections:
        for item in section.get("items", []):
            if item["srNo"] == sr_no:
                return item
    raise HTTPException(status_code=404, detail="Document not found")


def _find_document_by_name(crew_id: str, doc_name: str) -> Dict[str, Any]:
    sections = STATE["documents"].get(crew_id, {}).get("sections", [])
    for section in sections:
        for item in section.get("items", []):
            if item["name"] == doc_name:
                return item
    raise HTTPException(status_code=404, detail="Document not found")


def _find_confirmation_item(crew_id: str, sr_no: int) -> Dict[str, Any]:
    for item in STATE["confirmation"].get(crew_id, []):
        if item["srNo"] == sr_no:
            return item
    raise HTTPException(status_code=404, detail="Confirmation item not found")


def _append_audit(crew_id: str, actor: str, action: str, target: str, message: str) -> None:
    STATE["audit_logs"][crew_id].insert(
        0,
        {
            "id": secrets.token_hex(6),
            "timestamp": now_stamp(),
            "actor": actor,
            "action": action,
            "target": target,
            "message": message,
        },
    )


def _required_documents_for(crew_id: str) -> List[str]:
    crew = _find_crew_member(crew_id)
    return VESSEL_MATRIX.get(crew["rank"], [])


def _hydrate_document_item(crew_id: str, item: Dict[str, Any], required_docs: List[str]) -> None:
    if not item.get("missing") and (not item.get("attachmentUrl") or str(item.get("attachmentUrl", "")).startswith("/files/")):
        item["attachmentUrl"] = f"/api/crew/{crew_id}/documents/{item['srNo']}/placeholder"
    elif item.get("missing"):
        item.setdefault("attachmentUrl", "")
    item.setdefault("attachmentName", f"{item['name']}.pdf" if not item.get("missing") else "")
    item.setdefault("portalVerified", item.get("verifiedOps", False))
    item.setdefault("overrideStatus", "")
    item.setdefault("overrideReason", "")
    item.setdefault("extractionConfidence", 0.98 if item.get("verifiedRC") else 0.72)
    item["required"] = item["name"] in required_docs


def _recalculate_crew(crew_id: str) -> None:
    required_docs = _required_documents_for(crew_id)
    docs = STATE["documents"][crew_id]
    all_items = [item for section in docs["sections"] for item in section["items"]]

    valid = 0
    pending = 0
    missing = 0
    expired = 0

    for item in all_items:
        _hydrate_document_item(crew_id, item, required_docs)
        status = item.get("overrideStatus") or item.get("aiStatus", "grey")
        item["aiStatus"] = status

        if item["required"] and item.get("missing"):
            missing += 1
        elif item["required"] and status == "yellow":
            pending += 1
        elif item["required"] and status == "red" and item.get("expired", False):
            expired += 1
        elif item["required"] and status == "green":
            valid += 1

    docs["summary"] = {
        "valid": valid,
        "pendingVerification": pending,
        "missing": missing,
        "expired": expired,
    }

    crew = _find_crew_member(crew_id)
    if missing > 0 or expired > 0:
        crew["aiStatus"] = "red"
        crew["complianceIssue"] = True
    elif pending > 0:
        crew["aiStatus"] = "yellow"
        crew["complianceIssue"] = False
    else:
        crew["aiStatus"] = "green"
        crew["complianceIssue"] = False


async def _build_portal_response(
    crew_id: str,
    doc_name: str,
    doc_no: str = "",
    issue_authority: Optional[str] = None,
) -> Dict[str, Any]:
    portal_configuration = _portal_configuration()
    if portal_configuration["configured"]:
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{portal_configuration['baseUrl']}/verify",
                    headers={
                        "Authorization": f"Bearer {os.environ.get('PORTAL_API_TOKEN', '')}".strip(),
                    },
                    json={
                        "crewId": crew_id,
                        "documentName": doc_name,
                        "documentNumber": doc_no,
                        "issueAuthority": issue_authority,
                    },
                )
            response.raise_for_status()
            payload = response.json()
            return {
                "docName": doc_name,
                "verified": bool(payload.get("verified")),
                "message": payload.get("message") or f"{doc_name} verified via {portal_configuration['provider']}.",
                "portal": payload.get("portal") or portal_configuration["provider"],
            }
        except Exception as exc:
            return {
                "docName": doc_name,
                "verified": False,
                "message": f"{portal_configuration['provider']} integration failed: {exc}",
                "portal": portal_configuration["provider"],
            }

    if crew_id == "c002" and "Flag CDC" in doc_name:
        return {
            "docName": doc_name,
            "verified": False,
            "message": "Not found on DG portal - document not registered.",
            "portal": "DG Shipping India",
        }

    return {
        "docName": doc_name,
        "verified": True,
        "message": f"Valid as per DG records - {doc_name} is in order.",
        "portal": "DG Shipping India",
    }


def _apply_portal_result(crew_id: str, item: Dict[str, Any], result: Dict[str, Any]) -> None:
    item["portalVerified"] = result["verified"]
    item["verifiedOps"] = result["verified"]
    if result["verified"] and not item.get("missing"):
        item["aiStatus"] = "green"
        item["overrideStatus"] = ""
        item["overrideReason"] = ""
    _recalculate_crew(crew_id)


def _build_extraction_report(crew_id: str) -> Dict[str, Any]:
    crew = _find_crew_member(crew_id)
    docs = STATE["documents"][crew_id]
    required_docs = _required_documents_for(crew_id)

    extracted = []
    for section in docs["sections"]:
        for item in section["items"]:
            extracted.append(
                {
                    "srNo": item["srNo"],
                    "name": item["name"],
                    "section": section["title"],
                    "confidence": item.get("extractionConfidence", 0.8),
                    "matchedToMatrix": item["name"] in required_docs,
                    "sourceFile": f"{crew['empNo']}_{item['srNo']:02d}.pdf" if not item.get("missing") else "missing",
                    "status": item["aiStatus"],
                }
            )

    return {
        "crewId": crew_id,
        "crewName": crew["name"],
        "rank": crew["rank"],
        "requiredDocuments": required_docs,
        "extractedDocuments": extracted,
    }


def _get_fallback_narrative(crew_id: str) -> str:
    crew = _find_crew_member(crew_id)
    docs = STATE["documents"][crew_id]
    summary = docs["summary"]
    missing_items = [
        item["name"]
        for section in docs["sections"]
        for item in section["items"]
        if item.get("missing")
    ]
    pending_items = [
        item["name"]
        for section in docs["sections"]
        for item in section["items"]
        if item.get("aiStatus") == "yellow" and not item.get("missing")
    ]

    if crew["aiStatus"] == "green":
        return (
            f"All {summary['valid']} required documents for {crew['name']} are valid, verified, and compliant "
            "with vessel and rank requirements. No document gaps remain before sign-on. Risk level: Low."
        )
    if crew["aiStatus"] == "red":
        return (
            f"Critical compliance issues remain for {crew['name']}. Missing items include "
            f"{', '.join(missing_items[:3])}{'...' if len(missing_items) > 3 else ''}. "
            "RC and Ops should not clear sign-on until these gaps are resolved. Risk level: High."
        )
    return (
        f"All required documents are attached for {crew['name']}, but {summary['pendingVerification']} item(s) "
        f"still require portal verification, including {', '.join(pending_items[:3])}. "
        "Crew may proceed only with controlled review from Ops. Risk level: Medium."
    )


async def _generate_ai_narrative(crew_id: str) -> str:
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not anthropic_key:
        return _get_fallback_narrative(crew_id)

    crew = _find_crew_member(crew_id)
    docs = STATE["documents"][crew_id]
    summary = docs["summary"]
    required_docs = _required_documents_for(crew_id)
    missing_items = [
        item["name"]
        for section in docs["sections"]
        for item in section["items"]
        if item.get("missing")
    ]
    pending_items = [
        item["name"]
        for section in docs["sections"]
        for item in section["items"]
        if item.get("aiStatus") == "yellow" and not item.get("missing")
    ]

    prompt = f"""You are a maritime compliance officer helping review a pre-joining checklist.
Seafarer: {crew['name']}
Rank: {crew['rank']}
Vessel: {BASE_VESSEL['name']} ({BASE_VESSEL['type']})
Flag: {BASE_VESSEL['flag']}
Required documents count: {len(required_docs)}
Valid and verified: {summary['valid']}
Pending verification: {summary['pendingVerification']}
Missing: {summary['missing']}
Expired: {summary['expired']}
Missing items: {', '.join(missing_items) if missing_items else 'None'}
Pending items: {', '.join(pending_items) if pending_items else 'None'}

Provide a concise 3-4 sentence assessment with:
1. overall compliance posture
2. specific next actions for RC or Ops
3. sign-on risk level
"""

    try:
        client = anthropic.Anthropic(api_key=anthropic_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception:
        return _get_fallback_narrative(crew_id)


def _build_ai_check_payload(crew_id: str, ai_narrative: str) -> Dict[str, Any]:
    crew = _find_crew_member(crew_id)
    docs = STATE["documents"][crew_id]
    extraction = _build_extraction_report(crew_id)

    return {
        "crewId": crew_id,
        "name": crew["name"],
        "rank": crew["rank"],
        "vessel": f"{BASE_VESSEL['name']} ({BASE_VESSEL['type']})",
        "flag": BASE_VESSEL["flag"],
        "summary": docs["summary"],
        "missingItems": [item["name"] for section in docs["sections"] for item in section["items"] if item.get("missing")],
        "pendingItems": [item["name"] for section in docs["sections"] for item in section["items"] if item.get("aiStatus") == "yellow" and not item.get("missing")],
        "expiredItems": [item["name"] for section in docs["sections"] for item in section["items"] if item.get("expired")],
        "aiNarrative": ai_narrative,
        "overallStatus": crew["aiStatus"],
        "matrixDocuments": extraction["requiredDocuments"],
        "extractedDocuments": extraction["extractedDocuments"],
    }


def _get_latest_link(crew_id: str) -> Optional[Dict[str, Any]]:
    token = STATE["latest_link_by_crew"].get(crew_id)
    if not token:
        return None
    return STATE["self_service_links"].get(token)


def _build_placeholder_attachment_pdf(crew_id: str, sr_no: int) -> bytes:
    crew = _find_crew_member(crew_id)
    item = _find_document(crew_id, sr_no)
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, 800, "Crewlink Checklist Attachment Placeholder")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, 770, f"Seafarer: {crew['name']} ({crew['rank']})")
    pdf.drawString(40, 752, f"Document: {item['name']}")
    pdf.drawString(40, 734, f"Document No: {item.get('docNo') or '-'}")
    pdf.drawString(40, 716, f"Issue Date: {item.get('issueDate') or '-'}")
    pdf.drawString(40, 698, f"Expiry Date: {item.get('expiryDate') or '-'}")
    pdf.drawString(40, 680, f"Generated: {now_stamp()}")
    pdf.drawString(40, 640, "Upload a real document to replace this placeholder in the production workflow.")
    pdf.save()
    return buffer.getvalue()


def _resolve_public_base_url(request: Optional[Request] = None) -> str:
    explicit_url = os.environ.get("PUBLIC_APP_URL") or os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    if explicit_url:
        normalized = explicit_url.rstrip("/")
        if normalized.startswith("http://") or normalized.startswith("https://"):
            return normalized
        return f"https://{normalized}"

    if request is not None:
        forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
        if forwarded_host:
            return f"{forwarded_proto}://{forwarded_host}".rstrip("/")
        return str(request.base_url).rstrip("/")

    return "http://localhost:8000"


def _serialize_self_service_packet(packet: Optional[Dict[str, Any]], request: Optional[Request] = None) -> Optional[Dict[str, Any]]:
    if packet is None:
        return None

    payload = deepcopy(packet)
    payload["url"] = f"{_resolve_public_base_url(request)}/approval/{packet['token']}"
    return payload


def _create_self_service_link(crew_id: str, sent_by: str) -> Dict[str, Any]:
    crew = _find_crew_member(crew_id)
    token = secrets.token_urlsafe(10)
    packet = {
        "token": token,
        "crewId": crew_id,
        "crewName": crew["name"],
        "rank": crew["rank"],
        "status": "sent",
        "sentAt": now_stamp(),
        "sentBy": sent_by,
        "items": deepcopy(STATE["confirmation"][crew_id]),
    }
    STATE["self_service_links"][token] = packet
    STATE["latest_link_by_crew"][crew_id] = token
    _append_audit(
        crew_id,
        actor=sent_by,
        action="sent_to_seafarer",
        target="Seafarer Confirmation",
        message=f"Shared self-service approval link for {crew['name']}.",
    )
    return packet


def _build_export_pdf(crew_id: str) -> bytes:
    crew = _find_crew_member(crew_id)
    docs = STATE["documents"][crew_id]

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, f"Crewlink AI-ACE Checklist - {crew['name']}")
    y -= 22

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Rank: {crew['rank']}    Emp No: {crew['empNo']}    Vessel: {BASE_VESSEL['name']}")
    y -= 16
    pdf.drawString(40, y, f"Generated: {now_stamp()}")
    y -= 20

    summary = docs["summary"]
    pdf.setFillColor(colors.HexColor("#1a2a4a"))
    pdf.rect(40, y - 4, width - 80, 20, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(48, y + 2, f"Summary  Valid: {summary['valid']}   Pending: {summary['pendingVerification']}   Missing: {summary['missing']}   Expired: {summary['expired']}")
    y -= 26

    for section in docs["sections"]:
        if y < 80:
            pdf.showPage()
            y = height - 40
        pdf.setFillColor(colors.HexColor("#e8eef5"))
        pdf.rect(40, y - 2, width - 80, 16, fill=1, stroke=0)
        pdf.setFillColor(colors.HexColor("#1a2a4a"))
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(44, y + 2, section["title"])
        y -= 18

        for item in section["items"]:
            if y < 60:
                pdf.showPage()
                y = height - 40
            status = item["aiStatus"].upper()
            text = f"{item['srNo']:>2}. {item['name']} | {item['docNo'] or '-'} | {status} | Remark: {item['remark'] or '-'}"
            pdf.setFillColor(colors.black if not item.get("missing") else colors.HexColor("#e67e22"))
            pdf.setFont("Helvetica", 8.5)
            max_width = width - 90
            while text:
                cut = len(text)
                while cut > 1 and stringWidth(text[:cut], "Helvetica", 8.5) > max_width:
                    cut -= 1
                line = text[:cut]
                pdf.drawString(48, y, line)
                text = text[cut:].lstrip()
                y -= 11

    pdf.save()
    return buffer.getvalue()


@app.post("/api/auth/login")
def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_session(user["id"])
    return {"token": token, "user": {**user, "token": token}}


@app.get("/api/auth/me")
def get_current_user_profile(current_user: Dict[str, Any] = Depends(require_user())):
    return {key: current_user[key] for key in ("id", "username", "fullName", "role")}


@app.post("/api/auth/logout")
def logout(current_user: Dict[str, Any] = Depends(require_user())):
    delete_session(current_user["token"])
    return {"ok": True}


@app.get("/api/integrations/status")
def get_integrations_status(current_user: Dict[str, Any] = Depends(require_user())):
    portal_configuration = _portal_configuration()
    return {
        "portal": {
            "provider": portal_configuration["provider"],
            "configured": portal_configuration["configured"],
            "mode": "external" if portal_configuration["configured"] else "mock",
        },
        "storage": {
            "databasePath": portal_configuration["databasePath"],
            "uploadsPath": os.path.join(data_dir(), "uploads"),
        },
        "user": current_user["role"],
    }


@app.get("/api/files/{file_id}")
def serve_uploaded_file(file_id: str, current_user: Dict[str, Any] = Depends(require_user())):
    attachment = get_attachment(file_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(
        attachment["absolutePath"],
        media_type=attachment["contentType"],
        filename=attachment["originalName"],
    )


@app.get("/api/crew/{crew_id}/documents/{sr_no}/placeholder")
def serve_placeholder_attachment(crew_id: str, sr_no: int, current_user: Dict[str, Any] = Depends(require_user())):
    _find_crew_member(crew_id)
    payload = _build_placeholder_attachment_pdf(crew_id, sr_no)
    filename = f"{crew_id}-{sr_no}-placeholder.pdf"
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@app.get("/api/vessel")
def get_vessel(current_user: Dict[str, Any] = Depends(require_user())):
    return STATE["vessel"]


@app.get("/api/crew")
def get_crew(current_user: Dict[str, Any] = Depends(require_user())):
    return STATE["crew"]


@app.get("/api/crew/{crew_id}")
def get_crew_member(crew_id: str, current_user: Dict[str, Any] = Depends(require_user())):
    return _find_crew_member(crew_id)


@app.get("/api/crew/{crew_id}/documents")
def get_crew_documents(crew_id: str, current_user: Dict[str, Any] = Depends(require_user())):
    _find_crew_member(crew_id)
    _recalculate_crew(crew_id)
    return STATE["documents"][crew_id]


@app.get("/api/crew/{crew_id}/confirmation")
def get_confirmation(crew_id: str, current_user: Dict[str, Any] = Depends(require_user())):
    _find_crew_member(crew_id)
    return STATE["confirmation"][crew_id]


@app.get("/api/crew/{crew_id}/audit-log")
def get_audit_log(crew_id: str, current_user: Dict[str, Any] = Depends(require_user())):
    _find_crew_member(crew_id)
    return STATE["audit_logs"][crew_id]


@app.get("/api/crew/{crew_id}/matrix")
def get_matrix(crew_id: str, current_user: Dict[str, Any] = Depends(require_user())):
    crew = _find_crew_member(crew_id)
    return {
        "crewId": crew_id,
        "vessel": BASE_VESSEL["name"],
        "rank": crew["rank"],
        "requiredDocuments": _required_documents_for(crew_id),
    }


@app.get("/api/crew/{crew_id}/extraction")
def get_extraction(crew_id: str, current_user: Dict[str, Any] = Depends(require_user())):
    _find_crew_member(crew_id)
    return _build_extraction_report(crew_id)


@app.get("/api/crew/{crew_id}/self-service/latest")
def get_latest_self_service_link(
    crew_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_user()),
):
    _find_crew_member(crew_id)
    return _serialize_self_service_packet(_get_latest_link(crew_id), request)


@app.get("/api/crew/{crew_id}/export-checklist")
def export_checklist(crew_id: str, current_user: Dict[str, Any] = Depends(require_user())):
    _find_crew_member(crew_id)
    pdf_bytes = _build_export_pdf(crew_id)
    filename = f"{crew_id}-prejoining-checklist.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@app.post("/api/crew/{crew_id}/documents/{sr_no}/remark")
def save_remark(
    crew_id: str,
    sr_no: int,
    request: RemarkRequest,
    current_user: Dict[str, Any] = Depends(require_user({ROLE_RC, ROLE_OPS, ROLE_ADMIN})),
):
    item = _find_document(crew_id, sr_no)
    item["remark"] = request.remark
    _append_audit(
        crew_id,
        actor=current_user["fullName"],
        action="remark_updated",
        target=item["name"],
        message=f"Updated remark to '{request.remark}'.",
    )
    persist_state()
    return {"ok": True, "item": item}


@app.post("/api/crew/{crew_id}/documents/{sr_no}/override")
def override_document_status(
    crew_id: str,
    sr_no: int,
    request: OverrideRequest,
    current_user: Dict[str, Any] = Depends(require_user({ROLE_OPS, ROLE_ADMIN})),
):
    item = _find_document(crew_id, sr_no)
    item["overrideStatus"] = request.status
    item["aiStatus"] = request.status
    item["overrideReason"] = request.reason
    if request.status == "green":
        item["missing"] = False
        item["verifiedOps"] = True
        item["portalVerified"] = True
    elif request.status == "yellow":
        item["missing"] = False
        item["verifiedOps"] = False
        item["portalVerified"] = False
    else:
        item["missing"] = True
        item["verifiedOps"] = False
        item["portalVerified"] = False
    _recalculate_crew(crew_id)
    STATE["learning_feedback"][crew_id].append(
        {
            "timestamp": now_stamp(),
            "document": item["name"],
            "status": request.status,
            "reason": request.reason,
        }
    )
    _append_audit(
        crew_id,
        actor=current_user["fullName"],
        action="override",
        target=item["name"],
        message=f"Overrode AI status to {request.status.upper()} with reason: {request.reason}",
    )
    persist_state()
    return {"ok": True, "item": item, "summary": STATE["documents"][crew_id]["summary"]}


@app.post("/api/crew/{crew_id}/documents/{sr_no}/attachment")
async def upload_document_attachment(
    crew_id: str,
    sr_no: int,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(require_user({ROLE_RC, ROLE_OPS, ROLE_ADMIN})),
):
    _find_crew_member(crew_id)
    item = _find_document(crew_id, sr_no)
    content = await file.read()
    attachment = save_attachment(
        crew_id=crew_id,
        sr_no=sr_no,
        original_name=file.filename or f"{item['name']}.pdf",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        uploaded_by=current_user["fullName"],
    )
    item["attachmentUrl"] = f"/api/files/{attachment['fileId']}"
    item["attachmentName"] = attachment["originalName"]
    _append_audit(
        crew_id,
        actor=current_user["fullName"],
        action="attachment_uploaded",
        target=item["name"],
        message=f"Uploaded attachment {attachment['originalName']}.",
    )
    persist_state()
    return {"ok": True, "item": item}


@app.post("/api/crew/{crew_id}/confirmation/{sr_no}")
def update_confirmation_item(
    crew_id: str,
    sr_no: int,
    request: ConfirmationUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_user({ROLE_OPS, ROLE_ADMIN})),
):
    item = _find_confirmation_item(crew_id, sr_no)
    item["verifyOps"] = request.verifyOps
    item["officeRemark"] = request.officeRemark
    _append_audit(
        crew_id,
        actor=current_user["fullName"],
        action="departure_ops_updated",
        target=item["description"],
        message=f"Updated Ops confirmation to {'verified' if request.verifyOps else 'pending'} with remark: {request.officeRemark or 'No remark'}",
    )
    persist_state()
    return {"ok": True, "item": item}


@app.post("/api/crew/{crew_id}/verify-portal")
async def verify_portal(
    crew_id: str,
    request: PortalVerifyRequest,
    current_user: Dict[str, Any] = Depends(require_user({ROLE_OPS, ROLE_ADMIN, ROLE_RC})),
):
    _find_crew_member(crew_id)
    item = _find_document_by_name(crew_id, request.docName)
    await asyncio.sleep(0.8)
    result = await _build_portal_response(crew_id, request.docName, request.docNo, request.issueAuthority)
    _apply_portal_result(crew_id, item, result)
    _append_audit(
        crew_id,
        actor=current_user["fullName"],
        action="portal_verification",
        target=request.docName,
        message=result["message"],
    )
    persist_state()
    return result


@app.post("/api/crew/{crew_id}/verify-portal-batch")
async def verify_portal_batch(
    crew_id: str,
    current_user: Dict[str, Any] = Depends(require_user({ROLE_OPS, ROLE_ADMIN, ROLE_RC})),
):
    _find_crew_member(crew_id)
    await asyncio.sleep(1.0)
    items_to_verify = [
        item
        for section in STATE["documents"][crew_id]["sections"]
        for item in section["items"]
        if item.get("aiStatus") == "yellow" and not item.get("missing")
    ]

    results = []
    verified_count = 0
    failed_count = 0

    for item in items_to_verify:
        result = await _build_portal_response(crew_id, item["name"], item.get("docNo", ""))
        _apply_portal_result(crew_id, item, result)
        if result["verified"]:
            verified_count += 1
        else:
            failed_count += 1
        results.append(result)

    _append_audit(
        crew_id,
        actor=current_user["fullName"],
        action="batch_verification",
        target="Pending documents",
        message=f"Batch verification completed: {verified_count} verified, {failed_count} failed.",
    )
    persist_state()

    return {
        "crewId": crew_id,
        "verifiedCount": verified_count,
        "failedCount": failed_count,
        "results": results,
        "summary": STATE["documents"][crew_id]["summary"],
    }


@app.post("/api/crew/{crew_id}/self-service/send")
def send_to_seafarer(
    crew_id: str,
    request: SendApprovalRequest,
    http_request: Request,
    current_user: Dict[str, Any] = Depends(require_user({ROLE_RC, ROLE_ADMIN})),
):
    _find_crew_member(crew_id)
    packet = _create_self_service_link(crew_id, current_user["fullName"])
    persist_state()
    return _serialize_self_service_packet(packet, http_request)


@app.get("/api/self-service/{token}")
def get_self_service_packet(token: str, request: Request):
    packet = STATE["self_service_links"].get(token)
    if not packet:
        raise HTTPException(status_code=404, detail="Approval link not found")
    return _serialize_self_service_packet(packet, request)


@app.post("/api/self-service/{token}/submit")
def submit_self_service_packet(token: str, request: SelfServiceSubmitRequest):
    packet = STATE["self_service_links"].get(token)
    if not packet:
        raise HTTPException(status_code=404, detail="Approval link not found")

    crew_id = packet["crewId"]
    items_by_sr_no = {item["srNo"]: item for item in STATE["confirmation"][crew_id]}

    for submission in request.items:
        item = items_by_sr_no.get(submission.srNo)
        if not item:
            continue
        item["verifyCrew"] = submission.verifyCrew
        item["seafarerRemark"] = submission.seafarerRemark

    packet["status"] = "submitted"
    packet["submittedAt"] = now_stamp()
    packet["submittedBy"] = request.seafarerName
    packet["items"] = deepcopy(STATE["confirmation"][crew_id])

    _append_audit(
        crew_id,
        actor=request.seafarerName,
        action="self_service_submitted",
        target="Seafarer Confirmation",
        message="Seafarer completed the confirmation checklist.",
    )
    persist_state()
    return _serialize_self_service_packet(packet)


@app.post("/api/ai/check/{crew_id}")
async def run_ai_check(
    crew_id: str,
    current_user: Dict[str, Any] = Depends(require_user({ROLE_RC, ROLE_OPS, ROLE_ADMIN})),
):
    _find_crew_member(crew_id)
    _recalculate_crew(crew_id)
    narrative = await _generate_ai_narrative(crew_id)
    _append_audit(
        crew_id,
        actor=current_user["fullName"],
        action="analysis",
        target="Checklist",
        message="Ran AI compliance analysis against the vessel and rank matrix.",
    )
    persist_state()
    return _build_ai_check_payload(crew_id, narrative)


@app.post("/api/ai/check-batch")
async def run_ai_check_batch(
    payload: Dict[str, List[str]],
    current_user: Dict[str, Any] = Depends(require_user({ROLE_RC, ROLE_OPS, ROLE_ADMIN})),
):
    crew_ids = payload.get("crewIds", [])
    results = []
    for crew_id in crew_ids:
        if any(item["id"] == crew_id for item in STATE["crew"]):
            results.append(await run_ai_check(crew_id, current_user))
    return {"results": results}


@app.get("/api/crew/{crew_id}/report")
def get_crew_report(
    crew_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_user()),
):
    _find_crew_member(crew_id)
    return {
        "matrix": {
            "requiredDocuments": _required_documents_for(crew_id),
            "vessel": BASE_VESSEL["name"],
        },
        "extraction": _build_extraction_report(crew_id),
        "auditLog": STATE["audit_logs"][crew_id][:10],
        "latestSelfServiceLink": _serialize_self_service_packet(_get_latest_link(crew_id), request),
        "learningFeedbackCount": len(STATE["learning_feedback"][crew_id]),
    }


@app.post("/api/reset-demo-data")
def reset_demo(current_user: Dict[str, Any] = Depends(require_user({ROLE_ADMIN}))):
    reset_demo_state()
    return {"ok": True}

init_database(DEFAULT_STATE, SEED_USERS)
STATE.update(load_state())
if not STATE.get("audit_logs"):
    reset_demo_state()

static_dir = os.path.join(os.path.dirname(__file__), "static")
assets_dir = os.path.join(static_dir, "assets")

if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(static_dir, "index.html"))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
