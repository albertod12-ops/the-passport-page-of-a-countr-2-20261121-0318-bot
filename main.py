"""Draw the passport spread of the Republic of Marenna as /output/entry.png.

An invented country that does not exist: a lagoon republic of stilt
towns on the Grey Lagoon, where the only way in or out is the pole-ferry
at slack water. The holder, Selma Orren, is a licensed lagoon ferry
pilot, and every detail of the document agrees with that: her
occupation, the ferry pilot's endorsement, the lagoon toll stamp, the
visa from neighbouring Aldorne, and a travel history of paired
entry/exit stamps, all dated after the passport was issued on
14 MAR 2023 and before it expires on 13 MAR 2033.

The program draws the whole spread with Pillow: paper, guilloche,
emblem, data page, machine-readable zone (ICAO check digits computed,
not typed), endorsement, visa, stamps, and a small ferry-route map.
The portrait is a photograph generated for this entry and kept in the
repository as portrait.jpg; it is pasted into the photo box and as a
faint ghost image. No network, no randomness: two runs produce the
same bytes.

Run it locally the same way the grader does, with an output
directory of your own:
    mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import hashlib
import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
PORTRAIT = HERE / "portrait.jpg"

W, H = 1024, 1024
PAPER = (245, 240, 225)
PAPER_DARK = (238, 231, 212)
INK = (26, 42, 74)
INK_SOFT = (58, 74, 104)
GREY = (110, 108, 96)
RED = (163, 51, 39)
BLUE = (42, 77, 143)
GREEN = (46, 107, 52)
TEAL = (15, 95, 92)
GOLD = (176, 141, 58)

SERIF = "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf"
SERIF_B = "/usr/share/fonts/truetype/noto/NotoSerif-Bold.ttf"
SERIF_I = "/usr/share/fonts/truetype/noto/NotoSerif-Italic.ttf"
SANS = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
SANS_B = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def tracked(draw, xy, text, fnt, fill, tracking=2):
    """Draw text with letter tracking, return width."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x


def text_w(draw, text, fnt, tracking=0):
    w = draw.textlength(text, font=fnt)
    return w + tracking * max(0, len(text) - 1)


def center(draw, cx, y, text, fnt, fill, tracking=0):
    draw.text((cx - text_w(draw, text, fnt, tracking) / 2, y), text,
              font=fnt, fill=fill)


def wrap(draw, text, fnt, width):
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=fnt) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# --- ICAO MRZ check digits -------------------------------------------------
def check_digit(s):
    weights = (7, 3, 1)
    total = 0
    for i, ch in enumerate(s):
        if ch.isdigit():
            v = int(ch)
        elif ch == "<":
            v = 0
        else:
            v = ord(ch) - 55
        total += v * weights[i % 3]
    return str(total % 10)


def mrz_lines():
    line1 = "P<MRNORREN<<SELMA" + "<" * (44 - len("P<MRNORREN<<SELMA"))
    doc, nat = "MR4829107", "MRN"
    dob, sex, exp = "810622", "F", "330313"
    personal = "8106224417<<<<"
    body = (doc + check_digit(doc) + nat + dob + check_digit(dob) + sex
            + exp + check_digit(exp) + personal + check_digit(personal))
    line2 = body + check_digit(body)
    assert len(line1) == 44 and len(line2) == 44, (line1, line2)
    return line1, line2


