from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from html import unescape
from io import BytesIO
from typing import Any, Dict, List, Literal, Optional
import asyncio
import os
import re
import secrets
from urllib.parse import urlsplit

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
        "dateOfBirth": "14-Feb-1986",
        "indosNo": "INDOS-A6227",
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
        "dateOfBirth": "02-Aug-1994",
        "indosNo": "",
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
        "dateOfBirth": "11-Nov-1988",
        "indosNo": "INDOS-A0806",
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

DEFAULT_PORTAL_LINKS = {
    "uk_mca_coc": "https://coccec.mcga.gov.uk/",
    "dg_shipping_home": "https://www.dgshipping.gov.in/",
    "dg_shipping_cdc": "http://220.156.189.33/IndosApplication/Indos/CDCChecker.jsp",
    "dg_shipping_coc": "http://220.156.189.33/esamudraUI/jsp/examination/checker/COCSearch.jsp?hidProcessId=COC",
    "dg_shipping_indos": "http://220.156.189.33/esamudraUI/jsp/examination/checker/PP_IndosChecker.jsp",
    "imo_gisis_directory": "https://gisis.imo.org/Public/CP/Browse.aspx?List=CV9&Function=2%20IMO%20Web%20Accounts",
}

CREWLINK_CONFIRMATION_TEMPLATE = [
    {"srNo": 1, "description": "Air Ticket, Letter to Immigration, Okay to Board / Letter of Guarantee / Visas (as applicable)", "verifyOps": False, "officeRemark": "", "verifyCrew": False, "seafarerRemark": ""},
    {"srNo": 2, "description": "Flag Documents / CRA", "verifyOps": False, "officeRemark": "", "verifyCrew": False, "seafarerRemark": ""},
    {"srNo": 3, "description": "Original Medical Report", "verifyOps": False, "officeRemark": "", "verifyCrew": False, "seafarerRemark": ""},
    {"srNo": 4, "description": "Original PP and CDC (and any other original seafarer's document kept in office)", "verifyOps": False, "officeRemark": "", "verifyCrew": False, "seafarerRemark": ""},
    {"srNo": 5, "description": "Seafarer's Employment Agreement", "verifyOps": False, "officeRemark": "", "verifyCrew": False, "seafarerRemark": ""},
    {"srNo": 6, "description": "Seafarer's Declarations", "verifyOps": False, "officeRemark": "", "verifyCrew": False, "seafarerRemark": ""},
    {"srNo": 7, "description": "Terms of Employment for Seafarers", "verifyOps": False, "officeRemark": "", "verifyCrew": False, "seafarerRemark": ""},
    {"srNo": 8, "description": "Working Gear", "verifyOps": False, "officeRemark": "", "verifyCrew": False, "seafarerRemark": ""},
]

CREWLINK_RANK_ALIASES = {
    "MST": "MST",
    "MASTER": "MST",
    "CO": "CO",
    "CHIEF OFFICER": "CO",
    "2O": "CO",
    "C/O": "CO",
    "A3O": "A3O",
    "3O": "A3O",
    "3/O": "A3O",
}


def _clone_document_bundle(template_crew_id: str, replacements: Dict[str, str]) -> Dict[str, Any]:
    bundle = deepcopy(BASE_DOCUMENTS[template_crew_id])
    for section in bundle["sections"]:
        for item in section["items"]:
            if item.get("docNo"):
                updated_doc_no = item["docNo"]
                for source, target in replacements.items():
                    updated_doc_no = updated_doc_no.replace(source, target)
                item["docNo"] = updated_doc_no
    return bundle


def _seed_sample_replacements() -> None:
    extra_crew = [
        {
            "id": "c004",
            "srNo": 4,
            "rank": "A3O",
            "name": "Rohit Kishore Nair",
            "empNo": "A9104",
            "nationality": "Indian",
            "dateOfBirth": "19-May-1993",
            "indosNo": "INDOS-A9104",
            "travelDate": "02-Aug-2026",
            "signOnDate": "05-Aug-2026",
            "reliefDue": "05-Feb-2027",
            "relieverRank": "A3O",
            "relieverName": "Francis Zamani Duniya",
            "relieverApproved": True,
            "aiStatus": "red",
            "complianceIssue": True,
            "status": "planned",
        },
        {
            "id": "c005",
            "srNo": 5,
            "rank": "CO",
            "name": "Emmanuel Bassey",
            "empNo": "A9105",
            "nationality": "Nigerian",
            "dateOfBirth": "28-Jan-1991",
            "indosNo": "",
            "travelDate": "30-Jul-2026",
            "signOnDate": "02-Aug-2026",
            "reliefDue": "02-Feb-2027",
            "relieverRank": "CO",
            "relieverName": "Anish Ranjan Singh",
            "relieverApproved": True,
            "aiStatus": "yellow",
            "complianceIssue": False,
            "status": "planned",
        },
        {
            "id": "c006",
            "srNo": 6,
            "rank": "MST",
            "name": "Jose Manuel Cruz",
            "empNo": "A9106",
            "nationality": "Filipino",
            "dateOfBirth": "07-Sep-1984",
            "indosNo": "",
            "travelDate": "12-Aug-2026",
            "signOnDate": "15-Aug-2026",
            "reliefDue": "15-Feb-2027",
            "relieverRank": "MST",
            "relieverName": "Hilton Henry Barreto",
            "relieverApproved": False,
            "aiStatus": "green",
            "complianceIssue": False,
            "status": "planned",
        },
    ]
    BASE_CREW.extend(extra_crew)

    BASE_DOCUMENTS.update(
        {
            "c004": _clone_document_bundle("c002", {"A5743": "A9104"}),
            "c005": _clone_document_bundle("c003", {"A0806": "A9105"}),
            "c006": _clone_document_bundle("c001", {"A6227": "A9106"}),
        }
    )

    BASE_CONFIRMATION.update(
        {
            "c004": deepcopy(BASE_CONFIRMATION["c002"]),
            "c005": deepcopy(BASE_CONFIRMATION["c003"]),
            "c006": deepcopy(BASE_CONFIRMATION["c001"]),
        }
    )


_seed_sample_replacements()


class PortalVerifyRequest(BaseModel):
    docName: str
    docNo: str
    issueAuthority: Optional[str] = None


class CrewlinkImportRequest(BaseModel):
    vesselId: Optional[int] = None
    crewIds: Optional[List[int]] = None
    maxCrew: Optional[int] = None
    replaceState: bool = True


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
    provider = os.environ.get("PORTAL_PROVIDER", "official-portal-automation")
    base_url = os.environ.get("PORTAL_API_BASE_URL", "").rstrip("/")
    return {
        "provider": provider,
        "configured": bool(base_url) or _portal_live_checks_enabled(),
        "baseUrl": base_url,
        "storagePath": data_dir(),
        "databasePath": db_path(),
    }


def _portal_links() -> Dict[str, str]:
    return {
        "uk_mca_coc": os.environ.get("UK_MCA_COC_PORTAL_URL", DEFAULT_PORTAL_LINKS["uk_mca_coc"]).strip(),
        "dg_shipping_home": os.environ.get("DG_SHIPPING_PORTAL_URL", DEFAULT_PORTAL_LINKS["dg_shipping_home"]).strip(),
        "dg_shipping_cdc": os.environ.get("DG_SHIPPING_CDC_CHECKER_URL", DEFAULT_PORTAL_LINKS["dg_shipping_cdc"]).strip(),
        "dg_shipping_coc": os.environ.get("DG_SHIPPING_COC_CHECKER_URL", DEFAULT_PORTAL_LINKS["dg_shipping_coc"]).strip(),
        "dg_shipping_indos": os.environ.get("DG_SHIPPING_INDOS_CHECKER_URL", DEFAULT_PORTAL_LINKS["dg_shipping_indos"]).strip(),
        "imo_gisis_directory": os.environ.get("IMO_GISIS_CERTIFICATE_DIRECTORY_URL", DEFAULT_PORTAL_LINKS["imo_gisis_directory"]).strip(),
    }


