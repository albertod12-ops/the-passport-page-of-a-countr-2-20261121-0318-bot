"""Draw the passport spread of the Kingdom of Zanvara as /output/entry.png.

An invented country that does not exist: a hidden highland kingdom in
the Great Rift highlands, revealed to the world in 2019, whose
solar-lattice technology runs on sunstone, a crystal found nowhere
else. The holder, Amara Ndele, is a licensed solar lattice engineer,
and every detail of the document agrees with that: her occupation,
the solar lattice endorsement, the sunstone levy stamp, the visa from
neighbouring Kessari, and a travel history of paired entry/exit
stamps, all dated after the passport was issued on 09 MAY 2023 and
before it expires on 08 MAY 2033.

The program draws the whole spread with Pillow: paper, guilloche,
emblem, data page, machine-readable zone (ICAO check digits computed,
not typed), endorsement, visa, stamps, and a small sky-rail route
map. The portrait is a photograph generated for this entry and kept
in the repository as portrait.jpg; it is pasted into the photo box.
No network, no randomness: two runs produce the same bytes.

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
ZGREEN = (14, 59, 46)
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
    line1 = "P<ZNVNDELE<<AMARA" + "<" * (44 - len("P<ZNVNDELE<<AMARA"))
    doc, nat = "ZV7391846", "ZNV"
    dob, sex, exp = "900214", "F", "330508"
    personal = "9002145523<<<<"
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
    # sun-disc over the highland peaks
    draw.ellipse([cx - 7, cy - 20, cx + 7, cy - 6], outline=color, width=2)
    for ang in range(0, 360, 45):
        a = math.radians(ang)
        x1 = cx + 10 * math.cos(a)
        y1 = cy - 13 + 10 * math.sin(a)
        x2 = cx + 14 * math.cos(a)
        y2 = cy - 13 + 14 * math.sin(a)
        draw.line([(x1, y1), (x2, y2)], fill=color, width=1)
    # peaks
    draw.polygon([(cx - 18, cy + 12), (cx - 6, cy - 4), (cx + 2, cy + 12)],
                 outline=color)
    draw.polygon([(cx - 2, cy + 12), (cx + 10, cy - 8), (cx + 20, cy + 12)],
                 outline=color)
    draw.line([(cx - 20, cy + 12), (cx + 22, cy + 12)], fill=color, width=2)


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
    center(draw, 259, 100, "KINGDOM OF ZANVARA", font(SERIF_B, 29), INK)
    center(draw, 259, 132, "UFALME WA ZANVARA  ·  KINGDOM OF ZANVARA",
           font(SANS, 10), RED, tracking=1)
    center(draw, 259, 148, "P A S S P O R T",
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
    field(draw, 212, 184, "Type / Aina", "P")
    field(draw, 272, 184, "Code / Msimbo", "ZNV")
    field(draw, 344, 184, "Passport No. / Nambari", "ZV7391846")
    # data fields
    field(draw, 212, 222, "Surname / Jina la ukoo", "NDELE")
    field(draw, 212, 260, "Given names / Majina", "AMARA")
    field(draw, 212, 298, "Nationality / Uraia", "ZANVARAN")
    field(draw, 212, 336, "Date of birth / Tarehe ya kuzaliwa",
          "14 FEB 1990")
    field(draw, 392, 336, "Sex / Jinsia", "F")
    field(draw, 212, 374, "Place of birth / Mahali pa kuzaliwa",
          "TAVARA, ZANVARA")
    field(draw, 212, 412, "Personal No. / Nambari ya kibinafsi",
          "900214-5523")
    field(draw, 212, 450, "Date of issue / Tarehe ya kutolewa", "09 MAY 2023")
    field(draw, 392, 450, "Date of expiry / Muda wake", "08 MAY 2033")
    field(draw, 212, 488, "Authority / Mamlaka",
          "PASSPORT OFFICE, TAVARA")
    field(draw, 212, 526, "Occupation / Kazi",
          "SOLAR LATTICE ENGINEER · GRID LIC. SL-207", vsize=13)

    # signature
    draw.text((36, 566), "Amara Ndele", font=font(SERIF_I, 24), fill=INK)
    draw.line([(34, 596), (240, 596)], fill=INK, width=1)
    draw.text((34, 600), "Holder's signature / Sahihi",
              font=font(SANS, 8), fill=GREY)

    # observations
    draw.rectangle([34, 626, 484, 716], outline=INK_SOFT, width=1)
    draw.text((44, 634), "OBSERVATIONS / MAELEZO",
              font=font(SANS_B, 9), fill=INK)
    obs = ("Holder is a licensed solar lattice engineer (grid lic. "
           "SL-207). Grid access only during daylight sync; sunstone "
           "must not leave the kingdom unsealed; see endorsement on "
           "page 3.")
    y = 652
    for line in wrap(draw, obs, font(SERIF, 11), 430):
        draw.text((44, y), line, font=font(SERIF, 11), fill=INK)
        y += 15

    # grid sync strip
    draw.rectangle([34, 730, 484, 786], outline=ZGREEN, width=1)
    draw.rectangle([34, 730, 484, 752], fill=ZGREEN)
    draw.text((44, 735), "GRID SYNC — TAVARA, TODAY",
              font=font(SANS_B, 9), fill=(255, 255, 255))
    draw.text((44, 758),
              "Sunrise 05:58  ·  Sunset 17:42      Daylight sync only",
              font=font(SANS_B, 10), fill=INK)

    # MRZ
    l1, l2 = mrz_lines()
    draw.rectangle([34, 806, 484, 872], fill=(255, 255, 255),
                   outline=INK_SOFT, width=1)
    draw.text((44, 816), l1, font=font(MONO, 13), fill=INK)
    draw.text((44, 840), l2, font=font(MONO, 13), fill=INK)
    draw.text((34, 884), "LANGUAGES OF ISSUE: ZANVARAN · ENGLISH   |   "
              "ICAO 9303 BIOMETRIC", font=font(SANS, 8), fill=GREY)
    # faint watermark of the passport number, Merrow-style
    wm = "ZV7391846"
    wf = font(SERIF_B, 44)
    draw.text((259 - draw.textlength(wm, font=wf) / 2, 908), wm,
              font=wf, fill=(206, 200, 180))
    center(draw, 259, 972, "2", font(SERIF, 12), INK_SOFT)

    # ================= RIGHT PAGE: visas & stamps =================
    draw.text((540, 30), "ENDORSEMENTS · VISAS", font=font(SERIF_B, 24),
              fill=INK)
    draw.text((972, 34), "3", font=font(SERIF, 12), fill=INK_SOFT)
    draw.line([(540, 62), (990, 62)], fill=INK, width=2)

    # endorsement box
    draw.rectangle([540, 76, 990, 218], outline=INK, width=2)
    draw.text((552, 86), "SOLAR LATTICE ENGINEER'S ENDORSEMENT 2 / 2023",
              font=font(SANS_B, 11), fill=INK)
    draw.line([(552, 106), (978, 106)], fill=INK_SOFT, width=1)
    body = ("The holder is a licensed solar lattice engineer (grid lic. "
            "SL-207), authorised to service the Sunstone Grid. Grid "
            "access only during daylight sync, within ± 1 h of sunrise "
            "and sunset at the Tavara grid gate. Sunstone must not leave "
            "the kingdom unsealed.")
    y = 114
    for line in wrap(draw, body, font(SERIF, 12), 290):
        draw.text((552, y), line, font=font(SERIF, 12), fill=INK)
        y += 16
    draw.text((552, 196), "Tavara, 09 MAY 2023",
              font=font(SERIF_I, 11), fill=INK_SOFT)
    # sunstone levy stamp, overlapping the endorsement corner
    stamp(img, (856, 128, 976, 196),
          [("ZANVARA", "mid"), ("SUNSTONE LEVY", "mid"), ("40 ZVK", "big"),
           ("PAID", "mid")], RED, shape="rect", angle=-7, size=10)

    # Kessari visa
    draw.rectangle([540, 232, 990, 396], fill=(232, 240, 228),
                   outline=GREEN, width=2)
    draw.rectangle([540, 232, 990, 258], fill=GREEN)
    draw.text((552, 238), "REPUBLIC OF KESSARI — SHORT-STAY VISA",
              font=font(SANS_B, 11), fill=(255, 255, 255))
    draw.text((930, 238), "VISA C", font=font(SANS_B, 11),
              fill=(255, 255, 255))
    draw.text((552, 266), "No. KES 2511 0934",
              font=font(SANS_B, 10), fill=RED)
    field(draw, 552, 288, "Valid from / Valable du", "02 DEC 2024")
    field(draw, 770, 288, "Until / Au", "01 JAN 2025")
    field(draw, 552, 326, "Entries / Entrées", "1 · SINGLE")
    field(draw, 770, 326, "Duration / Durée", "20 DAYS")
    draw.text((552, 366), "Issued at / Délivré à  CONSULATE, TAVARA — "
              "18 NOV 2024", font=font(SANS_B, 10), fill=INK)
    draw.text((552, 382), "Passport ZV7391846  ·  NDELE, AMARA  ·  "
              "ENTRY BY RIFT GATE SKY-RAIL · FEE 45 KES PAID",
              font=font(SANS, 9), fill=INK_SOFT)

    draw.text((540, 408), "ENTRY AND EXIT  ·  KUINGIA NA KUTOKA",
              font=font(SANS_B, 10), fill=INK_SOFT)
    draw.line([(540, 426), (990, 426)], fill=INK_SOFT, width=1)

    # stamps: paired, consistent travel history — 4 rows, 8 stamps
    stamp(img, (540, 440, 758, 502),
          [("ZANVARA · EXIT", "mid"), ("12 JUN 2023", "big"),
           ("TAVARA SKY GATE", "small"), ("GRID SYNC 05:58", "small")],
          BLUE, shape="rect", angle=-2, size=10)
    stamp(img, (772, 440, 990, 502),
          [("KESSARI", "big"), ("ENTRY", "mid"), ("13 JUN 2023", "mid"),
           ("RIFT GATE", "small")], RED, shape="round", angle=3, size=10)
    stamp(img, (540, 508, 758, 570),
          [("KESSARI", "big"), ("EXIT", "mid"), ("15 JUN 2023", "mid"),
           ("RIFT GATE", "small")], RED, shape="rect", angle=2, size=10)
    stamp(img, (772, 508, 990, 570),
          [("ZANVARA · ENTRY", "mid"), ("16 JUN 2023", "big"),
           ("TAVARA SKY GATE", "small"), ("GRID SYNC 05:58", "small")],
          GREEN, shape="rect", angle=-3, size=10)
    stamp(img, (540, 576, 758, 638),
          [("KESSARI", "big"), ("ENTRY", "mid"), ("05 DEC 2024", "mid"),
           ("RIFT GATE", "small")], BLUE, shape="oval", angle=-2,
          size=10)
    stamp(img, (772, 576, 990, 638),
          [("KESSARI", "big"), ("EXIT", "mid"), ("12 DEC 2024", "mid"),
           ("RIFT GATE", "small")], RED, shape="rect", angle=3, size=10)
    stamp(img, (540, 644, 758, 706),
          [("VEYRA", "big"), ("ENTRY", "mid"), ("22 AUG 2025", "mid"),
           ("LAKE PORT", "small")], GREEN, shape="round", angle=2,
          size=10)
    stamp(img, (772, 644, 990, 706),
          [("VEYRA", "big"), ("EXIT", "mid"), ("29 AUG 2025", "mid"),
           ("LAKE PORT", "small")], BLUE, shape="rect", angle=-2,
          size=10)

    # sky-rail route map: topographic strip, rail line with ties,
    # three stations with elevations, scale bar, compass
    draw.rectangle([540, 718, 990, 900], outline=INK_SOFT, width=1)
    draw.rectangle([540, 718, 990, 740], fill=INK)
    draw.text((552, 723), "RIFT HIGHLANDS — SKY-RAIL ROUTE 1",
              font=font(SANS_B, 10), fill=(255, 255, 255))
    draw.text((852, 723), "ELEV. IN METRES", font=font(SANS, 8),
              fill=(220, 220, 220))
    # highland sky
    draw.rectangle([540, 740, 990, 900], fill=(216, 228, 222))
    # contour curves
    for y0, amp in ((768, 6), (800, 8), (836, 5)):
        pts = [(x, y0 + amp * math.sin(x / 61.0 + y0))
               for x in range(540, 991, 8)]
        draw.line(pts, fill=(188, 200, 188), width=1)
    # mountain masses
    draw.polygon([(540, 900), (540, 812), (630, 740), (700, 812),
                  (660, 900)], fill=(226, 214, 178))
    draw.polygon([(990, 900), (990, 806), (890, 740), (830, 812),
                  (872, 900)], fill=(226, 214, 178))
    draw.polygon([(700, 900), (760, 836), (830, 900)], fill=(226, 214, 178))
    # rail: two quadratic runs, Tavara -> Nyota Ridge -> Rift Gate,
    # solid line with ties
    def rail(x0, y0, cx, cy, x1, y1):
        pts = []
        for i in range(0, 49):
            t = i / 48
            bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
            by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
            pts.append((bx, by))
        draw.line(pts, fill=ZGREEN, width=3)
        for i in range(0, 49, 4):
            bx, by = pts[i]
            j = min(i + 1, 48)
            dx, dy = pts[j][0] - bx, pts[j][1] - by
            n = math.hypot(dx, dy) or 1
            px, py = -dy / n * 4, dx / n * 4
            draw.line([(bx - px, by - py), (bx + px, by + py)],
                      fill=ZGREEN, width=2)
        return pts
    rail(610, 838, 690, 776, 760, 792)
    rail(760, 792, 830, 800, 905, 806)
    for (x, y, name, elev, lx, ly) in (
            (610, 838, "TAVARA", "2,410 m", 622, 830),
            (760, 792, "NYOTA RIDGE", "3,180 m", 772, 764),
            (905, 806, "RIFT GATE", "1,860 m", 812, 812)):
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill=RED,
                     outline=(255, 255, 255), width=1)
        draw.text((lx, ly), name, font=font(SANS_B, 9), fill=INK)
        draw.text((lx, ly + 11), elev, font=font(SANS, 8), fill=INK_SOFT)
    draw.text((660, 748), "DAYLIGHT SYNC ONLY", font=font(SANS_B, 8),
              fill=RED)
    # scale bar, bottom left
    draw.line([(560, 888), (620, 888)], fill=INK, width=3)
    draw.line([(560, 884), (560, 892)], fill=INK, width=1)
    draw.line([(590, 884), (590, 892)], fill=INK, width=1)
    draw.line([(620, 884), (620, 892)], fill=INK, width=1)
    draw.text((560, 872), "0", font=font(SANS, 8), fill=INK)
    draw.text((586, 872), "10", font=font(SANS, 8), fill=INK)
    draw.text((612, 872), "20 KM", font=font(SANS, 8), fill=INK)
    # compass
    draw.ellipse([946, 856, 978, 888], outline=INK, width=1)
    draw.text((958, 860), "N", font=font(SANS_B, 10), fill=INK)
    draw.line([(962, 872), (962, 882)], fill=INK, width=1)

    draw.text((540, 912),
              "This passport remains the property of the Kingdom of "
              "Zanvara.", font=font(SERIF_I, 11), fill=INK_SOFT)
    draw.text((540, 930), "If found, return to the Passport Office, "
              "Tavara.", font=font(SERIF_I, 11), fill=INK_SOFT)
    draw.text((920, 972), "ZV7391846", font=font(SANS, 9), fill=GREY)
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
