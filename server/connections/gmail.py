"""Gmail over IMAP with an app password: search with Gmail's own syntax, read a message, and -
through the approval gate - leave a draft in your Drafts folder. Nothing is ever sent.

An app password (Google Account > Security > 2-Step Verification > App passwords) rather than a
Google sign-in: signing in through Google needs a registered developer app, and Jarvis has no
server to register. The password only opens mail, and you can revoke it from the same page.

Python's own imaplib and email - no extra dependency. Each call opens its own connection; there is
nothing to keep alive between questions.
"""

from __future__ import annotations

import email
import email.policy
import imaplib
import re
import time
from email.message import EmailMessage, Message

HOST = "imap.gmail.com"
ALL_MAIL = '"[Gmail]/All Mail"'
DRAFTS = '"[Gmail]/Drafts"'
BODY_CHARS = 6000
SNIPPET_CHARS = 160


class GmailError(RuntimeError):
    pass


def _text(message: Message) -> str:
    """The readable body: the plain-text part if there is one, else the HTML with tags removed."""
    part = (
        message.get_body(preferencelist=("plain", "html"))
        if isinstance(message, EmailMessage)
        else None
    )
    if part is None:
        return ""
    body = str(part.get_content())
    if part.get_content_type() == "text/html":
        body = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)
        body = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", body)).strip()


def summarize(uid: str, raw: bytes, snippet: bool = True) -> str:
    message = email.message_from_bytes(raw, policy=email.policy.default)
    sender, subject = message.get("From", ""), message.get("Subject", "(no subject)")
    head = f"[{uid}] {message.get('Date', '')} | From: {sender} | {subject}"
    body = _text(message)
    if snippet:
        return f"{head}\n  {body[:SNIPPET_CHARS].replace(chr(10), ' ')}"
    return f"{head}\nTo: {message.get('To', '')}\n\n{body[:BODY_CHARS]}"


class Gmail:
    def __init__(self, address: str, app_password: str) -> None:
        self.address = address
        self._password = app_password.replace(" ", "")

    def _open(self, mailbox: str = ALL_MAIL, readonly: bool = True) -> imaplib.IMAP4_SSL:
        try:
            imap = imaplib.IMAP4_SSL(HOST, timeout=20)
            imap.login(self.address, self._password)
        except imaplib.IMAP4.error as exc:
            raise GmailError(
                "Gmail refused the sign-in. Check the address and use an app password, not your "
                "normal password."
            ) from exc
        except OSError as exc:
            raise GmailError(f"Couldn't reach Gmail ({exc}).") from exc
        status, _ = imap.select(mailbox, readonly=readonly)
        if status != "OK":
            imap.logout()
            raise GmailError(
                f"Gmail has no {mailbox} folder (is IMAP turned on in Gmail settings?)."
            )
        return imap

    def verify(self) -> None:
        self._open().logout()

    def search(self, query: str, limit: int = 10) -> str:
        """Gmail's own search syntax: `from:bank newer_than:7d`, `is:unread`, `subject:invoice`."""
        imap = self._open()
        try:
            status, data = imap.uid("SEARCH", "X-GM-RAW", f'"{query.replace(chr(34), "")}"')
            if status != "OK":
                raise GmailError("Gmail could not run that search.")
            uids = data[0].split()[-limit:][::-1]
            out = []
            for uid in uids:
                status, parts = imap.uid("FETCH", uid, "(BODY.PEEK[])")
                raw = next((p[1] for p in parts if isinstance(p, tuple)), b"")
                out.append(summarize(uid.decode(), raw))
            return "\n".join(out) or "No messages matched."
        finally:
            imap.logout()

    def read(self, uid: str) -> str:
        imap = self._open()
        try:
            status, parts = imap.uid("FETCH", uid, "(BODY.PEEK[])")
            raw = next((p[1] for p in parts if isinstance(p, tuple)), None)
            if status != "OK" or not raw:
                raise GmailError(f"No message {uid}. Search again for its number.")
            return summarize(uid, raw, snippet=False)
        finally:
            imap.logout()

    def draft(self, to: str, subject: str, body: str) -> str:
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self.address, to, subject
        message.set_content(body)
        imap = self._open(DRAFTS, readonly=False)
        try:
            when = imaplib.Time2Internaldate(time.time())
            status, _ = imap.append(DRAFTS, "(\\Draft)", when, message.as_bytes())
            if status != "OK":
                raise GmailError("Gmail did not accept the draft.")
            return f"Draft to {to} saved in Gmail Drafts. It has not been sent."
        finally:
            imap.logout()
