from __future__ import annotations

import base64
import json
from dataclasses import dataclass

import gspread
from google.oauth2 import credentials as user_credentials
from google.oauth2 import service_account
from googleapiclient.discovery import Resource, build
from gspread import Client


@dataclass
class AuthorizedClients:
    gc: Client
    drive_service: Resource
    sheets_service: Resource


def authorize(
    credentials: service_account.Credentials | user_credentials.Credentials,
) -> AuthorizedClients:

    # Build and authorize the drive service
    drive_service = build("drive", "v3", credentials=credentials)

    # Build and authorize the sheets service
    sheets_service = build("sheets", "v4", credentials=credentials)

    # Set up a authorized gspread client
    gc = gspread.authorize(credentials)

    return AuthorizedClients(
        gc=gc, drive_service=drive_service, sheets_service=sheets_service
    )


def authorized_service_account_credentials(
    b64_encoded_service_account_credentials: str,
) -> service_account.Credentials:
    SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/userinfo.email",
    ]
    service_account_credentials = base64.b64decode(
        b64_encoded_service_account_credentials
    ).decode("utf-8")
    json_acct_info = json.loads(service_account_credentials)
    credentials = service_account.Credentials.from_service_account_info(json_acct_info)
    scoped_credentials = credentials.with_scopes(SCOPES)

    return scoped_credentials


def authorized_user_credentials(
    access_token: str,
) -> user_credentials.Credentials:
    return user_credentials.Credentials(access_token)