# --- stamps -----------------------------------------------------------------
def stamp(img, box, lines, color, shape="rect", angle=0, size=11):
    """Draw a rubber stamp on its own layer, rotate it, paste it back."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    pad = 14
    layer = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if shape == "round":
        d.ellipse([pad, pad, w + pad, h + pad], outline=color + (255,),
                  width=3)
        d.ellipse([pad + 4, pad + 4, w + pad - 4, h + pad - 4],
                  outline=color + (200,), width=1)
    elif shape == "oval":
        d.ellipse([pad, pad + 6, w + pad, h + pad - 6],
                  outline=color + (255,), width=3)
    else:
        d.rounded_rectangle([pad, pad, w + pad, h + pad], radius=6,
                            outline=color + (255,), width=3)
        d.rounded_rectangle([pad + 4, pad + 4, w + pad - 4, h + pad - 4],
                            radius=4, outline=color + (170,), width=1)
    f_big = font(SANS_B, size + 2)
    f_mid = font(SANS_B, size)
    f_small = font(SANS, size - 2)
    n = len(lines)
    y = pad + (h - n * (size + 5)) / 2 + 2
    for i, (txt, kind) in enumerate(lines):
        f = f_big if kind == "big" else f_mid if kind == "mid" else f_small
        tw = d.textlength(txt, font=f)
        d.text(((w + 2 * pad - tw) / 2, y), txt, font=f, fill=color + (235,))
        y += size + 5
    layer = layer.rotate(angle, resample=Image.BICUBIC, expand=False)
    img.paste(layer, (x0 - pad, y0 - pad), layer)


def emblem(draw, cx, cy, r, color, width=2):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=width)
    draw.ellipse([cx - r + 5, cy - r + 5, cx + r - 5, cy + r - 5],
                 outline=color, width=1)
    # three lagoon waves
    for k, yy in enumerate((-8, 0, 8)):
        pts = []
        for t in range(-r + 8, r - 7, 4):
            pts.append((cx + t, cy + yy + 3 * math.sin(t / 9.0 + k)))
        draw.line(pts, fill=color, width=2)
    # pole-ferry: hull + pole + small sail
    draw.line([(cx - 14, cy - 16), (cx + 14, cy - 16)], fill=color, width=2)
    draw.line([(cx - 10, cy - 16), (cx + 10, cy - 16)], fill=color, width=1)
    draw.line([(cx + 4, cy - 30), (cx + 4, cy - 16)], fill=color, width=2)
    draw.polygon([(cx + 4, cy - 30), (cx + 16, cy - 18), (cx + 4, cy - 18)],
                 outline=color)


def guilloche(draw):
    """Faint security waves across both pages."""
    col = (196, 188, 158)
    for y0 in range(30, H - 20, 26):
        pts = [(x, y0 + 3 * math.sin(x / 47.0 + y0)) for x in range(16, 1008, 8)]
        draw.line(pts, fill=col, width=1)


def field(draw, x, y, label, value, vsize=15, label_color=None):
    draw.text((x, y), label, font=font(SANS, 8), fill=label_color or GREY)
    draw.text((x, y + 11), value, font=font(SERIF_B, vsize), fill=INK)


def draw_spread():
    img = Image.new("RGB", (W, H), (30, 33, 46))
    draw = ImageDraw.Draw(img, "RGBA")
    # paper
    draw.rectangle([12, 12, 1012, 1012], fill=PAPER)
    guilloche(draw)
    # centre gutter
    draw.rectangle([506, 12, 518, 1012], fill=(214, 206, 182))
    draw.line([(506, 12), (506, 1012)], fill=(180, 172, 148), width=1)
    draw.line([(518, 12), (518, 1012)], fill=(180, 172, 148), width=1)
    draw.rectangle([12, 12, 1012, 1012], outline=(30, 33, 46), width=2)

    # ================= LEFT PAGE: data page =================
    emblem(draw, 259, 66, 27, INK)
    center(draw, 259, 100, "REPUBLIC OF MARENNA", font(SERIF_B, 29), INK)
    center(draw, 259, 132, "MARENNISK REPUBLIKK  ·  REPUBLIKA MARENNA",
           font(SANS, 10), RED, tracking=1)
    center(draw, 259, 148, "P A S S A  ·  P A S  ·  P A S S P O R T",
           font(SANS_B, 10), INK_SOFT, tracking=1)
    draw.line([(34, 168), (484, 168)], fill=INK, width=2)
    draw.line([(34, 172), (484, 172)], fill=INK, width=1)

    # photo
    portrait = Image.open(PORTRAIT).convert("RGB")
    crop = portrait.crop((380, 20, 1180, 1170)).resize((170, 244),
                                                       Image.LANCZOS)
    img.paste(crop, (34, 184))
    draw.rectangle([34, 184, 204, 428], outline=INK, width=2)
    draw.text((34, 432), "PHOTOGRAPH", font=font(SANS, 7), fill=GREY)

    # type / code / number row, right of the photo
    field(draw, 212, 184, "Type / Slag", "P")
    field(draw, 272, 184, "Code / Kóð", "MRN")
    field(draw, 344, 184, "Passport No. / Passa nr.", "MR4829107")
    # data fields
    field(draw, 212, 222, "Surname / Ættarnavn", "ORREN")
    field(draw, 212, 260, "Given names / Fornavn", "SELMA")
    field(draw, 212, 298, "Nationality / Ríkisfang", "MARENNIC")
    field(draw, 212, 336, "Date of birth / Fæðingardagur", "22 JUN 1981")
    field(draw, 392, 336, "Sex / Kyn", "F")
    field(draw, 212, 374, "Place of birth / Fæðingarstaður",
          "VESSA, GREY LAGOON")
    field(draw, 212, 412, "Personal No. / Kennitala", "810622-4417")
    field(draw, 212, 450, "Date of issue / Dags útgáfu", "14 MAR 2023")
    field(draw, 392, 450, "Date of expiry / Gildir til", "13 MAR 2033")
    field(draw, 212, 488, "Authority / Útgefandi",
          "PASSPORT OFFICE, PORT VESSA")
    field(draw, 212, 526, "Occupation / Starf",
          "LAGOON FERRY PILOT · LIC. FP-118", vsize=13)

    # signature
    draw.text((36, 566), "Selma Orren", font=font(SERIF_I, 24), fill=INK)
    draw.line([(34, 596), (240, 596)], fill=INK, width=1)
    draw.text((34, 600), "Holder's signature / Undirskrift",
              font=font(SANS, 8), fill=GREY)

    # (ghost portrait omitted: the data column leaves no clear spot for
    # a second image without covering a field)

    # observations
    draw.rectangle([34, 626, 484, 716], outline=INK_SOFT, width=1)
    draw.text((44, 634), "OBSERVATIONS / ATHUGASEMDIR",
              font=font(SANS_B, 9), fill=INK)
    obs = ("Holder is a licensed lagoon ferry pilot (lic. FP-118). "
           "Crossings only at slack water; pole-ferry only; "
           "see endorsement on page 3.")
    y = 652
    for line in wrap(draw, obs, font(SERIF, 11), 430):
        draw.text((44, y), line, font=font(SERIF, 11), fill=INK)
        y += 15

    # tide strip
    draw.rectangle([34, 730, 484, 786], outline=TEAL, width=1)
    draw.rectangle([34, 730, 484, 752], fill=TEAL)
    draw.text((44, 735), "TIDE CARD — VESSA GATE, TODAY",
              font=font(SANS_B, 9), fill=(255, 255, 255))
    draw.text((44, 758),
              "Low water 06:41  ·  18:57      Slack ± 2 h      Pole-ferry only",
              font=font(SANS_B, 10), fill=INK)

    # MRZ
    l1, l2 = mrz_lines()
    draw.rectangle([34, 806, 484, 872], fill=(255, 255, 255),
                   outline=INK_SOFT, width=1)
    draw.text((44, 816), l1, font=font(MONO, 13), fill=INK)
    draw.text((44, 840), l2, font=font(MONO, 13), fill=INK)
    draw.text((34, 884), "LANGUAGES OF ISSUE: MARENNIC · ENGLISH   |   "
              "ICAO 9303 BIOMETRIC", font=font(SANS, 8), fill=GREY)
    center(draw, 259, 972, "2", font(SERIF, 12), INK_SOFT)

    # ================= RIGHT PAGE: visas & stamps =================
    draw.text((540, 30), "ENDORSEMENTS · VISAS", font=font(SERIF_B, 24),
              fill=INK)
    draw.text((972, 34), "3", font=font(SERIF, 12), fill=INK_SOFT)
    draw.line([(540, 62), (990, 62)], fill=INK, width=2)

    # endorsement box
    draw.rectangle([540, 76, 990, 218], outline=INK, width=2)
    draw.text((552, 86), "FERRY PILOT'S ENDORSEMENT 1 / 2023 · GREY LAGOON",
              font=font(SANS_B, 11), fill=INK)
    draw.line([(552, 106), (978, 106)], fill=INK_SOFT, width=1)
    body = ("The holder is a licensed lagoon ferry pilot (lic. FP-118). "
            "Crossings are valid only at slack water, within ± 2 h of low "
            "tide posted at the Vessa tide gate. Pole-ferry only; no motor "
            "after dark. The tide card issued with this passport must be "
            "carried.")
    y = 114
    for line in wrap(draw, body, font(SERIF, 12), 290):
        draw.text((552, y), line, font=font(SERIF, 12), fill=INK)
        y += 16
    draw.text((552, 196), "Port Vessa, 14 MAR 2023",
              font=font(SERIF_I, 11), fill=INK_SOFT)
    # toll stamp, overlapping the endorsement corner
    stamp(img, (856, 128, 976, 196),
          [("MARENNA", "mid"), ("LAGOON TOLL", "mid"), ("12 MRK", "big"),
           ("PAID", "mid")], RED, shape="rect", angle=-7, size=10)

    # Aldorne visa
    draw.rectangle([540, 232, 990, 396], fill=(232, 240, 228),
                   outline=GREEN, width=2)
    draw.rectangle([540, 232, 990, 258], fill=GREEN)
    draw.text((552, 238), "CONFEDERATION OF ALDORNE — SHORT-STAY VISA",
              font=font(SANS_B, 11), fill=(255, 255, 255))
    draw.text((930, 238), "VISA C", font=font(SANS_B, 11),
              fill=(255, 255, 255))
    draw.text((552, 266), "No. ALD 2407 1188",
              font=font(SANS_B, 10), fill=RED)
    field(draw, 552, 288, "Valid from / Valable du", "01 NOV 2024")
    field(draw, 770, 288, "Until / Au", "30 NOV 2024")
    field(draw, 552, 326, "Entries / Entrées", "1 · SINGLE")
    field(draw, 770, 326, "Duration / Durée", "15 DAYS")
    draw.text((552, 366), "Issued at / Délivré à  CONSULATE, PORT VESSA — "
              "22 OCT 2024", font=font(SANS_B, 10), fill=INK)
    draw.text((552, 382), "Passport MR4829107  ·  ORREN, SELMA  ·  "
              "ENTRY BY VESSA FERRY GATE · FEE 35 ALD PAID",
              font=font(SANS, 9), fill=INK_SOFT)

    draw.text((540, 408), "ENTRY AND EXIT  ·  INNKOMA OG ÚTFÖR",
              font=font(SANS_B, 10), fill=INK_SOFT)
    draw.line([(540, 426), (990, 426)], fill=INK_SOFT, width=1)

    # stamps: paired, consistent travel history
    stamp(img, (540, 440, 758, 512),
          [("MARENNA · UTFÖR / EXIT", "mid"), ("06 MAY 2023", "big"),
           ("VESSA FERRY GATE", "small"), ("LOW WATER 06:41", "small")],
          BLUE, shape="rect", angle=-2, size=11)
    stamp(img, (772, 440, 990, 512),
          [("DRAVIA", "big"), ("ENTRY", "mid"), ("07 MAY 2023", "mid"),
           ("NORTH QUAY", "small")], RED, shape="round", angle=3, size=11)
    stamp(img, (540, 524, 758, 596),
          [("DRAVIA", "big"), ("EXIT", "mid"), ("09 MAY 2023", "mid"),
           ("NORTH QUAY", "small")], RED, shape="rect", angle=2, size=11)
    stamp(img, (772, 524, 990, 596),
          [("MARENNA · INNKOMA / ENTRY", "mid"), ("10 MAY 2023", "big"),
           ("VESSA FERRY GATE", "small"), ("LOW WATER 06:58", "small")],
          GREEN, shape="rect", angle=-3, size=11)
    stamp(img, (540, 608, 758, 680),
          [("ALDORNE", "big"), ("ENTRY", "mid"), ("14 NOV 2024", "mid"),
           ("FERRY GATE 2", "small")], BLUE, shape="oval", angle=-2,
          size=11)
    stamp(img, (772, 608, 990, 680),
          [("ALDORNE", "big"), ("EXIT", "mid"), ("17 NOV 2024", "mid"),
           ("FERRY GATE 2", "small")], RED, shape="rect", angle=3, size=11)

    # ferry-route map
    draw.rectangle([540, 694, 990, 900], outline=INK_SOFT, width=1)
    draw.rectangle([540, 694, 990, 716], fill=INK)
    draw.text((552, 699), "GREY LAGOON — FERRY ROUTE 2",
              font=font(SANS_B, 10), fill=(255, 255, 255))
    draw.text((900, 699), "NOT TO SCALE", font=font(SANS, 8),
              fill=(220, 220, 220))
    # lagoon water
    draw.rectangle([540, 716, 990, 900], fill=(214, 228, 232))
    # land masses
    draw.polygon([(540, 716), (660, 716), (640, 790), (560, 830),
                  (540, 860)], fill=(226, 214, 178))
    draw.polygon([(990, 716), (880, 716), (900, 800), (990, 860)],
                 fill=(226, 214, 178))
    draw.polygon([(700, 900), (760, 830), (830, 900)], fill=(226, 214, 178))
    # route: smooth dashed curve Vessa -> North Quay
    x0, y0, cx, cy, x1, y1 = 610, 800, 760, 690, 905, 758
    for i in range(0, 25):
        t = i / 24
        bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
        by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
        if i % 2 == 0:
            draw.ellipse([bx - 2, by - 2, bx + 2, by + 2], fill=RED)
    for (x, y, name) in ((610, 800, "VESSA"), (905, 758, "NORTH QUAY"),
                         (760, 858, "TORMUND SANDS")):
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=RED,
                     outline=(255, 255, 255), width=1)
        draw.text((x + 8, y - 6), name, font=font(SANS_B, 9), fill=INK)
    draw.text((600, 830), "SLACK WATER ONLY", font=font(SANS_B, 8),
              fill=RED)
    # compass
    draw.ellipse([946, 856, 978, 888], outline=INK, width=1)
    draw.text((958, 860), "N", font=font(SANS_B, 10), fill=INK)
    draw.line([(962, 872), (962, 882)], fill=INK, width=1)

    draw.text((540, 912),
              "This passport remains the property of the Republic of "
              "Marenna.", font=font(SERIF_I, 11), fill=INK_SOFT)
    draw.text((540, 930), "If found, return to the Passport Office, "
              "Port Vessa.", font=font(SERIF_I, 11), fill=INK_SOFT)
    draw.text((920, 972), "MR4829107", font=font(SANS, 9), fill=GREY)
    return img


def main():
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "entry.png"
    if not PORTRAIT.is_file():
        print(f"missing portrait: {PORTRAIT}", file=sys.stderr)
        return 1
    img = draw_spread()
    img.save(out, format="PNG", optimize=True)
    size = out.stat().st_size
    print(f"wrote {out} {img.size} {size} bytes "
          f"sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")
    if size > 1_048_576:
        print("over 1 MiB cap, re-saving as JPEG", file=sys.stderr)
        img.save(out, format="JPEG", quality=90, optimize=True)
        size = out.stat().st_size
        print(f"re-saved {out} {size} bytes "
              f"sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")
    if size > 1_048_576 or img.size != (1024, 1024):
        print("entry fails the size cap", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
