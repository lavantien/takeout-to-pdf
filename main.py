import mailbox
import os
import base64
import html
from email.header import decode_header
from email.utils import parsedate_to_datetime
from weasyprint import HTML
from tqdm import tqdm
from bs4 import BeautifulSoup

# Configuration
MBOX_PATH = "emails.mbox"
OUTPUT_PDF = "emails_combined.pdf"
TEMP_IMG_DIR = "temp_images"
os.makedirs(TEMP_IMG_DIR, exist_ok=True)


def decode_mime(text: str) -> str:
    """Decode MIME-encoded header strings with proper exception handling"""
    decoded = []
    for part, encoding in decode_header(text or ""):
        if isinstance(part, bytes):
            try:
                decoded_part = part.decode(
                    encoding or "utf-8", errors="replace")
            except (UnicodeDecodeError, LookupError) as decode_error:
                try:
                    decoded_part = part.decode("latin-1", errors="replace")
                except Exception as fallback_error:
                    decoded_part = f"[Decode Error: {fallback_error}]"
            decoded.append(decoded_part)
        else:
            decoded.append(str(part))
    return " ".join(decoded)


def _extract_body_part(message) -> tuple:
    """Extract text/plain or text/html body part from email"""
    text_part = html_part = None
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                text_part = part
                break  # Prioritize plain text
            elif content_type == "text/html":
                html_part = part
    else:
        if message.get_content_type() in {"text/plain", "text/html"}:
            return (message, None)
    return (text_part, html_part)


def _decode_body(part) -> str:
    """Decode email body content with proper error handling"""
    try:
        payload = part.get_payload(decode=True)
        charset = part.get_content_charset("utf-8")
        body_content = payload.decode(charset, errors="replace")

        if part.get_content_type() == "text/html":
            soup = BeautifulSoup(body_content, "html.parser")
            return soup.get_text(separator="\n", strip=True)
        return body_content.strip()

    except (UnicodeDecodeError, LookupError):
        return payload.decode("latin-1", errors="replace").strip()
    except Exception as e:
        return f"[Body decode error: {str(e)}]"


def _extract_images(message) -> list:
    """Extract embedded images with error handling"""
    images = []
    try:
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_maintype() == "image":
                    try:
                        image_data = part.get_payload(decode=True)
                        if image_data:
                            images.append({
                                "mime_type": part.get_content_type(),
                                "data": base64.b64encode(image_data).decode("ascii")
                            })
                    except Exception as image_error:
                        images.append({
                            "mime_type": "text/plain",
                            "data": f"Image error: {str(image_error)}"
                        })
    except Exception as general_error:
        images.append({
            "mime_type": "text/plain",
            "data": f"Image extraction failed: {str(general_error)}"
        })
    return images


def process_email(message):
    """Process email with reduced complexity through helper functions"""
    email_data = {
        "date": parsedate_to_datetime(message["date"]) if message["date"] else None,
        "from": decode_mime(message["from"]) or "Unknown Sender",
        "subject": decode_mime(message["subject"]) or "No Subject",
        "body": "[No content available]",
        "images": []
    }

    # Body extraction
    text_part, html_part = _extract_body_part(message)
    target_part = text_part or html_part
    if target_part:
        email_data["body"] = _decode_body(target_part) or "[Empty content]"

    # Image extraction
    email_data["images"] = _extract_images(message)

    return email_data


# Load and sort emails
print("Loading and processing emails...")
mbox = mailbox.mbox(MBOX_PATH)
emails = []
for message in tqdm(mbox, desc="Processing emails"):
    emails.append(process_email(message))
mbox.close()

# Sort by date (oldest first)
emails = sorted(
    [e for e in emails if e["date"]],
    key=lambda x: x["date"]
) + [e for e in emails if not e["date"]]

# Build HTML content
html_template = """
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

for idx, email in enumerate(tqdm(emails, desc="Building HTML")):
    images_html = "".join(
        f'<img src="data:{img["mime_type"]};base64,{
            img["data"]}" alt="Email image">'
        for img in email["images"]
    )

    date_str = email["date"].strftime(
        "%Y-%m-%d %H:%M:%S") if email["date"] else "Unknown date"

    html_template += f"""
    <div class="email">
        <h3>Email {idx+1}</h3>
        <div class="meta">
            <div><strong>From:</strong> {email['from']}</div>
            <div><strong>Date:</strong> {date_str}</div>
            <div><strong>Subject:</strong> {email['subject']}</div>
        </div>
        <div class="body">{html.escape(email['body'])}</div>
        <div class="images">{images_html}</div>
    </div>
    """

html_template += "</body></html>"

# Generate PDF
print("Generating PDF...")
HTML(string=html_template).write_pdf(OUTPUT_PDF)

# Cleanup
print("Cleaning temporary files...")
for f in os.listdir(TEMP_IMG_DIR):
    os.remove(os.path.join(TEMP_IMG_DIR, f))
os.rmdir(TEMP_IMG_DIR)

print(f"\nSuccessfully created {OUTPUT_PDF} with {len(emails)} emails!")