def _crewlink_configuration() -> Dict[str, Any]:
    token = os.environ.get("CREWLINK_API_TOKEN", "").strip()
    api_base = os.environ.get("CREWLINK_API_BASE_URL", "https://api.crewlinkasm.com/api").rstrip("/")
    web_base = os.environ.get("CREWLINK_WEB_BASE_URL", "https://www.crewlinkasm.com").rstrip("/")
    vessel_id = os.environ.get("CREWLINK_VESSEL_ID", "").strip()
    return {
        "configured": bool(token),
        "apiBaseUrl": api_base,
        "webBaseUrl": web_base,
        "vesselId": int(vessel_id) if vessel_id.isdigit() else None,
        "hasToken": bool(token),
        "token": token,
    }


def _ai_configuration() -> Dict[str, Any]:
    preferred = os.environ.get("AI_PROVIDER", "auto").strip().lower()
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    if preferred == "openai" and openai_key:
        return {
            "provider": "openai",
            "configured": True,
            "model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
            "baseUrl": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            "apiKey": openai_key,
        }
    if preferred == "anthropic" and anthropic_key:
        return {
            "provider": "anthropic",
            "configured": True,
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            "baseUrl": "https://api.anthropic.com",
            "apiKey": anthropic_key,
        }
    if openai_key:
        return {
            "provider": "openai",
            "configured": True,
            "model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
            "baseUrl": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            "apiKey": openai_key,
        }
    if anthropic_key:
        return {
            "provider": "anthropic",
            "configured": True,
            "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            "baseUrl": "https://api.anthropic.com",
            "apiKey": anthropic_key,
        }
    return {
        "provider": "fallback",
        "configured": False,
        "model": "rule-based",
        "baseUrl": "",
        "apiKey": "",
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


def _portal_live_checks_enabled() -> bool:
    return os.environ.get("PORTAL_LIVE_CHECKS", "1").strip().lower() not in {"0", "false", "no", "off"}


def _origin_from_url(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _html_to_text(value: str) -> str:
    cleaned = re.sub(r"<br\s*/?>", "\n", value or "", flags=re.I)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return _normalize_text(unescape(cleaned))


def _parse_display_date(value: str) -> Optional[datetime]:
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _format_portal_date_for_dg(value: str) -> str:
    parsed = _parse_display_date(value)
    return parsed.strftime("%d/%m/%Y") if parsed else ""


def _format_portal_date_for_uk(value: str) -> str:
    parsed = _parse_display_date(value)
    return parsed.strftime("%Y-%m-%d") if parsed else ""


def _crew_portal_profile(crew_id: str) -> Dict[str, str]:
    crew = _find_crew_member(crew_id)
    passport_no = ""
    try:
        passport_no = _find_document_by_name(crew_id, "Passport").get("docNo", "")
    except HTTPException:
        passport_no = ""
    return {
        "dateOfBirth": crew.get("dateOfBirth", ""),
        "indosNo": crew.get("indosNo", ""),
        "passportNo": passport_no,
        "nationality": crew.get("nationality", ""),
        "crewName": crew.get("name", ""),
    }


def _format_date_display(value: Optional[str]) -> str:
    if not value:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    parsed = _parse_display_date(text)
    if parsed:
        return parsed.strftime("%d-%b-%Y")
    normalized = text.replace(".000Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(normalized, fmt).strftime("%d-%b-%Y")
        except ValueError:
            continue
    return text


def _normalized_rank_for_matrix(rank_code: str, rank_name: str = "") -> str:
    candidate = (rank_code or rank_name or "").strip().upper()
    return CREWLINK_RANK_ALIASES.get(candidate, candidate)


def _doc_type_from_name(name: str) -> str:
    lowered = name.lower()
    if "passport" in lowered or "cdc" in lowered or "indos" in lowered:
        return "Travel"
    if "gmdss" in lowered:
        return "IV/2"
    if "competency" in lowered or "watch" in lowered:
        return "II/2"
    return "Imported"


CREWLINK_CHECKLIST_SECTIONS = [
    ("Travel Documents", "travel", "Checklist/chkOnSelTravel"),
    ("National Licenses", "license", "Checklist/chkOnSelLic"),
    ("Flag State Endorsements", "flag", "Checklist/chkOnSelFlagLic"),
    ("STCW Courses", "course", "Checklist/chkOnSelCourse"),
    ("Other Documents / Pre-joining Docs", "other", "Checklist/chkOnSelOther"),
    ("Medical", "medical", "Checklist/chkOnSelMedical"),
]


def _crewlink_has_value(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    return bool(text and text.lower() not in {"na", "n/a", "nil", "null"})


def _crewlink_checklist_name(raw_name: str) -> str:
    cleaned = re.sub(r"^[A-Z]\s*:\s*", "", (raw_name or "").strip())
    replacements = {
        "INDos No": "INDoS Number",
        "Medical Decalration": "Medical Declaration",
        "Yellow fever Cert": "Yellow Fever Certificate",
    }
    return replacements.get(cleaned, cleaned or "Imported Checklist Item")


def _crewlink_is_expired(value: Any) -> bool:
    if not value:
        return False
    normalized = str(value).strip()
    if not normalized or normalized.startswith("1900-01-01"):
        return False
    display = _format_date_display(normalized)
    parsed = _parse_display_date(display)
    return bool(parsed and parsed.date() < datetime.now(UTC).date())


def _crewlink_requires_attention(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    return any(
        marker in lowered
        for marker in (
            "review",
            "pending",
            "will check",
            "await",
            "waiver",
            "ops",
            "retry",
            "manual",
        )
    )


def _crewlink_effective_date(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw or raw.startswith("1900-01-01"):
        return ""
    return _format_date_display(raw)


def _crewlink_item(
    sr_no: int,
    name: str,
    doc_no: str = "",
    issue_date: str = "",
    expiry_date: str = "NA",
    verified: bool = True,
    remark: str = "",
    missing: bool = False,
    attachment_url: str = "",
    type_label: Optional[str] = None,
) -> Dict[str, Any]:
    status: AIStatus = "red" if missing else ("green" if verified else "yellow")
    return {
        "srNo": sr_no,
        "name": name,
        "docNo": doc_no,
        "type": type_label or _doc_type_from_name(name),
        "issueDate": issue_date or "",
        "expiryDate": expiry_date or "NA",
        "verifiedRC": verified and not missing,
        "verifiedOps": False,
        "portalVerified": False,
        "aiStatus": status,
        "remark": remark,
        "missing": missing,
        "attachmentUrl": attachment_url,
        "attachmentName": name if attachment_url else "",
        "overrideStatus": "",
        "overrideReason": "",
        "extractionConfidence": 0.98 if verified and not missing else 0.72,
    }


async def _crewlink_get_json(client: httpx.AsyncClient, path: str, **params: Any) -> Any:
    config = _crewlink_configuration()
    response = await client.get(
        f"{config['apiBaseUrl']}/{path.lstrip('/')}",
        params=params,
        headers={
            "Authorization": f"Bearer {config['token']}",
            "Accept": "application/json, text/plain, */*",
            "Origin": config["webBaseUrl"],
            "Referer": f"{config['webBaseUrl']}/",
        },
    )
    response.raise_for_status()
    return response.json()


async def _crewlink_post_json(client: httpx.AsyncClient, path: str, payload: Dict[str, Any]) -> Any:
    config = _crewlink_configuration()
    response = await client.post(
        f"{config['apiBaseUrl']}/{path.lstrip('/')}",
        json=payload,
        headers={
            "Authorization": f"Bearer {config['token']}",
            "Accept": "application/json, text/plain, */*",
            "Origin": config["webBaseUrl"],
            "Referer": f"{config['webBaseUrl']}/",
        },
    )
    response.raise_for_status()
    return response.json()


async def _crewlink_try_get_json(client: httpx.AsyncClient, path: str, **params: Any) -> Any:
    try:
        return await _crewlink_get_json(client, path, **params)
    except httpx.HTTPError:
        return None


async def _crewlink_try_post_json(client: httpx.AsyncClient, path: str, payload: Dict[str, Any]) -> Any:
    try:
        return await _crewlink_post_json(client, path, payload)
    except httpx.HTTPError:
        return None


def _crewlink_license_to_name(license_item: Dict[str, Any]) -> str:
    license_name = (
        license_item.get("licenceRegister", {}).get("licenceName")
        or license_item.get("licenseName")
        or "Imported License"
    )
    lowered = license_name.lower()
    if "master" in lowered and "ii/2" in lowered:
        return "Certificate of Competency (Master)"
    if ("chief mate" in lowered or "chief officer" in lowered) and "ii/2" in lowered:
        return "Certificate of Competency (Chief Officer)"
    if "navigational watch" in lowered or "ii/1" in lowered:
        return "Officer in Charge of Navigational Watch II/1"
    if "gmdss" in lowered:
        return "GMDSS Radio Operator Certificate IV/2"
    return license_name


def _crewlink_checklist_request(
    list_item: Dict[str, Any],
    crew_id: int,
    sign_on: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not sign_on:
        return None
    expected_sign_on_date = (
        sign_on.get("expectedSignOnDate")
        or list_item.get("signOnDate")
        or list_item.get("travelDate")
    )
    if not expected_sign_on_date:
        return None
    return {
        "checklistId": 0,
        "crewId": crew_id,
        "rankId": sign_on.get("rankId") or list_item.get("rankId") or list_item.get("relieverRankId") or 0,
        "vesselId": sign_on.get("vesselId") or list_item.get("vesselId") or 0,
        "activitySignOnId": sign_on.get("activitySignOnId") or 0,
        "expectedSignOnDate": expected_sign_on_date,
        "duration": str(sign_on.get("duration") or "3"),
        "validityPeriod": str(sign_on.get("docsValidityCheckPeriod") or "3"),
    }


def _crewlink_item_from_checklist(
    sr_no: int,
    section_kind: str,
    raw_item: Dict[str, Any],
) -> Dict[str, Any]:
    name = _crewlink_checklist_name(raw_item.get("docname", ""))
    level = (raw_item.get("level") or "").strip()
    remark = (raw_item.get("remark1") or "").strip()
    file_path = (raw_item.get("filePath") or "").strip()
    doc_no = str(raw_item.get("docNo") or "").strip()
    issue_date = _crewlink_effective_date(raw_item.get("issueDate"))
    expiry_date = _format_date_display(raw_item.get("expiryDate")) or "NA"
    verified_rc = bool(raw_item.get("firstVerification") or raw_item.get("firstVerifiedOn"))
    verified_ops = bool(raw_item.get("secondVerification") or raw_item.get("secondVerifiedOn"))
    has_evidence = bool(
        file_path
        or _crewlink_has_value(doc_no)
        or issue_date
        or verified_rc
        or verified_ops
    )
    preferred = level.lower() == "preferred"
    not_applicable = (
        remark.lower() in {"na", "n/a"}
        and not has_evidence
        and not verified_rc
        and not verified_ops
    )

    if section_kind in {"course", "other"}:
        required = level.lower() == "mandatory"
    else:
        required = not preferred and not not_applicable

    missing = required and not has_evidence
    expired = required and _crewlink_is_expired(raw_item.get("expiryDate"))
    pending = (
        required
        and not missing
        and not expired
        and (
            _crewlink_requires_attention(remark)
            or (verified_rc and not verified_ops)
            or (not verified_rc and not verified_ops)
        )
    )

    if missing or expired:
        ai_status: AIStatus = "red"
    elif pending:
        ai_status = "yellow"
    elif has_evidence:
        ai_status = "green"
    else:
        ai_status = "grey"

    final_remark = remark
    if not final_remark and missing:
        final_remark = "Required by Crewlink checklist but the document is not attached."
    elif not final_remark and expired:
        final_remark = "Document appears expired in Crewlink."
    elif not final_remark and pending:
        final_remark = "Checklist verification is pending."

    type_label = str(raw_item.get("type") or "").strip() or _doc_type_from_name(name)
    item = {
        "srNo": sr_no,
        "name": name,
        "docNo": doc_no if _crewlink_has_value(doc_no) else "",
        "type": type_label,
        "issueDate": issue_date or "",
        "expiryDate": expiry_date,
        "verifiedRC": verified_rc or verified_ops,
        "verifiedOps": False,
        "portalVerified": False,
        "aiStatus": ai_status,
        "remark": final_remark,
        "missing": missing,
        "expired": expired,
        "attachmentUrl": file_path,
        "attachmentName": name if file_path else "",
        "overrideStatus": "",
        "overrideReason": "",
        "required": required,
        "checklistLevel": level,
        "extractionConfidence": 0.99 if has_evidence else 0.7,
    }
    if raw_item.get("checkListId"):
        item["crewlinkChecklistId"] = raw_item["checkListId"]
    return item


def _crewlink_build_checklist_documents(
    checklist_sections: Dict[str, List[Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    sections: List[Dict[str, Any]] = []
    sr_no = 1

    for title, key, _endpoint in CREWLINK_CHECKLIST_SECTIONS:
        raw_items = checklist_sections.get(key) or []
        items: List[Dict[str, Any]] = []
        for raw_item in raw_items:
            items.append(_crewlink_item_from_checklist(sr_no, key, raw_item))
            sr_no += 1
        if items:
            sections.append({"title": title, "items": items})

    if not sections:
        return None

    return {"sections": sections, "summary": {"valid": 0, "pendingVerification": 0, "missing": 0, "expired": 0}}


async def _crewlink_fetch_crew_bundle(client: httpx.AsyncClient, crew_id: int) -> Dict[str, Any]:
    results = await asyncio.gather(
        _crewlink_try_get_json(client, "CrewDetails/getParticular", crewId=crew_id),
        _crewlink_try_get_json(client, "passport/getByCrewId", crewId=crew_id),
        _crewlink_try_get_json(client, "CDC/filter", status=0, crewId=crew_id),
        _crewlink_try_get_json(client, "crewotherdocuments/GetIndos", crewId=crew_id),
        _crewlink_try_get_json(client, "CrewLicense/getCrewLicense", status=0, crewId=crew_id),
        _crewlink_try_get_json(client, f"ActivitySignOn/signonbyuserid/{crew_id}"),
    )
    return {
        "particulars": results[0][0] if isinstance(results[0], list) and results[0] else {},
        "passport": results[1] or {},
        "cdc": results[2] or [],
        "indos": results[3] or [],
        "licenses": results[4] or [],
        "signOn": results[5] if isinstance(results[5], dict) else None,
    }


async def _crewlink_fetch_checklist_sections(
    client: httpx.AsyncClient,
    list_item: Dict[str, Any],
    crew_id: int,
    sign_on: Optional[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    payload = _crewlink_checklist_request(list_item, crew_id, sign_on)
    if not payload:
        return {}

    requests = [
        _crewlink_try_post_json(client, endpoint, payload)
        for _title, _key, endpoint in CREWLINK_CHECKLIST_SECTIONS
    ]
    responses = await asyncio.gather(*requests)

    sections: Dict[str, List[Dict[str, Any]]] = {}
    for (_title, key, _endpoint), response in zip(CREWLINK_CHECKLIST_SECTIONS, responses):
        if isinstance(response, list) and response:
            sections[key] = response
    return sections


def _crewlink_build_documents(
    rank_code: str,
    bundle: Dict[str, Any],
    checklist_sections: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Any]:
    checklist_docs = _crewlink_build_checklist_documents(checklist_sections or {})
    if checklist_docs:
        return checklist_docs

    sections: List[Dict[str, Any]] = []
    sr_no = 1

    travel_items: List[Dict[str, Any]] = []
    passport = bundle.get("passport") or {}
    if passport:
        travel_items.append(
            _crewlink_item(
                sr_no,
                "Passport",
                doc_no=passport.get("passportNumber", ""),
                issue_date=_format_date_display(passport.get("doi")),
                expiry_date=_format_date_display(passport.get("doe")) or "NA",
                verified=bool(passport.get("isVerified", True)),
                remark="Imported from Crewlink Passport register.",
                attachment_url=passport.get("filePath", ""),
            )
        )
        sr_no += 1

    cdc_items = bundle.get("cdc") or []
    if cdc_items:
        cdc_item = cdc_items[0]
        travel_items.append(
            _crewlink_item(
                sr_no,
                "CDC (Continuous Discharge Certificate)",
                doc_no=cdc_item.get("cdcNumber", ""),
                issue_date=_format_date_display(cdc_item.get("doi")),
                expiry_date=_format_date_display(cdc_item.get("doe")) or "NA",
                verified=bool(cdc_item.get("isVerified", True)),
                remark="Imported from Crewlink CDC register.",
                attachment_url=cdc_item.get("filePath", ""),
            )
        )
        sr_no += 1

    indos_items = bundle.get("indos") or []
    if indos_items:
        indos_item = indos_items[0]
        travel_items.append(
            _crewlink_item(
                sr_no,
                "INDoS Number",
                doc_no=indos_item.get("documentNo", ""),
                issue_date=_format_date_display(indos_item.get("issueDate")),
                expiry_date=_format_date_display(indos_item.get("expiryDate")) or "NA",
                verified=True,
                remark="Imported from Crewlink other documents.",
                attachment_url=indos_item.get("attachment", ""),
            )
        )
        sr_no += 1

    if travel_items:
        sections.append({"title": "Travel Documents", "items": travel_items})

    license_items: List[Dict[str, Any]] = []
    for license_item in bundle.get("licenses") or []:
        license_items.append(
            _crewlink_item(
                sr_no,
                _crewlink_license_to_name(license_item),
                doc_no=license_item.get("licenseNumber", ""),
                issue_date=_format_date_display(license_item.get("issueDate")),
                expiry_date=_format_date_display(license_item.get("expiryDate")) or "NA",
                verified=bool(license_item.get("isVerified", True)),
                remark="Imported from Crewlink license register.",
                attachment_url=license_item.get("attachment", ""),
            )
        )
        sr_no += 1
    if license_items:
        sections.append({"title": "License (National & Flag)", "items": license_items})

    imported_names = {item["name"] for section in sections for item in section["items"]}
    for required_name in VESSEL_MATRIX.get(rank_code, []):
        if required_name in imported_names or required_name in {"Passport", "CDC (Continuous Discharge Certificate)"}:
            continue
        target_title = "STCW Courses"
        lower_name = required_name.lower()
        if "flag cdc" in lower_name or "competency" in lower_name or "gmdss" in lower_name:
            target_title = "License (National & Flag)"
        elif "offer letter" in lower_name or "interview sheet" in lower_name or "employment" in lower_name or "undertaking" in lower_name or "briefing" in lower_name:
            target_title = "Other Documents / Pre-joining Docs"
        elif "security training" in lower_name or "personal safety" in lower_name or "pssr" in lower_name:
            target_title = "STCW Basic Courses"
        existing = next((section for section in sections if section["title"] == target_title), None)
        if not existing:
            existing = {"title": target_title, "items": []}
            sections.append(existing)
        existing["items"].append(
            _crewlink_item(
                sr_no,
                required_name,
                verified=False,
                remark="Required by vessel matrix but not found in Crewlink import.",
                missing=True,
            )
        )
        sr_no += 1

    return {"sections": sections, "summary": {"valid": 0, "pendingVerification": 0, "missing": 0, "expired": 0}}


def _crewlink_build_confirmation() -> List[Dict[str, Any]]:
    return deepcopy(CREWLINK_CONFIRMATION_TEMPLATE)


def _crewlink_build_crew_member(list_item: Dict[str, Any], particulars: Dict[str, Any]) -> Dict[str, Any]:
    rank_code = _normalized_rank_for_matrix(list_item.get("rank", ""), particulars.get("rankRegister", {}).get("code", ""))
    crew_name = " ".join(
        part
        for part in [list_item.get("firstName"), list_item.get("middleName"), list_item.get("lastName")]
        if part
    ).strip()
    due_date = list_item.get("dueDate") or particulars.get("reliefDate") or ""
    status = "onboard" if (particulars.get("status") or list_item.get("status") or "").lower() == "onboard" else "planned"
    return {
        "id": f"cl{list_item.get('crewId') or list_item.get('reliever1') or secrets.token_hex(4)}",
        "srNo": 0,
        "rank": rank_code,
        "name": crew_name or list_item.get("relieverName") or "Unknown Crew",
        "empNo": list_item.get("empNumber") or list_item.get("relieverEmpNumber") or "",
        "nationality": list_item.get("nationality") or "",
        "dateOfBirth": _format_date_display(particulars.get("dob")),
        "indosNo": "",
        "travelDate": _format_date_display(list_item.get("travelDate")),
        "signOnDate": _format_date_display(list_item.get("signOnDate")),
        "reliefDue": _format_date_display(due_date),
        "relieverRank": list_item.get("relieverRank") or "",
        "relieverName": list_item.get("relieverName") or "",
        "relieverApproved": str(list_item.get("planStatus") or "").lower() == "approved",
        "aiStatus": "yellow",
        "complianceIssue": False,
        "status": status,
        "crewlinkCrewId": list_item.get("crewId"),
        "crewlinkCrewListId": list_item.get("crewListId"),
    }


async def _import_crewlink_vessel(
    *,
    vessel_id: Optional[int],
    crew_ids: Optional[List[int]],
    max_crew: Optional[int],
    replace_state: bool,
    actor: str,
) -> Dict[str, Any]:
    config = _crewlink_configuration()
    if not config["configured"]:
        raise HTTPException(status_code=400, detail="Crewlink API token is not configured.")
    target_vessel_id = vessel_id or config["vesselId"]
    if not target_vessel_id:
        raise HTTPException(status_code=400, detail="Crewlink vessel ID is not configured.")

    async with httpx.AsyncClient(timeout=30.0) as client:
        vessel_header, crew_list = await asyncio.gather(
            _crewlink_get_json(client, "Vessel/getVesselHeader", vesselId=target_vessel_id),
            _crewlink_get_json(client, "CrewList/getCrewList", vesselId=target_vessel_id),
        )

        selected_list = [item for item in crew_list if item.get("crewId") or item.get("reliever1")]
        if crew_ids:
            requested = set(crew_ids)
            selected_list = [item for item in selected_list if item.get("crewId") in requested or item.get("reliever1") in requested]
        if max_crew:
            selected_list = selected_list[:max_crew]

        imported_crew: List[Dict[str, Any]] = []
        imported_documents: Dict[str, Any] = {}
        imported_confirmation: Dict[str, Any] = {}
        imported_audit_logs: Dict[str, Any] = {}

        for index, item in enumerate(selected_list, start=1):
            source_crew_id = item.get("crewId") or item.get("reliever1")
            if not source_crew_id:
                continue
            bundle = await _crewlink_fetch_crew_bundle(client, int(source_crew_id))
            checklist_sections = await _crewlink_fetch_checklist_sections(
                client,
                item,
                int(source_crew_id),
                bundle.get("signOn"),
            )
            crew_member = _crewlink_build_crew_member(item, bundle["particulars"])
            crew_member["srNo"] = index
            if bundle.get("indos"):
                crew_member["indosNo"] = bundle["indos"][0].get("documentNo", "")
            imported_crew.append(crew_member)
            imported_documents[crew_member["id"]] = _crewlink_build_documents(
                crew_member["rank"],
                bundle,
                checklist_sections,
            )
            imported_confirmation[crew_member["id"]] = _crewlink_build_confirmation()
            imported_audit_logs[crew_member["id"]] = [
                {
                    "id": secrets.token_hex(6),
                    "timestamp": now_stamp(),
                    "actor": actor,
                    "action": "crewlink_import",
                    "target": crew_member["name"],
                    "message": f"Imported live Crewlink data for {crew_member['name']} ({crew_member['empNo']}) from vessel {item.get('vesselName') or target_vessel_id}.",
                }
            ]

    if replace_state:
        STATE["crew"] = imported_crew
        STATE["documents"] = imported_documents
        STATE["confirmation"] = imported_confirmation
        STATE["audit_logs"] = imported_audit_logs
        STATE["learning_feedback"] = {}
        STATE["self_service_links"] = {}
        STATE["latest_link_by_crew"] = {}
    else:
        existing_ids = {crew["id"] for crew in STATE["crew"]}
        for crew_member in imported_crew:
            if crew_member["id"] not in existing_ids:
                STATE["crew"].append(crew_member)
        STATE["documents"].update(imported_documents)
        STATE["confirmation"].update(imported_confirmation)
        STATE["audit_logs"].update(imported_audit_logs)

    vessel = vessel_header[0] if vessel_header else {}
    STATE["vessel"] = {
        "id": f"crewlink-vessel-{target_vessel_id}",
        "name": vessel.get("vesselName") or f"Vessel {target_vessel_id}",
        "type": vessel.get("shipCategory") or "",
        "imo": f"IMO {vessel.get('imo')}" if vessel.get("imo") else "",
        "flag": vessel.get("flag") or "",
        "totalCrew": len(imported_crew),
        "reliefOverdue": 0,
        "dueOneMonth": 0,
        "extraCrew": len([crew for crew in imported_crew if crew.get("status") == "planned"]),
        "extendedContract": 0,
        "reducedContract": 0,
        "crewlinkVesselId": target_vessel_id,
    }

    for crew_member in imported_crew:
        _recalculate_crew(crew_member["id"])

    persist_state()
    return {
        "ok": True,
        "vessel": STATE["vessel"],
        "importedCrew": len(imported_crew),
        "crewIds": [crew["id"] for crew in imported_crew],
    }


def _build_portal_result(
    *,
    doc_name: str,
    verified: bool,
    message: str,
    portal: str,
    portal_label: Optional[str],
    portal_url: Optional[str],
    verification_mode: Literal["auto", "manual", "directory"],
    required_inputs: Optional[List[str]] = None,
    recommended_ai_status: AIStatus = "yellow",
    checklist_status: Literal["good", "pending", "missing"] = "pending",
) -> Dict[str, Any]:
    return {
        "docName": doc_name,
        "verified": verified,
        "message": message,
        "portal": portal,
        "portalLabel": portal_label or portal,
        "portalUrl": portal_url or "",
        "verificationMode": verification_mode,
        "requiredInputs": required_inputs or [],
        "recommendedAiStatus": recommended_ai_status,
        "checklistStatus": checklist_status,
    }


def _looks_like_indian_competency_name(doc_name: str) -> bool:
    candidate = doc_name.lower()
    competency_keywords = (
        "certificate of competency",
        "officer in charge",
        "navigational watch",
        "chief officer",
        "chief mate",
        "second mate",
        "master",
        "mate f.g.",
        "master f.g.",
        "engineer officer",
        "chief engineer",
        "second engineer",
        "watchkeeping officer",
    )
    if any(keyword in candidate for keyword in competency_keywords):
        return True
    return bool(re.search(r"\bii/[12]\b|\biii/[12]\b|\biv/2\b", candidate)) and "gmdss" not in candidate


def _resolve_portal_route(
    crew_id: str,
    doc_name: str,
    doc_no: str = "",
    issue_authority: Optional[str] = None,
) -> Dict[str, Any]:
    crew = _find_crew_member(crew_id)
    links = _portal_links()
    authority = (issue_authority or "").strip().lower()
    name = doc_name.lower()
    number = doc_no.upper()

    indian_document = (
        authority in {"india", "dg shipping", "indos", "mmd"}
        or crew["nationality"].lower() == "indian"
        or number.startswith(("IND-", "MUM", "KOL", "CHN"))
        or "indos" in name
    )
    uk_document = authority in {"uk", "united kingdom", "mca"} or "mca" in name or "fse" in name

    if uk_document:
        return {
            "portal": "UK MCA",
            "portalLabel": "UK CoC / FSE Checker",
            "portalUrl": links["uk_mca_coc"],
            "verificationMode": "auto",
            "requiredInputs": ["Document ID", "Seafarer date of birth"],
            "message": "Validate the document ID against the seafarer's date of birth through the UK MCA checker.",
            "strategy": "uk_mca_coc",
            "autoCapable": True,
            "eligible": True,
        }

    if indian_document and (
        "coc" in name
        or "certificate of competency" in name
        or "officer in charge" in name
        or _looks_like_indian_competency_name(name)
    ):
        return {
            "portal": "DG Shipping India",
            "portalLabel": "DG Shipping CoC Checker",
            "portalUrl": links["dg_shipping_coc"],
            "verificationMode": "auto",
            "requiredInputs": ["INDoS number", "Seafarer date of birth"],
            "message": "Validate the Indian competency record through DG Shipping using INDoS and date of birth.",
            "strategy": "dg_coc",
            "autoCapable": True,
            "eligible": True,
        }

    if indian_document and ("gmdss" in name):
        return {
            "portal": "DG Shipping India",
            "portalLabel": "DG Shipping GMDSS Checker",
            "portalUrl": links["dg_shipping_indos"],
            "verificationMode": "auto",
            "requiredInputs": ["INDoS number", "Seafarer date of birth"],
            "message": "Validate the GMDSS certificate through DG Shipping using INDoS and date of birth.",
            "strategy": "dg_cop",
            "searchType": "GMDSS",
            "autoCapable": True,
            "eligible": True,
        }

    if indian_document and ("watch keeping" in name or "etr" in name or "ab " in name):
        return {
            "portal": "DG Shipping India",
            "portalLabel": "DG Shipping Watchkeeping / AB / ETR Checker",
            "portalUrl": links["dg_shipping_indos"],
            "verificationMode": "auto",
            "requiredInputs": ["INDoS number", "Seafarer date of birth"],
            "message": "Validate the watchkeeping / AB / ETR certificate through DG Shipping using INDoS and date of birth.",
            "strategy": "dg_cop",
            "searchType": "WK",
            "autoCapable": True,
            "eligible": True,
        }

    if indian_document and ("dc endorsement" in name):
        return {
            "portal": "DG Shipping India",
            "portalLabel": "DG Shipping COP - DC Endorsement Checker",
            "portalUrl": links["dg_shipping_indos"],
            "verificationMode": "auto",
            "requiredInputs": ["INDoS number", "Seafarer date of birth"],
            "message": "Validate the dangerous cargo endorsement through DG Shipping using INDoS and date of birth.",
            "strategy": "dg_cop",
            "searchType": "DC",
            "autoCapable": True,
            "eligible": True,
        }

    if indian_document and ("polar" in name):
        return {
            "portal": "DG Shipping India",
            "portalLabel": "DG Shipping Polar Water Checker",
            "portalUrl": links["dg_shipping_indos"],
            "verificationMode": "auto",
            "requiredInputs": ["INDoS number", "Seafarer date of birth"],
            "message": "Validate the Polar Water endorsement through DG Shipping using INDoS and date of birth.",
            "strategy": "dg_cop",
            "searchType": "DCPOLAR",
            "autoCapable": True,
            "eligible": True,
        }

    if indian_document and ("igf" in name):
        return {
            "portal": "DG Shipping India",
            "portalLabel": "DG Shipping IGF Code Checker",
            "portalUrl": links["dg_shipping_indos"],
            "verificationMode": "auto",
            "requiredInputs": ["INDoS number", "Seafarer date of birth"],
            "message": "Validate the IGF certificate through DG Shipping using INDoS and date of birth.",
            "strategy": "dg_cop",
            "searchType": "IGF",
            "autoCapable": True,
            "eligible": True,
        }

    if indian_document and ("indos" in name):
        return {
            "portal": "DG Shipping India",
            "portalLabel": "DG Shipping INDoS Checker",
            "portalUrl": links["dg_shipping_indos"],
            "verificationMode": "auto",
            "requiredInputs": ["INDoS number", "Seafarer date of birth"],
            "message": "Validate the INDoS record through DG Shipping using INDoS and date of birth.",
            "strategy": "dg_indos",
            "autoCapable": True,
            "eligible": True,
        }

    if indian_document and ("cop" in name):
        return {
            "portal": "DG Shipping India",
            "portalLabel": "DG Shipping INDoS / CoP Checker",
            "portalUrl": links["dg_shipping_indos"],
            "verificationMode": "auto",
            "requiredInputs": ["INDoS number", "Seafarer date of birth"],
            "message": "Validate the certificate of proficiency through DG Shipping using INDoS and date of birth.",
            "strategy": "dg_cop",
            "searchType": "COP",
            "autoCapable": True,
            "eligible": True,
        }

    if "flag cdc" in name or "i/10" in name or "flag endorsement" in name:
        return {
            "portal": "IMO GISIS",
            "portalLabel": "IMO GISIS Certificate Verification Directory",
            "portalUrl": links["imo_gisis_directory"],
            "verificationMode": "directory",
            "requiredInputs": ["Flag state or issuing authority", "Document number", "Seafarer details"],
            "message": "Use the IMO GISIS certificate verification directory to locate the correct flag-state checker for this endorsement.",
            "strategy": "gisis_directory",
            "autoCapable": False,
            "eligible": True,
        }

    if indian_document and ("cdc" in name):
        return {
            "portal": "DG Shipping India",
            "portalLabel": "DG Shipping CDC Checker",
            "portalUrl": links["dg_shipping_cdc"],
            "verificationMode": "auto",
            "requiredInputs": ["CDC number", "Seafarer date of birth"],
            "message": "Validate the CDC number against the seafarer's date of birth through DG Shipping.",
            "strategy": "dg_cdc",
            "autoCapable": True,
            "eligible": True,
        }

    return {
        "portal": "Crewlink AI",
        "portalLabel": "Matrix / document completeness check",
        "portalUrl": links["dg_shipping_home"] if indian_document else "",
        "verificationMode": "auto",
        "requiredInputs": [],
        "message": "This document does not have a supported public verification portal in the current workflow and remains under AI + human checklist review.",
        "strategy": "unsupported",
        "autoCapable": False,
        "eligible": False,
    }


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
    item.setdefault("portalVerified", False)
    item.setdefault("overrideStatus", "")
    item.setdefault("overrideReason", "")
    item.setdefault("extractionConfidence", 0.98 if item.get("verifiedRC") else 0.72)
    item["required"] = item.get("required", item["name"] in required_docs)


def _recalculate_crew(crew_id: str) -> None:
    required_docs = _required_documents_for(crew_id)
    docs = STATE["documents"][crew_id]
    all_items = [item for section in docs["sections"] for item in section["items"]]
    crew = _find_crew_member(crew_id)
    crewlink_imported = bool(crew.get("crewlinkCrewId"))

    if not required_docs:
        for item in all_items:
            _hydrate_document_item(crew_id, item, required_docs)
        docs["summary"] = {
            "valid": 0,
            "pendingVerification": 0,
            "missing": 0,
            "expired": 0,
        }
        crew["aiStatus"] = "yellow"
        crew["complianceIssue"] = False
        return

    valid = 0
    pending = 0
    missing = 0
    expired = 0

    for item in all_items:
        _hydrate_document_item(crew_id, item, required_docs)
        status = item.get("overrideStatus") or item.get("aiStatus", "grey")
        route = _resolve_portal_route(crew_id, item["name"], item.get("docNo", ""))
        portal_pending = (
            crewlink_imported
            and item["required"]
            and not item.get("missing")
            and not item.get("expired", False)
            and route.get("eligible")
            and not item.get("portalVerified", False)
            and not item.get("overrideStatus")
        )
        if portal_pending:
            status = "yellow"
            if not item.get("remark"):
                item["remark"] = f"Portal verification pending through {route['portalLabel']}."
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
    if missing > 0 or expired > 0:
        crew["aiStatus"] = "red"
        crew["complianceIssue"] = True
    elif pending > 0:
        crew["aiStatus"] = "yellow"
        crew["complianceIssue"] = False
    else:
        crew["aiStatus"] = "green"
        crew["complianceIssue"] = False


async def _run_uk_mca_check(
    client: httpx.AsyncClient,
    route: Dict[str, Any],
    crew_id: str,
    doc_name: str,
    doc_no: str,
) -> Dict[str, Any]:
    profile = _crew_portal_profile(crew_id)
    if not doc_no.strip():
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message="Portal check pending: document ID is missing on this checklist item.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="yellow",
            checklist_status="pending",
        )

    birth_date = _format_portal_date_for_uk(profile["dateOfBirth"])
    if not birth_date:
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message="Portal check pending: crew date of birth is not stored in the profile.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="yellow",
            checklist_status="pending",
        )

    result_url = f"{route['portalUrl'].rstrip('/')}/Certificate-Search-Results/"
    response = await client.get(result_url, params={"documentId": doc_no.strip(), "date": birth_date})
    response.raise_for_status()
    text = _html_to_text(response.text)
    lower_text = text.lower()

    if "no coc record found" in lower_text:
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message="Official UK MCA checker did not find a record for this document ID and date of birth.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=str(response.url),
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="red",
            checklist_status="missing",
        )

    return _build_portal_result(
        doc_name=doc_name,
        verified=True,
        message="Verified automatically through the official UK MCA checker.",
        portal=route["portal"],
        portal_label=route["portalLabel"],
        portal_url=str(response.url),
        verification_mode="auto",
        required_inputs=route["requiredInputs"],
        recommended_ai_status="green",
        checklist_status="good",
    )


async def _run_dg_cdc_check(
    client: httpx.AsyncClient,
    route: Dict[str, Any],
    crew_id: str,
    doc_name: str,
    doc_no: str,
) -> Dict[str, Any]:
    profile = _crew_portal_profile(crew_id)
    if not doc_no.strip():
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message="Portal check pending: CDC number is missing on this checklist item.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="yellow",
            checklist_status="pending",
        )

    dob = _format_portal_date_for_dg(profile["dateOfBirth"])
    if not dob:
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message="Portal check pending: crew date of birth is not stored in the profile.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="yellow",
            checklist_status="pending",
        )

    response = await client.post(
        f"{_origin_from_url(route['portalUrl'])}/IndosApplication/ajaxservlet",
        params={"CDCno": doc_no.strip().upper(), "dob": dob},
    )
    response.raise_for_status()
    text = _html_to_text(response.text)
    lower_text = text.lower()

    if "cdc details not found" in lower_text or "could not find the match of cdc no." in lower_text:
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message="Official DG Shipping checker could not find a matching CDC record.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="red",
            checklist_status="missing",
        )

    return _build_portal_result(
        doc_name=doc_name,
        verified=True,
        message="Verified automatically through the official DG Shipping CDC checker.",
        portal=route["portal"],
        portal_label=route["portalLabel"],
        portal_url=route["portalUrl"],
        verification_mode="auto",
        required_inputs=route["requiredInputs"],
        recommended_ai_status="green",
        checklist_status="good",
    )


async def _run_dg_coc_check(
    client: httpx.AsyncClient,
    route: Dict[str, Any],
    crew_id: str,
    doc_name: str,
) -> Dict[str, Any]:
    profile = _crew_portal_profile(crew_id)
    indos_no = profile["indosNo"].strip()
    dob = _format_portal_date_for_dg(profile["dateOfBirth"])

    if not indos_no:
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message="Portal check pending: INDoS number is not stored in the crew profile.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="yellow",
            checklist_status="pending",
        )
    if not dob:
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message="Portal check pending: crew date of birth is not stored in the profile.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="yellow",
            checklist_status="pending",
        )

    response = await client.post(
        f"{_origin_from_url(route['portalUrl'])}/esamudraUI/jsp/examination/checker/COCSearchDetails.jsp",
        data={"txtNo": indos_no.upper(), "txtDob": dob},
    )
    response.raise_for_status()
    text = _html_to_text(response.text)
    lower_text = text.lower()

    if "could not find coc details" in lower_text:
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message="Official DG Shipping checker could not find a matching Indian competency record.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="red",
            checklist_status="missing",
        )

    return _build_portal_result(
        doc_name=doc_name,
        verified=True,
        message="Verified automatically through the official DG Shipping competency checker.",
        portal=route["portal"],
        portal_label=route["portalLabel"],
        portal_url=route["portalUrl"],
        verification_mode="auto",
        required_inputs=route["requiredInputs"],
        recommended_ai_status="green",
        checklist_status="good",
    )


async def _run_dg_indos_ajax_check(
    client: httpx.AsyncClient,
    route: Dict[str, Any],
    crew_id: str,
    doc_name: str,
    search_type: str,
    txt_no: str,
) -> Dict[str, Any]:
    profile = _crew_portal_profile(crew_id)
    dob = _format_portal_date_for_dg(profile["dateOfBirth"])

    if not txt_no.strip():
        missing_label = "INDoS number" if search_type != "CDC" else "CDC number"
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message=f"Portal check pending: {missing_label} is not stored in the crew profile.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="yellow",
            checklist_status="pending",
        )
    if not dob:
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message="Portal check pending: crew date of birth is not stored in the profile.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="yellow",
            checklist_status="pending",
        )

    response = await client.post(
        f"{_origin_from_url(route['portalUrl'])}/esamudraUI/checkerajaxservlet",
        params={
            "txtNo": txt_no.strip().upper(),
            "dob": dob,
            "processId": "PPIndosCheck",
            "searchType": search_type,
        },
    )
    response.raise_for_status()
    text = _html_to_text(response.text)
    lower_text = text.lower()

    missing_patterns = {
        "Indos": "could not find the match of INDoS No.",
        "CDC": "could not find the match of CDC No.",
    }
    if missing_patterns.get(search_type, "could not find").lower() in lower_text:
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message=f"Official DG Shipping checker could not find a matching {search_type} record.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="red",
            checklist_status="missing",
        )

    return _build_portal_result(
        doc_name=doc_name,
        verified=True,
        message=f"Verified automatically through the official DG Shipping {search_type} checker.",
        portal=route["portal"],
        portal_label=route["portalLabel"],
        portal_url=route["portalUrl"],
        verification_mode="auto",
        required_inputs=route["requiredInputs"],
        recommended_ai_status="green",
        checklist_status="good",
    )


