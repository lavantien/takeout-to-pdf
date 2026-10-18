import sys

from pypdf import PdfReader

EXPECTED_ORDER = [
    "first@example.com",
    "second@example.com",
    "third@example.com",
    "markup@example.com",
    "htmlonly@example.com",
    "minuszero@example.com",
    "baddate@example.com",
    "nobody@example.com",
]

EXPECTED_TEXT = [
    "html fallback text",
    "dated second, carries a png",
    "dated third, plain text",
    "Shiny <b>subject</b> & more",
    "dated fifth,",
    "html only",
    "naive -0000 date, sorts with the dated",
    "invalid date header, lands with the undated",
    "undated, goes last",
    "Unknown date",
]


def main():
    reader = PdfReader("emails_combined.pdf")
    text = "\n".join(page.extract_text() for page in reader.pages)

    observed = [
        line.removeprefix("From: ").strip()
        for line in text.splitlines()
        if line.startswith("From: ")
    ]
    if observed != EXPECTED_ORDER:
        print(f"FAIL: sender order wrong\nobserved: {observed}")
        sys.exit(1)

    for needle in EXPECTED_TEXT:
        if needle not in text:
            print(f"FAIL: '{needle}' missing from the pdf text")
            sys.exit(1)

    if "&lt;" in text or "<div>" in text:
        print("FAIL: unescaped or double-escaped html leaked into the pdf")
        sys.exit(1)

    image_count = 0
    for page in reader.pages:
        xobjects = page.get("/Resources", {}).get("/XObject", {})
        for name in xobjects:
            if xobjects[name].get_object().get("/Subtype") == "/Image":
                image_count += 1
    if image_count < 1:
        print("FAIL: no embedded image in the pdf")
        sys.exit(1)

    print(
        f"PASS: {len(reader.pages)} pages, sender order correct, "
        f"all bodies present, markup escaped, {image_count} image(s)"
    )


if __name__ == "__main__":
    main()
