"""
Work Ops Module — Outlook, Teams, SharePoint, DataSync automation.

Merged from: outlook_teams_scraper, sharepoint_downloader, datasync_automation.
"""

import logging
from typing import Any, Dict, List

from core.agents.tools import get_registry, tool

logger = logging.getLogger(__name__)


@tool(name="extract_emails", description="Extract emails from Outlook using browser automation", module="work_ops")
def extract_emails(folder: str = "Inbox", limit: int = 20, filter_sender: str = "") -> Dict:
    """Extract emails from Outlook via Playwright browser automation."""
    try:
        from playwright.sync_api import sync_playwright
        emails = []
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://outlook.office.com/mail/" + folder.lower())
            page.wait_for_timeout(3000)
            items = page.query_selector_all('[role="option"]')
            for item in items[:limit]:
                subject = item.query_selector('[data-conversation-title]')
                sender = item.query_selector('[title]')
                if subject:
                    email_data = {
                        "subject": subject.get_attribute("data-conversation-title") or subject.inner_text(),
                        "sender": sender.get_attribute("title") if sender else "",
                    }
                    if filter_sender and filter_sender.lower() not in email_data["sender"].lower():
                        continue
                    emails.append(email_data)
        return {"count": len(emails), "emails": emails}
    except Exception as e:
        return {"error": str(e), "hint": "Make sure Playwright is installed and Outlook is open in browser"}


@tool(name="extract_teams_messages", description="Extract messages from Microsoft Teams channels", module="work_ops")
def extract_teams_messages(channel: str = "", limit: int = 50) -> Dict:
    """Extract Teams messages via browser automation."""
    try:
        from playwright.sync_api import sync_playwright
        messages = []
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()
            page.goto("https://teams.microsoft.com/")
            page.wait_for_timeout(3000)
            msg_elements = page.query_selector_all('[data-tid="message-body-content"]')
            for el in msg_elements[:limit]:
                messages.append({"content": el.inner_text()[:500]})
        return {"count": len(messages), "messages": messages}
    except Exception as e:
        return {"error": str(e), "hint": "Make sure Teams is open in browser"}


@tool(name="download_sharepoint_files", description="Download files from SharePoint document libraries", module="work_ops")
def download_sharepoint_files(list_name: str = "", output_dir: str = "", limit: int = 100) -> Dict:
    """Download files from SharePoint."""
    from config.settings import get_settings
    import httpx
    import os

    settings = get_settings()
    site_url = settings.urls.get("sharepoint_base", "")
    output = output_dir or str(settings.paths.output_dir / "sharepoint_downloads")
    os.makedirs(output, exist_ok=True)

    return {
        "status": "ready",
        "site_url": site_url,
        "output_dir": output,
        "note": "SharePoint downloads require browser auth — use Playwright for authenticated access",
    }


@tool(name="datasync_status", description="Check DataSync automation status", module="work_ops")
def datasync_status() -> Dict:
    """Check the status of data synchronization jobs."""
    return {
        "status": "available",
        "pipelines": [
            "FHIR-10G", "FHIR-11X", "LEAP-10G", "LEAP-11X", "UDS+",
        ],
        "note": "Connect to database to check actual sync status",
    }


def register():
    return {
        "name": "work_ops",
        "description": "Work operations — Outlook email extraction, Teams messages, SharePoint downloads, DataSync",
        "version": "2.0.0",
        "tools": ["extract_emails", "extract_teams_messages", "download_sharepoint_files", "datasync_status"],
        "routes": [
            {"method": "GET", "path": "/work/emails", "handler": "extract_emails"},
            {"method": "GET", "path": "/work/teams", "handler": "extract_teams_messages"},
            {"method": "POST", "path": "/work/sharepoint", "handler": "download_sharepoint_files"},
            {"method": "GET", "path": "/work/datasync", "handler": "datasync_status"},
        ],
    }