async def _run_dg_cop_check(
    client: httpx.AsyncClient,
    route: Dict[str, Any],
    crew_id: str,
    doc_name: str,
) -> Dict[str, Any]:
    profile = _crew_portal_profile(crew_id)
    indos_no = profile["indosNo"].strip()
    dob = _format_portal_date_for_dg(profile["dateOfBirth"])

    if not indos_no:
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message="Portal check pending: INDoS number is not stored in the crew profile.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="yellow",
            checklist_status="pending",
        )
    if not dob:
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message="Portal check pending: crew date of birth is not stored in the profile.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="yellow",
            checklist_status="pending",
        )

    response = await client.post(
        f"{_origin_from_url(route['portalUrl'])}/esamudraUI/jsp/examination/checker/COPDetails.jsp?hidProcessMode=beforeAdd",
        data={"cmbSearch_by": route["searchType"], "txtNo": indos_no.upper(), "txtDob": dob},
    )
    response.raise_for_status()
    text = _html_to_text(response.text)
    lower_text = text.lower()

    if "could not find" in lower_text and "details" in lower_text:
        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message=f"Official DG Shipping checker could not find a matching {route['searchType']} record.",
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode="auto",
            required_inputs=route["requiredInputs"],
            recommended_ai_status="red",
            checklist_status="missing",
        )

    return _build_portal_result(
        doc_name=doc_name,
        verified=True,
        message=f"Verified automatically through the official DG Shipping {route['searchType']} checker.",
        portal=route["portal"],
        portal_label=route["portalLabel"],
        portal_url=route["portalUrl"],
        verification_mode="auto",
        required_inputs=route["requiredInputs"],
        recommended_ai_status="green",
        checklist_status="good",
    )


