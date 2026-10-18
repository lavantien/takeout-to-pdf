import argparse
import base64
import html
import mailbox
import os
import sys
from datetime import timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup
from tqdm import tqdm
from weasyprint import HTML

DEFAULT_MBOX = "emails.mbox"
DEFAULT_PDF = "emails_combined.pdf"

HTML_HEAD = """
<html>
    <head>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; }
            .email { margin: 2rem 0; padding: 1rem; border: 1px solid #eee; }
            .email h3 { color: #333; margin: 0 0 0.5rem; }
            .meta { color: #666; font-size: 0.9rem; }
            .body {
                white-space: pre-wrap;
                margin: 1rem 0;
                padding: 1rem;
                background: #f9f9f9;
                border-radius: 4px;
            }
            .images { margin-top: 1rem; }
            img {
                max-width: 300px;
                height: auto;
                margin: 0.5rem;
                border: 1px solid #ddd;
                padding: 2px;
            }
        </style>
    </head>
    <body>
"""

HTML_TAIL = """
    </body>
</html>
"""


def decode_mime(text: str) -> str:
    decoded = []
    for part, encoding in decode_header(text or ""):
        if isinstance(part, bytes):
            try:
                decoded_part = part.decode(encoding or "utf-8", errors="replace")
            except (UnicodeDecodeError, LookupError):
                decoded_part = part.decode("latin-1", errors="replace")
            decoded.append(decoded_part)
        else:
            decoded.append(str(part))
    return " ".join(decoded)


def parse_date(raw: str):
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _extract_body_part(message):
    text_part = html_part = None
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                return part, None
            if content_type == "text/html" and html_part is None:
                html_part = part
    elif message.get_content_type() in {"text/plain", "text/html"}:
        return message, None
    return text_part, html_part


def _decode_body(part) -> str:
    payload = part.get_payload(decode=True)
    try:
        charset = part.get_content_charset("utf-8")
        body = payload.decode(charset, errors="replace")
    except (UnicodeDecodeError, LookupError):
        return payload.decode("latin-1", errors="replace").strip()
    if part.get_content_type() == "text/html":
        return BeautifulSoup(body, "html.parser").get_text(
            separator="\n", strip=True
        )
    return body.strip()


def _extract_images(message) -> list[dict]:
    images = []
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_maintype() != "image":
                continue
            data = part.get_payload(decode=True)
            if data:
                images.append(
                    {
                        "mime_type": part.get_content_type(),
                        "data": base64.b64encode(data).decode("ascii"),
                    }
                )
    return images


def process_email(message) -> dict:
    text_part, html_part = _extract_body_part(message)
    target_part = text_part or html_part
    body = "[No content available]"
    if target_part:
        body = _decode_body(target_part) or "[Empty content]"
    return {
        "date": parse_date(message["date"]),
        "from": decode_mime(message["from"]) or "Unknown Sender",
        "subject": decode_mime(message["subject"]) or "No Subject",
        "body": body,
        "images": _extract_images(message),
    }


def render_email(index: int, email_data: dict) -> str:
    images_html = "".join(
        f'<img src="data:{img["mime_type"]};base64,{img["data"]}" alt="Email image">'
        for img in email_data["images"]
    )
    date_str = (
        email_data["date"].strftime("%Y-%m-%d %H:%M:%S")
        if email_data["date"]
        else "Unknown date"
    )
    return f"""
    <div class="email">
        <h3>Email {index}</h3>
        <div class="meta">
            <div><strong>From:</strong> {html.escape(email_data["from"])}</div>
            <div><strong>Date:</strong> {date_str}</div>
            <div><strong>Subject:</strong> {html.escape(email_data["subject"])}</div>
        </div>
        <div class="body">{html.escape(email_data["body"])}</div>
        <div class="images">{images_html}</div>
    </div>
    """


def build_document(emails: list[dict]) -> str:
    cards = [
        render_email(index, email_data)
        for index, email_data in enumerate(
            tqdm(emails, desc="Building HTML"), start=1
        )
    ]
    return HTML_HEAD + "\n".join(cards) + HTML_TAIL


def load_emails(mbox_path: str) -> list[dict]:
    print(f"Loading and processing emails from {mbox_path}...")
    box = mailbox.mbox(mbox_path)
    emails = [process_email(message) for message in tqdm(box, desc="Processing emails")]
    box.close()
    dated = sorted(
        (email_data for email_data in emails if email_data["date"]),
        key=lambda email_data: email_data["date"],
    )
    undated = [email_data for email_data in emails if not email_data["date"]]
    return dated + undated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="convert a Google Takeout Gmail mbox into one combined pdf"
    )
    parser.add_argument(
        "-i", "--input", default=DEFAULT_MBOX, help="path to the mbox file"
    )
    parser.add_argument(
        "-o", "--output", default=DEFAULT_PDF, help="path to the output pdf"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not os.path.isfile(args.input):
        sys.exit(f"error: mbox not found: {args.input}")
    output_dir = os.path.dirname(os.path.abspath(args.output))
    if not os.path.isdir(output_dir):
        sys.exit(f"error: output directory not found: {output_dir}")
    emails = load_emails(args.input)
    if not emails:
        sys.exit(f"error: no messages found in {args.input}")
    document = build_document(emails)
    print("Generating PDF...")
    HTML(string=document).write_pdf(args.output)
    print(f"\nSuccessfully created {args.output} with {len(emails)} emails!")


if __name__ == "__main__":
    main()
