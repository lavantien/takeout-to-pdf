import base64
import mailbox
import os
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import format_datetime

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNg"
    "YGBgAAAABQABh6FO1AAAAABJRU5ErkJggg=="
)


def make_msg(from_, subject, when=None):
    msg = EmailMessage()
    msg["From"] = from_
    msg["To"] = "me@example.com"
    msg["Subject"] = subject
    if when is not None:
        msg["Date"] = when
    return msg


def main():
    if os.path.exists("emails.mbox"):
        os.remove("emails.mbox")
    box = mailbox.mbox("emails.mbox", create=True)
    box.lock()
    try:
        third = make_msg("third@example.com", "plain body wins")
        third["Date"] = format_datetime(
            datetime(2021, 3, 3, 12, 0, 0, tzinfo=timezone.utc)
        )
        third.set_content("dated third, plain text")

        first = make_msg("first@example.com", "html body stripped")
        first["Date"] = format_datetime(
            datetime(2021, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        )
        first.set_content("html fallback text")
        first.add_alternative(
            "<div><p>dated first, <b>html</b> body</p></div>", subtype="html"
        )

        second = make_msg("second@example.com", "embedded image")
        second["Date"] = format_datetime(
            datetime(2021, 2, 2, 10, 30, 0, tzinfo=timezone.utc)
        )
        second.set_content("dated second, carries a png")
        second.add_attachment(
            PNG_1X1, maintype="image", subtype="png", filename="dot.png"
        )

        markup = make_msg("markup@example.com", "Shiny <b>subject</b> & more")
        markup["Date"] = format_datetime(
            datetime(2021, 4, 4, 8, 0, 0, tzinfo=timezone.utc)
        )
        markup.set_content("markup sender, safe subject")

        htmlonly = make_msg("htmlonly@example.com", "html only body")
        htmlonly["Date"] = format_datetime(
            datetime(2021, 5, 5, 16, 0, 0, tzinfo=timezone.utc)
        )
        htmlonly.set_content(
            "<div><p>dated fifth, <i>html only</i> body</p></div>", subtype="html"
        )

        minuszero = make_msg("minuszero@example.com", "naive timezone")
        minuszero["Date"] = "Tue, 06 Jul 2021 06:06:06 -0000"
        minuszero.set_content("naive -0000 date, sorts with the dated")

        bad_date = make_msg("baddate@example.com", "unparsable date")
        bad_date["Date"] = "definitely not a date"
        bad_date.set_content("invalid date header, lands with the undated")

        undated = make_msg("nobody@example.com", "no date header")
        undated.set_content("undated, goes last")

        for msg in (
            third,
            first,
            second,
            markup,
            htmlonly,
            minuszero,
            bad_date,
            undated,
        ):
            box.add(msg)
    finally:
        box.unlock()
        box.close()
    print("wrote emails.mbox with 8 messages")


if __name__ == "__main__":
    main()