async def _run_official_portal_check(
    route: Dict[str, Any],
    crew_id: str,
    doc_name: str,
    doc_no: str,
) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        strategy = route.get("strategy")
        if strategy == "uk_mca_coc":
            return await _run_uk_mca_check(client, route, crew_id, doc_name, doc_no)
        if strategy == "dg_cdc":
            return await _run_dg_cdc_check(client, route, crew_id, doc_name, doc_no)
        if strategy == "dg_coc":
            return await _run_dg_coc_check(client, route, crew_id, doc_name)
        if strategy == "dg_indos":
            profile = _crew_portal_profile(crew_id)
            return await _run_dg_indos_ajax_check(client, route, crew_id, doc_name, "Indos", profile["indosNo"])
        if strategy == "dg_cop":
            return await _run_dg_cop_check(client, route, crew_id, doc_name)

    return _build_portal_result(
        doc_name=doc_name,
        verified=False,
        message="Portal check pending: no automated checker has been configured for this document type.",
        portal=route["portal"],
        portal_label=route["portalLabel"],
        portal_url=route["portalUrl"],
        verification_mode="auto",
        required_inputs=route["requiredInputs"],
        recommended_ai_status="yellow",
        checklist_status="pending",
    )


async def _build_portal_response(
    crew_id: str,
    doc_name: str,
    doc_no: str = "",
    issue_authority: Optional[str] = None,
) -> Dict[str, Any]:
    portal_configuration = _portal_configuration()
    if portal_configuration["configured"]:
        route = _resolve_portal_route(crew_id, doc_name, doc_no, issue_authority)
        if portal_configuration["baseUrl"]:
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
                return _build_portal_result(
                    doc_name=doc_name,
                    verified=bool(payload.get("verified")),
                    message=payload.get("message") or f"{doc_name} verified via {portal_configuration['provider']}.",
                    portal=payload.get("portal") or portal_configuration["provider"],
                    portal_label=payload.get("portalLabel") or payload.get("portal") or portal_configuration["provider"],
                    portal_url=payload.get("portalUrl") or portal_configuration["baseUrl"],
                    verification_mode="auto",
                    required_inputs=payload.get("requiredInputs") or [],
                    recommended_ai_status=payload.get("recommendedAiStatus") or ("green" if payload.get("verified") else "yellow"),
                    checklist_status=payload.get("checklistStatus") or ("good" if payload.get("verified") else "pending"),
                )
            except Exception as exc:
                return _build_portal_result(
                    doc_name=doc_name,
                    verified=False,
                    message=f"{portal_configuration['provider']} integration failed: {exc}",
                    portal=portal_configuration["provider"],
                    portal_label=portal_configuration["provider"],
                    portal_url=portal_configuration["baseUrl"],
                    verification_mode="auto",
                    required_inputs=[],
                    recommended_ai_status="yellow",
                    checklist_status="pending",
                )

        if route.get("autoCapable") and _portal_live_checks_enabled():
            try:
                return await _run_official_portal_check(route, crew_id, doc_name, doc_no)
            except Exception as exc:
                return _build_portal_result(
                    doc_name=doc_name,
                    verified=False,
                    message=f"Official portal automation failed: {exc}",
                    portal=route["portal"],
                    portal_label=route["portalLabel"],
                    portal_url=route["portalUrl"],
                    verification_mode="auto",
                    required_inputs=route["requiredInputs"],
                    recommended_ai_status="yellow",
                    checklist_status="pending",
                )

        if not route.get("eligible"):
            return _build_portal_result(
                doc_name=doc_name,
                verified=False,
                message=route["message"],
                portal=route["portal"],
                portal_label=route["portalLabel"],
                portal_url=route["portalUrl"],
                verification_mode="auto",
                required_inputs=route["requiredInputs"],
                recommended_ai_status="yellow",
                checklist_status="pending",
            )

        return _build_portal_result(
            doc_name=doc_name,
            verified=False,
            message=route["message"],
            portal=route["portal"],
            portal_label=route["portalLabel"],
            portal_url=route["portalUrl"],
            verification_mode=route["verificationMode"],
            required_inputs=route["requiredInputs"],
            recommended_ai_status="yellow",
            checklist_status="pending",
        )
    route = _resolve_portal_route(crew_id, doc_name, doc_no, issue_authority)
    return _build_portal_result(
        doc_name=doc_name,
        verified=False,
        message=route["message"],
        portal=route["portal"],
        portal_label=route["portalLabel"],
        portal_url=route["portalUrl"],
        verification_mode=route["verificationMode"],
        required_inputs=route["requiredInputs"],
        recommended_ai_status="yellow",
        checklist_status="pending",
    )


