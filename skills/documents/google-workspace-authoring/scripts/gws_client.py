#!/usr/bin/env python3
"""Thin auth + batchUpdate helper for Google Slides / Docs / Sheets.

Auth precedence:
  1. GOOGLE_APPLICATION_CREDENTIALS  -> service account (server / CI, no browser)
  2. token.json + credentials.json   -> installed-app OAuth (interactive, first run opens browser)

Deps (Python 3.9 OK):
  pip install google-api-python-client google-auth google-auth-oauthlib

Usage examples:
  python3 gws_client.py new-slides "Q3 Media Plan"          # -> prints presentationId
  python3 gws_client.py new-doc    "Creative Brief"          # -> prints documentId
  python3 gws_client.py new-sheet  "Budget Tracker"          # -> prints spreadsheetId
"""
import json
import os
import sys

SCOPES = [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def get_credentials():
    """Return a google.auth credentials object using SA or OAuth installed-app flow."""
    sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if sa_path and os.path.exists(sa_path):
        from google.oauth2 import service_account
        return service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as fh:
            fh.write(creds.to_json())
    return creds


def service(api, version):
    from googleapiclient.discovery import build
    return build(api, version, credentials=get_credentials())


def batch_update_slides(presentation_id, requests):
    return service("slides", "v1").presentations().batchUpdate(
        presentationId=presentation_id, body={"requests": requests}
    ).execute()


def batch_update_docs(document_id, requests):
    return service("docs", "v1").documents().batchUpdate(
        documentId=document_id, body={"requests": requests}
    ).execute()


def batch_update_sheets(spreadsheet_id, requests):
    return service("sheets", "v4").spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()


def _cli(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, title = argv[1], argv[2]
    if cmd == "new-slides":
        r = service("slides", "v1").presentations().create(body={"title": title}).execute()
        print(r["presentationId"])
    elif cmd == "new-doc":
        r = service("docs", "v1").documents().create(body={"title": title}).execute()
        print(r["documentId"])
    elif cmd == "new-sheet":
        r = service("sheets", "v4").spreadsheets().create(
            body={"properties": {"title": title}}
        ).execute()
        print(r["spreadsheetId"])
    else:
        print("unknown command: %s" % cmd, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv))