def _apply_portal_result(crew_id: str, item: Dict[str, Any], result: Dict[str, Any]) -> None:
    item["portalVerified"] = result["verified"]
    item["verifiedOps"] = result["verified"]
    if result.get("verificationMode") == "auto":
        item["aiStatus"] = result.get("recommendedAiStatus", item.get("aiStatus", "yellow"))
        item["remark"] = result.get("message", item.get("remark", ""))
        if result["verified"]:
            item["missing"] = False
            item["overrideStatus"] = ""
            item["overrideReason"] = ""
        else:
            item["verifiedOps"] = False
    elif result["verified"] and not item.get("missing"):
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
    ai_configuration = _ai_configuration()
    if not ai_configuration["configured"]:
        return _get_fallback_narrative(crew_id)

    crew = _find_crew_member(crew_id)
    docs = STATE["documents"][crew_id]
    vessel = STATE.get("vessel", BASE_VESSEL)
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
Vessel: {vessel.get('name', BASE_VESSEL['name'])} ({vessel.get('type', BASE_VESSEL['type'])})
Flag: {vessel.get('flag', BASE_VESSEL['flag'])}
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
        if ai_configuration["provider"] == "openai":
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{ai_configuration['baseUrl']}/responses",
                    headers={
                        "Authorization": f"Bearer {ai_configuration['apiKey']}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": ai_configuration["model"],
                        "max_output_tokens": 400,
                        "input": [
                            {
                                "role": "system",
                                "content": [
                                    {
                                        "type": "input_text",
                                        "text": "You are a maritime compliance officer helping RC and Ops review sign-on checklist readiness.",
                                    }
                                ],
                            },
                            {
                                "role": "user",
                                "content": [{"type": "input_text", "text": prompt}],
                            },
                        ],
                    },
                )
            response.raise_for_status()
            payload = response.json()
            output_text = (payload.get("output_text") or "").strip()
            if output_text:
                return output_text
            for item in payload.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") in {"output_text", "text"} and content.get("text"):
                        return str(content["text"]).strip()
            return _get_fallback_narrative(crew_id)

        client = anthropic.Anthropic(api_key=ai_configuration["apiKey"])
        message = client.messages.create(
            model=ai_configuration["model"],
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
    vessel = STATE.get("vessel", BASE_VESSEL)

    return {
        "crewId": crew_id,
        "name": crew["name"],
        "rank": crew["rank"],
        "vessel": f"{vessel.get('name', BASE_VESSEL['name'])} ({vessel.get('type', BASE_VESSEL['type'])})",
        "flag": vessel.get("flag", BASE_VESSEL["flag"]),
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
    vessel = STATE.get("vessel", BASE_VESSEL)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, f"Crewlink AI-ACE Checklist - {crew['name']}")
    y -= 22

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, y, f"Rank: {crew['rank']}    Emp No: {crew['empNo']}    Vessel: {vessel.get('name', BASE_VESSEL['name'])}")
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
    ai_configuration = _ai_configuration()
    crewlink_configuration = _crewlink_configuration()
    return {
        "portal": {
            "provider": portal_configuration["provider"],
            "configured": portal_configuration["configured"],
            "mode": "external" if portal_configuration["baseUrl"] else ("official-automation" if _portal_live_checks_enabled() else "directory-routed"),
        },
        "ai": {
            "provider": ai_configuration["provider"],
            "configured": ai_configuration["configured"],
            "model": ai_configuration["model"],
            "mode": "external" if ai_configuration["configured"] else "fallback",
        },
        "storage": {
            "databasePath": portal_configuration["databasePath"],
            "uploadsPath": os.path.join(data_dir(), "uploads"),
        },
        "crewlink": {
            "configured": crewlink_configuration["configured"],
            "apiBaseUrl": crewlink_configuration["apiBaseUrl"],
            "vesselId": crewlink_configuration["vesselId"],
        },
        "user": current_user["role"],
    }


@app.get("/api/integrations/crewlink/status")
def get_crewlink_status(current_user: Dict[str, Any] = Depends(require_user({ROLE_ADMIN, ROLE_OPS, ROLE_RC}))):
    configuration = _crewlink_configuration()
    return {
        "configured": configuration["configured"],
        "apiBaseUrl": configuration["apiBaseUrl"],
        "webBaseUrl": configuration["webBaseUrl"],
        "vesselId": configuration["vesselId"],
        "hasToken": configuration["hasToken"],
    }


@app.post("/api/integrations/crewlink/import")
async def import_crewlink_data(
    request: CrewlinkImportRequest,
    current_user: Dict[str, Any] = Depends(require_user({ROLE_ADMIN, ROLE_OPS})),
):
    return await _import_crewlink_vessel(
        vessel_id=request.vesselId,
        crew_ids=request.crewIds,
        max_crew=request.maxCrew,
        replace_state=request.replaceState,
        actor=current_user["fullName"],
    )


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
    item["missing"] = False
    item["verifiedRC"] = True
    item["verifiedOps"] = False
    item["portalVerified"] = False
    item["overrideStatus"] = ""
    item["overrideReason"] = ""
    item["aiStatus"] = "yellow"
    portal_result = await _build_portal_response(crew_id, item["name"], item.get("docNo", ""))
    _apply_portal_result(crew_id, item, portal_result)
    _append_audit(
        crew_id,
        actor=current_user["fullName"],
        action="attachment_uploaded",
        target=item["name"],
        message=f"Uploaded attachment {attachment['originalName']}. {portal_result['message']}",
    )
    persist_state()
    return {"ok": True, "item": item, "summary": STATE["documents"][crew_id]["summary"], "portalResult": portal_result}


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
        if item.get("aiStatus") == "yellow"
        and not item.get("missing")
        and not item.get("portalVerified")
        and _resolve_portal_route(crew_id, item["name"], item.get("docNo", "")).get("eligible")
    ]

    results = []
    verified_count = 0
    failed_count = 0
    manual_count = 0

    for item in items_to_verify:
        result = await _build_portal_response(crew_id, item["name"], item.get("docNo", ""))
        _apply_portal_result(crew_id, item, result)
        if result.get("verificationMode") in {"manual", "directory"} and not result["verified"]:
            manual_count += 1
        elif result["verified"]:
            verified_count += 1
        else:
            failed_count += 1
        results.append(result)

    _append_audit(
        crew_id,
        actor=current_user["fullName"],
        action="batch_verification",
        target="Pending documents",
        message=f"Batch verification completed: {verified_count} verified, {manual_count} routed to portal, {failed_count} failed.",
    )
    persist_state()

    return {
        "crewId": crew_id,
        "verifiedCount": verified_count,
        "failedCount": failed_count,
        "manualCount": manual_count,
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
