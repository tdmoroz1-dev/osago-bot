import telebot
from telebot import types
import pymupdf
import os, datetime, json, io, gc, traceback
from flask import Flask
import threading

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

user_choices = {}

def load_font(paths):
    for p in paths:
        try:
            if os.path.exists(p):
                with open(p, "rb") as f: data = f.read()
                if len(data) > 100: return data
        except: continue
    return None

REG_BUF = load_font(["times.ttf", r"C:\Windows\Fonts\times.ttf"])
BLD_BUF = load_font(["timesbd.ttf", r"C:\Windows\Fonts\timesbd.ttf"])
THM_BUF = load_font(["tahoma.ttf", r"C:\Windows\Fonts\tahoma.ttf"])
THM_BD_BUF = load_font(["tahomabd.ttf", r"C:\Windows\Fonts\tahomabd.ttf"])

if THM_BUF is None: THM_BUF = REG_BUF
if THM_BD_BUF is None: THM_BD_BUF = BLD_BUF

FONT_REG_OBJ = pymupdf.Font(fontbuffer=REG_BUF)
FONT_BLD_OBJ = pymupdf.Font(fontbuffer=BLD_BUF)
THM_OBJ = pymupdf.Font(fontbuffer=THM_BUF)
THM_BD_OBJ = pymupdf.Font(fontbuffer=THM_BD_BUF)

# Arial для Росгосстраха (если файлов нет - падаем на Tahoma)
AR_BUF = load_font(["arial.ttf", r"C:\Windows\Fonts\arial.ttf"]) or THM_BUF
ARBD_BUF = load_font(["arialbd.ttf", r"C:\Windows\Fonts\arialbd.ttf"]) or THM_BD_BUF
ARBI_BUF = load_font(["arialbi.ttf", r"C:\Windows\Fonts\arialbi.ttf"]) or ARBD_BUF
AR_OBJ = pymupdf.Font(fontbuffer=AR_BUF)
ARBD_OBJ = pymupdf.Font(fontbuffer=ARBD_BUF)
ARBI_OBJ = pymupdf.Font(fontbuffer=ARBI_BUF)

def is_inside(inner, outer):
    r, o = pymupdf.Rect(inner), pymupdf.Rect(outer)
    return (r.x0 >= o.x0 - 0.5 and r.y0 >= o.y0 - 0.5 and r.x1 <= o.x1 + 0.5 and r.y1 <= o.y1 + 0.5)

def get_all_spans(page):
    out = []
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0: continue
        for ln in b.get("lines", []):
            for sp in ln.get("spans", []):
                if sp.get("text", "").strip():
                    out.append(sp)
    return out

def collect_spans(all_spans, area):
    out = []
    for sp in all_spans:
        if is_inside(sp["bbox"], area):
            out.append(sp)
    return out

def font_obj_by_name(fname):
    if fname == "thmb": return THM_BD_OBJ
    if fname == "thm": return THM_OBJ
    if fname == "tnewb": return FONT_BLD_OBJ
    return FONT_REG_OBJ

def int_to_rgb(c):
    return ((c >> 16) & 255) / 255.0, ((c >> 8) & 255) / 255.0, (c & 255) / 255.0

# =========================================================================
# АЛЬФА (НЕ ТРОНУТА)
# =========================================================================
FIELDS_ALFA = {
    "policyholder_fio":        (1, [16.0, 306.65, 230.53, 318.83], "reg",  11),
    "owner_fio":               (1, [16.0, 348.83, 230.86, 361.01], "reg",  11),
    "marka":                   (1, [14.0, 402.65, 184.0, 414.83], "reg",  11),
    "model":                   (1, [14.0, 417.65, 184.0, 429.83], "reg",  11),
    "vin":                     (1, [201.46, 413.15, 302.75, 425.33], "reg", 11),
    "gosnomer":                (1, [491.31, 413.15, 546.83, 425.33], "reg", 11),
    "pts_series":              (1, [411.07, 444.77, 446.77, 452.52], "bold", 7),
    "pts_number":              (1, [499.87, 444.77, 520.83, 452.52], "bold", 7),
    "premium_thousands":       (1, [452.24, 56.65, 463.22, 68.83],   "bold", 11),
    "premium_hundreds":        (1, [463.22, 56.65, 482.47, 68.83],   "bold", 11),
    "premium_kop":             (1, [514.5, 56.65, 525.5, 68.83],     "bold", 11),
    "policy_series":           (1, [259.0, 88.47, 282.8, 100.65],    "bold", 11),
    "policy_number":           (1, [349.0, 88.47, 403.9, 100.65],    "bold", 11),
    "date_start":              (1, [444.75, 187.21, 563.25, 197.18], "reg",  9),
    "date_end":                (1, [444.75, 207.21, 563.25, 217.18], "reg",  9),
    "date_period_start":       (1, [30.0, 252.21, 145.0, 262.18],    "reg",  9),
    "date_period_end":         (1, [165.0, 252.21, 285.0, 262.18],   "reg",  9),
    "date_issue1":             (1, [107.0, 754.3, 138.47, 762.05],   "reg",  7),
    "date_issue2":             (1, [228.99, 754.3, 260.46, 762.05],  "reg",  7),
    "date_design_1":           (1, [398.75, 730.34, 418.71, 739.2],  "reg",  8),
    "date_design_2":           (1, [418.7, 730.34, 507.84, 739.2],   "reg",  8),
    "trailer_old_x":           (1, [220.19, 375.57, 226.01, 382.21], "reg",  6),
    "trailer_new_x":           (1, [248.00, 375.57, 254.00, 382.21], "reg",  6),
    "premium_in_words":        (1, [245.54, 730.34, 398.75, 739.2],  "reg",  8),
    "tb":                      (1, [26.0, 703.77, 60.0, 711.52],     "reg",  7),
    "kt":                      (1, [86.0, 703.77, 120.0, 711.52],    "reg",  7),
    "kbm":                     (1, [141.5, 703.77, 175.5, 711.52],   "reg",  7),
    "kvs":                     (1, [199.0, 703.77, 233.0, 711.52],   "reg",  7),
    "ko":                      (1, [257.0, 703.77, 291.0, 711.52],   "reg",  7),
    "ks":                      (1, [315.0, 703.77, 349.0, 711.52],   "reg",  7),
    "kp":                      (1, [373.0, 703.77, 407.0, 711.52],   "reg",  7),
    "km":                      (1, [431.0, 703.77, 465.0, 711.52],   "reg",  7),
    "premium_total":           (1, [499.0, 703.77, 559.0, 711.52],   "reg",  7),
}
CENTER_FIELDS_ALFA = {"marka", "model", "premium_thousands", "premium_hundreds", "premium_kop", "tb", "kt", "kbm", "kvs", "ko", "ks", "kp", "km", "trailer_new_x", "policy_series", "policy_number", "premium_total"}
DECIMAL_FIELDS = ["kt", "kbm", "kvs", "ko", "ks", "kp", "km"]
DRIVER_ROWS = [(555.9, 563.65), (567.27, 575.02), (577.27, 585.02), (587.27, 595.02), (597.27, 605.02)]
DRIVER_DY = 1.8
DRIVER_COLS = {"fio": (187.2, 310.0), "license": (392.8, 65.0), "kbm": (518.0, 40.0)}
TOTAL_LABELS = {"tb": "ТБ", "kt": "КТ", "kbm": "КБМ", "kvs": "КВС", "ko": "КО", "ks": "КС", "kp": "КП", "km": "КМ", "premium_total": "Итого"}

def label_centers(page):
    out = {}
    for w in page.get_text("words", clip=pymupdf.Rect(0, 676, 600, 702)):
        out[w[4].strip()] = (w[0] + w[2]) / 2
    return out

def snap_rect(rect, key, centers):
    lab = TOTAL_LABELS.get(key)
    if lab and lab in centers:
        cx = centers[lab]
        half = (rect[2] - rect[0]) / 2
        return [cx - half, rect[1], cx + half, rect[3]]
    return rect

def fill_alfa_pdf(data):
    doc = pymupdf.open("template.pdf")
    today = datetime.date.today()
    try: next_year = today.replace(year=today.year + 1)
    except ValueError: next_year = today.replace(year=today.year + 1, day=28)
    end_date = next_year - datetime.timedelta(days=1)
    data["date_start"] = today.strftime("%d.%m.%Y")
    data["date_end"] = end_date.strftime("%d.%m.%Y")
    data["date_period_start"] = data["date_start"]
    data["date_period_end"] = data["date_end"]
    data["date_issue1"] = data["date_start"]
    data["date_issue2"] = data["date_start"]
    data["date_design_1"] = today.strftime("%d.%m.")
    data["date_design_2"] = today.strftime("%Y 00:00:00 UTC+03:00.")

    total_rub = str(data.get("premium_total_thousands", "")).strip()
    if not total_rub:
        total_rub = str(data.get("premium_thousands", "")).strip() + str(data.get("premium_hundreds", "")).strip()
    total_kop = str(data.get("premium_total_kop", "")).strip()
    if not total_kop:
        total_kop = str(data.get("premium_kop", "")).strip()
    if total_rub and total_kop:
        if len(total_kop) == 1: total_kop = "0" + total_kop
        data["premium_total"] = f"{total_rub}.{total_kop}"
    else:
        data["premium_total"] = total_rub
    data["premium_in_words"] = f"{total_rub} рублей {total_kop} копеек. Дата оформления:"

    by_page = {}
    for key, (pno, rect, fkey, size) in FIELDS_ALFA.items():
        if key not in data: continue
        val = str(data[key]).strip()
        if key in DECIMAL_FIELDS:
            try: val = f"{float(val):.2f}"
            except ValueError: pass
        if key in ["policy_series", "policy_number"] and not val: continue
        by_page.setdefault(pno, []).append((rect, val, fkey, size, key))

    for pno, items in by_page.items():
        page = doc[pno - 1]
        all_spans = get_all_spans(page)
        centers = label_centers(page)
        to_delete, inserts = [], []
        for (rect, val, fkey, size, key) in items:
            rect = snap_rect(rect, key, centers)
            spans = collect_spans(all_spans, rect)
            if key == "trailer_old_x" and not spans: continue
            if spans:
                for sp in spans: to_delete.append(sp["bbox"])
            if key in ["date_start", "date_end", "date_period_start", "date_period_end", "date_issue1", "date_issue2"]:
                if not spans: continue
                char_boxes = []
                for sp in spans:
                    text = sp['text'].strip()
                    x0, y0, x1, y1 = sp['bbox']
                    if len(text) == 1: char_boxes.append((x0, y0, x1, y1))
                    else:
                        w = (x1 - x0) / len(text)
                        for i in range(len(text)): char_boxes.append((x0 + i*w, y0, x0 + (i+1)*w, y1))
                char_boxes.sort(key=lambda b: b[0])
                clean_val = val.replace(" ", "")
                for i, ch in enumerate(clean_val):
                    if i >= len(char_boxes): break
                    x0, y0, x1, y1 = char_boxes[i]
                    inserts.append((x0, y1 - 0.22 * size, ch, fkey, size, "char", (0,0,0)))
            else:
                r = pymupdf.Rect(rect)
                is_center = key in CENTER_FIELDS_ALFA
                inserts.append((r, val, fkey, size, is_center, "box", (0,0,0)))

        if to_delete:
            for bb in to_delete: page.add_redact_annot(pymupdf.Rect(bb), fill=False)
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
        page.insert_font(fontname="tnew", fontbuffer=REG_BUF)
        page.insert_font(fontname="tnewb", fontbuffer=BLD_BUF)
        for item in inserts:
            if item[-2] == "char":
                x0, baseline, val, fkey, size, _, color = item
                fname = "tnewb" if fkey == "bold" else "tnew"
                if val: page.insert_text((x0, baseline), val, fontname=fname, fontsize=size, color=color)
            elif item[-2] == "box":
                r, val, fkey, size, is_center, _, color = item
                fname = "tnewb" if fkey == "bold" else "tnew"
                if is_center:
                    f_obj = FONT_BLD_OBJ if fkey == "bold" else FONT_REG_OBJ
                    text_w = f_obj.text_length(val, fontsize=size)
                    x_new = r.x0 + (r.width - text_w) / 2
                    if text_w >= r.width: x_new = r.x0
                else:
                    x_new = r.x0
                baseline = r.y1 - 0.22 * size
                if val: page.insert_text((x_new, baseline), val, fontname=fname, fontsize=size, color=color)
    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    gc.collect()
    return pdf_bytes

def fill_alfa_limited_pdf(data):
    doc = pymupdf.open("template.pdf")
    today = datetime.date.today()
    try: next_year = today.replace(year=today.year + 1)
    except ValueError: next_year = today.replace(year=today.year + 1, day=28)
    end_date = next_year - datetime.timedelta(days=1)
    data["date_start"] = today.strftime("%d.%m.%Y")
    data["date_end"] = end_date.strftime("%d.%m.%Y")
    data["date_period_start"] = data["date_start"]
    data["date_period_end"] = data["date_end"]
    data["date_issue1"] = data["date_start"]
    data["date_issue2"] = data["date_start"]
    data["date_design_1"] = today.strftime("%d.%m.")
    data["date_design_2"] = today.strftime("%Y 00:00:00 UTC+03:00.")

    total_rub = str(data.get("premium_total_thousands", "")).strip()
    if not total_rub:
        total_rub = str(data.get("premium_thousands", "")).strip() + str(data.get("premium_hundreds", "")).strip()
    total_kop = str(data.get("premium_total_kop", "")).strip()
    if not total_kop:
        total_kop = str(data.get("premium_kop", "")).strip()
    if total_rub and total_kop:
        if len(total_kop) == 1: total_kop = "0" + total_kop
        data["premium_total"] = f"{total_rub}.{total_kop}"
    else:
        data["premium_total"] = total_rub
    data["premium_in_words"] = f"{total_rub} рублей {total_kop} копеек. Дата оформления:"

    all_fields = dict(FIELDS_ALFA)
    all_fields["limited_checkbox"] = (1, [392.97, 517.61, 398.03, 525.36], "reg", 7)
    all_fields["unlimited_checkbox"] = (1, [392.97, 507.08, 398.03, 514.83], "reg", 7)
    data["limited_checkbox"] = "X"
    data["unlimited_checkbox"] = ""

    drivers = data.get("drivers", [])
    for i, (y0, y1) in enumerate(DRIVER_ROWS, start=1):
        for col, (cx, w) in DRIVER_COLS.items():
            all_fields[f"driver{i}_{col}"] = (1, [cx - w / 2, y0, cx + w / 2, y1], "reg", 7)
    for i, d in enumerate(drivers[:5]):
        idx = i + 1
        data[f"driver{idx}_fio"] = d.get("fio", "")
        data[f"driver{idx}_license"] = d.get("license", "")
        try: data[f"driver{idx}_kbm"] = f"{float(d.get('kbm', '1.00')):.2f}"
        except: data[f"driver{idx}_kbm"] = "1.00"

    by_page = {}
    for key, (pno, rect, fkey, size) in all_fields.items():
        if key not in data: continue
        val = str(data[key]).strip()
        if key in DECIMAL_FIELDS:
            try: val = f"{float(val):.2f}"
            except ValueError: pass
        if key in ["policy_series", "policy_number"] and not val: continue
        by_page.setdefault(pno, []).append((rect, val, fkey, size, key))

    for pno, items in by_page.items():
        page = doc[pno - 1]
        all_spans = get_all_spans(page)
        centers = label_centers(page)
        to_delete, inserts = [], []
        for (rect, val, fkey, size, key) in items:
            rect = snap_rect(rect, key, centers)
            r = pymupdf.Rect(rect)
            spans = collect_spans(all_spans, r)
            if key in ["trailer_old_x", "unlimited_checkbox", "limited_checkbox"]:
                if spans:
                    for sp in spans: to_delete.append(sp["bbox"])
                if val: inserts.append((r, val, fkey, size, True, "box", (0,0,0)))
                continue
            if spans:
                for sp in spans: to_delete.append(sp["bbox"])
            if key in ["date_start", "date_end", "date_period_start", "date_period_end", "date_issue1", "date_issue2"]:
                if not spans: continue
                char_boxes = []
                for sp in spans:
                    text = sp['text'].strip()
                    x0, y0, x1, y1 = sp['bbox']
                    if len(text) == 1: char_boxes.append((x0, y0, x1, y1))
                    else:
                        w = (x1 - x0) / len(text)
                        for i in range(len(text)): char_boxes.append((x0 + i*w, y0, x0 + (i+1)*w, y1))
                char_boxes.sort(key=lambda b: b[0])
                clean_val = val.replace(" ", "")
                for i, ch in enumerate(clean_val):
                    if i >= len(char_boxes): break
                    x0, y0, x1, y1 = char_boxes[i]
                    inserts.append((x0, y1 - 0.22 * size, ch, fkey, size, "char", (0,0,0)))
            else:
                is_center = True if key.startswith("driver") else (key in CENTER_FIELDS_ALFA)
                if key.startswith("driver"):
                    r = pymupdf.Rect(r.x0, r.y0 + DRIVER_DY, r.x1, r.y1 + DRIVER_DY)
                inserts.append((r, val, fkey, size, is_center, "box", (0,0,0)))

        if to_delete:
            for bb in to_delete: page.add_redact_annot(pymupdf.Rect(bb), fill=False)
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
        page.insert_font(fontname="tnew", fontbuffer=REG_BUF)
        page.insert_font(fontname="tnewb", fontbuffer=BLD_BUF)
        for item in inserts:
            if item[-2] == "char":
                x0, baseline, val, fkey, size, _, color = item
                fname = "tnewb" if fkey == "bold" else "tnew"
                if val: page.insert_text((x0, baseline), val, fontname=fname, fontsize=size, color=color)
            elif item[-2] == "box":
                r, val, fkey, size, is_center, _, color = item
                fname = "tnewb" if fkey == "bold" else "tnew"
                if is_center:
                    f_obj = FONT_BLD_OBJ if fkey == "bold" else FONT_REG_OBJ
                    text_w = f_obj.text_length(val, fontsize=size)
                    x_new = r.x0 + (r.width - text_w) / 2
                    if text_w >= r.width: x_new = r.x0
                else:
                    x_new = r.x0
                baseline = r.y1 - 0.22 * size
                if val: page.insert_text((x_new, baseline), val, fontname=fname, fontsize=size, color=color)
    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    gc.collect()
    return pdf_bytes

# =========================================================================
# ИНГОССТРАХ (НЕ ТРОНУТ)
# =========================================================================
FIELDS_INGOS = {
    "policyholder_fio":        (1, [25.0, 251.8, 500.0, 263.87]),
    "owner_fio":               (1, [25.0, 274.03, 500.0, 286.1]),
    "marka":                   (1, [50.0, 322.47, 160.0, 334.54]),
    "model":                   (1, [50.0, 334.54, 160.0, 346.61]),
    "gosnomer":                (1, [465.0, 331.73, 555.0, 343.8]),
    "premium_str":             (1, [450.0, 40.07, 580.0, 52.14]),
    "policy_number_str":       (1, [250.0, 99.02, 450.0, 115.91]),
    "date_start_top":          (1, [506.14, 162.21, 560.72, 171.87]),
    "date_end_top":            (1, [506.14, 177.57, 560.72, 187.22]),
    "date_period_str":         (1, [28.35, 223.93, 194.52, 236.0]),
    "pts_doc_line":            (1, [28.35, 363.31, 300.0, 372.96]),
    "unlimited_checkbox":      (1, [21.25, 420.22, 359.27, 429.87]),
    "limited_checkbox":        (1, [21.25, 429.87, 300.0, 439.52]),
    "trailer_checkbox":        (1, [250.59, 289.5, 300.92, 299.15]),
    "date_issue1":             (1, [26.65, 789.27, 300.0, 798.92]),
    "contract_date_line":      (1, [28.35, 744.16, 500.0, 753.81]),
    "tb":                      (1, [60.0, 667.2, 90.0, 678.07]),
    "kt":                      (1, [135.0, 667.2, 168.0, 678.07]),
    "kbm":                     (1, [188.0, 667.2, 220.0, 678.07]),
    "kvs":                     (1, [240.0, 667.2, 273.0, 678.07]),
    "ko":                      (1, [292.0, 667.2, 326.0, 678.07]),
    "ks":                      (1, [344.0, 667.2, 378.0, 678.07]),
    "kp":                      (1, [397.0, 667.2, 430.0, 678.07]),
    "km":                      (1, [449.0, 667.2, 483.0, 678.07]),
    "premium_total":           (1, [500.0, 667.2, 570.0, 678.07]),
}
CENTER_FIELDS_INGOS = {"marka", "model", "gosnomer", "policy_number_str", "premium_str", "tb", "kt", "kbm", "kvs", "ko", "ks", "kp", "km", "premium_total"}

INGOS_DRIVER_ROWS = [
    (483.44, 495.51, 61.98, 446.09, 539.14),
    (496.01, 508.08, 61.98, 446.12, 539.34),
    (508.58, 520.65, 61.98, 446.78, 539.66),
    (521.15, 533.22, 62.48, 447.04, 540.08),
    (533.72, 545.79, 62.48, 447.33, 540.08),
]

def get_font_name(font_str):
    if "Tahoma" in font_str:
        return "thmb" if "Bold" in font_str or "Bd" in font_str else "thm"
    if "Times" in font_str:
        return "tnewb" if "Bold" in font_str else "tnew"
    return "thm"

def ingos_vin_cells(page):
    cells = []
    try:
        for d in page.get_drawings():
            r = d["rect"]
            if 316 < r.y0 < 340 and 318 < r.y1 < 344 and 8 < r.width < 25 and 8 < r.height < 25:
                cells.append(pymupdf.Rect(r))
    except Exception: pass
    cells.sort(key=lambda r: r.x0)
    if cells:
        chain = [cells[0]]
        for r in cells[1:]:
            if r.x0 - chain[-1].x0 < 30: chain.append(r)
        cells = chain
    return cells

def fill_ingos_pdf(data):
    doc = pymupdf.open("template_ingos.pdf")

    msk_now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    today = msk_now.date()

    try: next_year = today.replace(year=today.year + 1)
    except ValueError: next_year = today.replace(year=today.year + 1, day=28)
    end_date = next_year - datetime.timedelta(days=1)

    months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    month_name = months[msk_now.month - 1]

    total_rub = str(data.get("premium_total_thousands", "")).strip()
    if not total_rub:
        total_rub = str(data.get("premium_thousands", "")).strip() + str(data.get("premium_hundreds", "")).strip()
    total_kop = str(data.get("premium_total_kop", "")).strip()
    if not total_kop:
        total_kop = str(data.get("premium_kop", "")).strip()
    if total_rub and total_kop:
        if len(total_kop) == 1: total_kop = "0" + total_kop
        formatted_total = f"{total_rub}.{total_kop}"
    else:
        formatted_total = total_rub

    if total_rub:
        data["premium_str"] = f"{total_rub} руб. {total_kop} коп."

    series = str(data.get('policy_series', '')).strip()
    number = str(data.get('policy_number', '')).strip()
    if series or number:
        data["policy_number_str"] = f"№  {series} {number}".strip()
    else:
        data.pop("policy_number_str", None)

    vin_val = "".join(str(data.get("vin", "")).split()).upper()
    data.pop("vin", None)

    data["date_start_top"] = f"{today.strftime('%d.%m.%Y')} г."
    data["date_end_top"] = f"{end_date.strftime('%d.%m.%Y')} г."
    data["date_period_str"] = f"с {today.strftime('%d.%m.%Y')} г. по {end_date.strftime('%d.%m.%Y')} г."
    data["pts_doc_line"] = f"Вид документа ПАСПОРТ ТС серия {data.get('pts_series', '')} номер {data.get('pts_number', '')}"
    data["date_issue1"] = f"Дата выдачи полиса «{msk_now.day}» {month_name} {msk_now.year} г."
    data["contract_date_line"] = f"Дата заключения договора «{msk_now.day}» {month_name} {msk_now.year} г. ({msk_now.strftime('%d.%m.%Y')} в {msk_now.strftime('%H:%M')} по московскому времени)"

    drivers = data.get("drivers", [])
    if drivers:
        data["unlimited_checkbox"] = "[ ] неограниченного количества лиц, допущенных к управлению транспортным средством"
        data["limited_checkbox"] = "[V] лиц, допущенных к управлению транспортным средством"
    else:
        data["unlimited_checkbox"] = "[V] неограниченного количества лиц, допущенных к управлению транспортным средством"
        data["limited_checkbox"] = "[ ] лиц, допущенных к управлению транспортным средством"
    if data.get("trailer", "").lower() == "нет":
        data["trailer_checkbox"] = "[] да, [X] нет."
    else:
        data["trailer_checkbox"] = "[X] да, [] нет."

    try:
        tot_r = int(float(formatted_total))
        tot_k = int(round((float(formatted_total) - tot_r) * 100))
        data["premium_total"] = f"{tot_r:,}".replace(',', ' ') + f",{tot_k:02d}"
    except: data["premium_total"] = formatted_total

    all_fields = dict(FIELDS_INGOS)
    if drivers:
        for i, d in enumerate(drivers[:5]):
            y0, y1, fx, lcx, kcx = INGOS_DRIVER_ROWS[i]
            all_fields[f"driver{i+1}_fio"]     = (1, [fx, y0, 400.0, y1])
            all_fields[f"driver{i+1}_license"] = (1, [lcx - 45.0, y0, lcx + 45.0, y1])
            all_fields[f"driver{i+1}_kbm"]     = (1, [kcx - 30.0, y0, kcx + 30.0, y1])
            data[f"driver{i+1}_fio"] = d.get("fio", "")
            data[f"driver{i+1}_license"] = d.get("license", "")
            try: data[f"driver{i+1}_kbm"] = f"{float(d.get('kbm', '1.00')):.2f}"
            except: data[f"driver{i+1}_kbm"] = "1.00"

    by_page = {}
    for key, (pno, rect) in all_fields.items():
        if key not in data: continue
        val = str(data[key]).strip()
        if key in DECIMAL_FIELDS:
            try: val = f"{float(val):.2f}"
            except ValueError: pass
        if key in ["policy_number_str", "premium_str"] and not val: continue
        by_page.setdefault(pno, []).append((rect, val, key))

    for pno, items in by_page.items():
        page = doc[pno - 1]
        all_spans = get_all_spans(page)
        to_delete, inserts, vin_inserts = [], [], []

        if pno == 1 and vin_val:
            VIN_RECT = [186, 318, 440, 340]
            vspans = collect_spans(all_spans, VIN_RECT)
            for sp in vspans: to_delete.append(sp["bbox"])

            cells = ingos_vin_cells(page)
            vfont, vsize, vcolor = "thmb", 11, (0,0,0)
            if vspans:
                vfont = get_font_name(vspans[0]["font"])
                vsize = vspans[0]["size"]
                vcolor = int_to_rgb(vspans[0]["color"])
            v_obj = font_obj_by_name(vfont)

            if len(cells) >= 17:
                for i, ch in enumerate(vin_val):
                    if i >= len(cells): break
                    cell = cells[i]
                    w = v_obj.text_length(ch, fontsize=vsize)
                    x = cell.x0 + (cell.width - w) / 2
                    y = cell.y1 - 3.5
                    vin_inserts.append((x, y, ch, vfont, vsize, vcolor))
            else:
                boxes = []
                for sp in vspans:
                    t = sp["text"]
                    x0, y0, x1, y1 = sp["bbox"]
                    w = (x1 - x0) / len(t)
                    for i, ch in enumerate(t):
                        if ch.isalnum(): boxes.append((x0 + i*w, x0 + (i+1)*w))
                boxes.sort()
                if len(boxes) >= 17:
                    c0 = (boxes[0][0] + boxes[0][1]) / 2
                    cN = (boxes[-1][0] + boxes[-1][1]) / 2
                    p = (cN - c0) / 16
                    centers = [c0 + i * p for i in range(17)]
                else:
                    c0 = 198.4; p = 14.05
                    centers = [c0 + i * p for i in range(17)]
                for i, ch in enumerate(vin_val):
                    if i < len(centers):
                        w = v_obj.text_length(ch, fontsize=vsize)
                        vin_inserts.append((centers[i] - w / 2, 332.5, ch, vfont, vsize, vcolor))

        for (rect, val, key) in items:
            r = pymupdf.Rect(rect)
            spans = collect_spans(all_spans, r)

            fname = "thm"
            fsize = 10
            fcolor = (0,0,0)

            if spans:
                if key in ["policy_number_str", "premium_str"]:
                    spans_sorted = sorted(spans, key=lambda s: s["bbox"][0])
                    if key == "premium_str": target_span = spans_sorted[0]
                    else: target_span = spans_sorted[-1]
                    fname = get_font_name(target_span["font"])
                    fsize = target_span["size"]
                    fcolor = int_to_rgb(target_span["color"])
                else:
                    fname = get_font_name(spans[0]["font"])
                    fsize = spans[0]["size"]
                    fcolor = int_to_rgb(spans[0]["color"])

                for sp in spans: to_delete.append(sp["bbox"])

            is_center = (key in CENTER_FIELDS_INGOS) or (key.startswith("driver") and not key.endswith("_fio"))
            inserts.append((r, val, fname, fsize, is_center, fcolor))

        if to_delete:
            for bb in to_delete: page.add_redact_annot(pymupdf.Rect(bb), fill=False)
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)

        page.insert_font(fontname="thm", fontbuffer=THM_BUF)
        page.insert_font(fontname="thmb", fontbuffer=THM_BD_BUF)
        page.insert_font(fontname="tnew", fontbuffer=REG_BUF)
        page.insert_font(fontname="tnewb", fontbuffer=BLD_BUF)

        for x, b, ch, fnt, sz, col in vin_inserts:
            page.insert_text((x, b), ch, fontname=fnt, fontsize=sz, color=col)

        for item in inserts:
            r, val, fname, size, is_center, color = item
            if not val: continue
            f_obj = font_obj_by_name(fname)
            text_w = f_obj.text_length(val, fontsize=size)

            if is_center:
                x_new = r.x0 + (r.width - text_w) / 2
                if text_w >= r.width: x_new = r.x0
            else:
                x_new = r.x0

            baseline = r.y1 - 0.22 * size
            page.insert_text((x_new, baseline), val, fontname=fname, fontsize=size, color=color)

    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    gc.collect()
    return pdf_bytes

# =========================================================================
# РОСГОССТРАХ — координаты из rgs_full.txt + rgs_cells.txt
# =========================================================================
MONTHS_RU = ["января","февраля","марта","апреля","мая","июня",
             "июля","августа","сентября","октября","ноября","декабря"]

RGS_TERM = {
    "sd": [442.32, 129.68, 469.68, 143.36],
    "sm": [479.28, 129.68, 506.64, 143.36],
    "sy": [531.36, 129.68, 558.72, 143.36],
    "ed": [442.32, 142.40, 469.68, 156.08],
    "em": [479.28, 142.40, 506.64, 156.08],
    "ey": [531.36, 142.40, 558.72, 156.08],
}
RGS_PERIOD = {
    "sd": [32.16, 189.20, 59.52, 202.88],
    "sm": [66.48, 189.20, 93.84, 202.88],
    "sy": [113.28, 189.20, 140.64, 202.88],
    "ed": [172.80, 189.20, 200.16, 202.88],
    "em": [207.84, 189.20, 235.20, 202.88],
    "ey": [252.00, 189.20, 279.36, 202.88],
}

RGS_TRAILER_YES = [266.16, 318.80, 279.60, 332.00]
RGS_TRAILER_NO  = [303.84, 318.80, 317.04, 332.00]
RGS_TYPE_BOX    = [413.04, 456.56, 458.88, 484.40]
RGS_TYPE_DX     = 435.46
RGS_TYPE_BASE   = 466.74
RGS_TYPE_STEP   = 11.28

RGS_VIN_RECT = [200.0, 355.0, 440.0, 375.0]

# Центры колонок марки/модели и госномера (по заголовкам бланка)
RGS_MARKA_CX = 107.49
RGS_GOS_CX   = 508.19

RGS_LABELS = {"tb":"ТБ","kt":"КТ","kbm":"КБМ","kvs":"КВС","ko":"КО",
              "ks":"КС","kp":"КП","km":"КМ","premium_total":"Итого"}
RGS_LABEL_FALLBACK = {"tb":49.8,"kt":108.0,"kbm":162.0,"kvs":216.0,"ko":265.6,
                      "ks":315.0,"kp":367.2,"km":439.1,"premium_total":527.9}

RGS_DRIVER_ROWS = [
    {"num":[22.0,506.5,30.0,519.5], "fio":[50.0,506.5,310.0,519.5],
     "vu":[385.0,506.5,468.0,519.5], "kbm":[505.0,507.0,548.0,520.0],
     "vu_cx":426.01, "kbm_cx":525.82, "num_cx":25.35},
    {"num":[22.0,520.7,30.0,533.7], "fio":[50.0,520.7,310.0,533.7],
     "vu":[385.0,520.7,468.0,533.7], "kbm":[505.0,523.0,548.0,536.1],
     "vu_cx":426.01, "kbm_cx":526.29, "num_cx":25.35},
    {"num":[22.0,536.8,30.0,549.8], "fio":[50.0,533.9,310.0,546.9],
     "vu":[385.0,534.6,468.0,547.6], "kbm":[505.0,539.2,548.0,552.2],
     "vu_cx":427.45, "kbm_cx":526.29, "num_cx":25.35},
    {"num":[22.0,552.6,30.0,565.6], "fio":[50.0,551.9,310.0,564.9],
     "vu":[385.0,551.6,468.0,564.7], "kbm":[505.0,555.2,548.0,568.3],
     "vu_cx":426.25, "kbm_cx":526.29, "num_cx":25.35},
]

def rgs_font_name(font_str):
    f = str(font_str).lower()
    bold = ("bold" in f) or ("bd" in f)
    ital = ("ita" in f) or ("oblique" in f)
    if bold and ital: return "arbi"
    if bold: return "arbd"
    return "ar"

def rgs_font_obj(fname):
    if fname == "arbi": return ARBI_OBJ
    if fname == "arbd": return ARBD_OBJ
    return AR_OBJ

def rgs_label_centers(page):
    out = {}
    try:
        for w in page.get_text("words", clip=pymupdf.Rect(0, 660, 600, 684)):
            out[w[4].strip()] = (w[0] + w[2]) / 2
    except Exception:
        pass
    return out

def rgs_coef(val):
    try: return f"{float(str(val).replace(',', '.')):.2f}"
    except Exception: return str(val).strip()

def fill_rgs_pdf(data):
    doc = pymupdf.open("template_rgs.pdf")
    page = doc[0]

    msk_now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
    today = msk_now.date()
    try: next_year = today.replace(year=today.year + 1)
    except ValueError: next_year = today.replace(year=today.year + 1, day=28)
    end_date = next_year - datetime.timedelta(days=1)

    rub = str(data.get("premium_total_thousands", "")).strip()
    if not rub:
        rub = str(data.get("premium_thousands", "")).strip() + str(data.get("premium_hundreds", "")).strip()
    kop = str(data.get("premium_total_kop", "")).strip()
    if not kop:
        kop = str(data.get("premium_kop", "")).strip()
    rub = "".join(c for c in rub if c.isdigit())
    kop = ("".join(c for c in kop if c.isdigit()) or "0").zfill(2)[:2]

    drivers = [d for d in data.get("drivers", []) if str(d.get("fio", "")).strip()]
    limited = bool(drivers)

    all_spans = get_all_spans(page)
    to_delete, inserts = [], []
    tasks = []

    def put(rect, text, align="left", cx=None, max_w=None):
        tasks.append({"rect": rect, "text": "" if text is None else str(text).strip(),
                      "align": align, "cx": cx, "max_w": max_w})

    def put_digits(rect, digits):
        sps = [s for s in collect_spans(all_spans, rect) if s["text"].strip().isdigit()]
        sps.sort(key=lambda s: s["bbox"][0])
        for s in sps: to_delete.append(s["bbox"])
        for i, ch in enumerate(str(digits)):
            if i >= len(sps): break
            s = sps[i]
            x0, y0, x1, y1 = s["bbox"]
            fn = rgs_font_name(s["font"]); fs = s["size"]; fc = int_to_rgb(s["color"])
            w = rgs_font_obj(fn).text_length(ch, fontsize=fs)
            base = s["origin"][1] if "origin" in s else y1 - 0.21 * fs
            inserts.append(((x0 + x1) / 2 - w / 2, base, ch, fn, fs, fc))

    def put_mark(box, symbol):
        r = pymupdf.Rect(box)
        for s in collect_spans(all_spans, r): to_delete.append(s["bbox"])
        if not symbol: return
        fs = 10.0
        w = ARBD_OBJ.text_length(symbol, fontsize=fs)
        inserts.append(((r.x0 + r.x1) / 2 - w / 2, r.y1 - 2.3, symbol, "arbd", fs, (0,0,0)))

    # 1. Премия сверху
    if rub:
        put([460, 29.0, 567, 38.5], f"{rub} руб. {kop} коп.", align="center", cx=513.63, max_w=104)

    # 2. Номер полиса (пусто в JSON -> оставляем шаблонный)
    p_ser = str(data.get("policy_series", "")).strip()
    p_num = str(data.get("policy_number", "")).strip()
    if p_ser or p_num:
        put([288, 47.5, 375, 60.5], f"{p_ser} {p_num}".strip(), max_w=85)

    # 3. Срок страхования — по клеткам
    put_digits(RGS_TERM["sd"], today.strftime("%d"))
    put_digits(RGS_TERM["sm"], today.strftime("%m"))
    put_digits(RGS_TERM["sy"], today.strftime("%y"))
    put_digits(RGS_TERM["ed"], end_date.strftime("%d"))
    put_digits(RGS_TERM["em"], end_date.strftime("%m"))
    put_digits(RGS_TERM["ey"], end_date.strftime("%y"))

    # 4. Период использования (1-й период) — по клеткам
    put_digits(RGS_PERIOD["sd"], today.strftime("%d"))
    put_digits(RGS_PERIOD["sm"], today.strftime("%m"))
    put_digits(RGS_PERIOD["sy"], today.strftime("%y"))
    put_digits(RGS_PERIOD["ed"], end_date.strftime("%d"))
    put_digits(RGS_PERIOD["em"], end_date.strftime("%m"))
    put_digits(RGS_PERIOD["ey"], end_date.strftime("%y"))

    # 5. Страхователь и собственник
    put([22, 244.5, 400, 257.0], data.get("policyholder_fio", ""), max_w=375)
    put([22, 293.0, 400, 305.5], data.get("owner_fio", ""), max_w=375)

    # 6. Прицеп
    trailer_yes = str(data.get("trailer", "")).strip().lower() in ("да", "yes", "true", "1")
    put_mark(RGS_TRAILER_YES, "V" if trailer_yes else "")
    put_mark(RGS_TRAILER_NO, "" if trailer_yes else "V")

    # 7. Марка + модель ОДНОЙ строкой — ПО ЦЕНТРУ колонки
    mm = f"{str(data.get('marka','')).strip()} {str(data.get('model','')).strip()}".strip()
    put([22, 348.5, 195, 366.0], mm, align="center", cx=RGS_MARKA_CX, max_w=170)

    # 8. Госномер — ПО ЦЕНТРУ колонки
    put([448, 355.5, 570, 370.0], data.get("gosnomer", ""), align="center", cx=RGS_GOS_CX, max_w=120)

    # 9. VIN — равномерная сетка по краям образца
    vin_val = "".join(str(data.get("vin", "")).split()).upper()
    if vin_val:
        vs = collect_spans(all_spans, RGS_VIN_RECT)
        for s in vs: to_delete.append(s["bbox"])
        if vs:
            sp = sorted(vs, key=lambda s: -len(s["text"]))[0]
            old = "".join(c for c in sp["text"] if c.isalnum())
            x0, y0, x1, y1 = sp["bbox"]
            fn = rgs_font_name(sp["font"]); fs = sp["size"]; fc = int_to_rgb(sp["color"])
            fo = rgs_font_obj(fn)
            base = sp["origin"][1] if "origin" in sp else y1 - 0.21 * fs
            n = len(old)
            if n > 1:
                c0 = x0 + fo.text_length(old[0], fontsize=fs) / 2
                cN = x1 - fo.text_length(old[-1], fontsize=fs) / 2
                pitch = (cN - c0) / (n - 1)
            else:
                c0, pitch = x0 + 3.0, 13.9
            for i, ch in enumerate(vin_val):
                w = fo.text_length(ch, fontsize=fs)
                inserts.append((c0 + i * pitch - w / 2, base, ch, fn, fs, fc))

    # 10. Документ на ТС — 3 отдельных поля
    put([80, 390.5, 110, 400.7], str(data.get("doc_type", "ПТС")).strip(), max_w=28)
    put([366, 390.7, 410, 400.7], data.get("pts_series", ""), max_w=42)
    put([441, 391.3, 500, 400.4], data.get("pts_number", ""), max_w=57)

    # 11. Цель использования — V у "личная" уже в бланке, не трогаем

    # 12. Тип полиса — галочка X в нужной строке
    tmarks = collect_spans(all_spans, RGS_TYPE_BOX)
    for s in tmarks: to_delete.append(s["bbox"])
    tdx, tbase = RGS_TYPE_DX, RGS_TYPE_BASE
    if tmarks:
        s0 = tmarks[0]
        tdx = (s0["bbox"][0] + s0["bbox"][2]) / 2
        tbase = s0["origin"][1] if "origin" in s0 else s0["bbox"][3] - 2.1
    w = ARBD_OBJ.text_length("X", fontsize=10.0)
    if not limited:
        inserts.append((tdx - w / 2, tbase, "X", "arbd", 10.0, (0,0,0)))
    else:
        inserts.append((tdx - w / 2, tbase + RGS_TYPE_STEP, "X", "arbd", 10.0, (0,0,0)))

    # 13. Таблица водителей (4 строки)
    if limited:
        for i, d in enumerate(drivers[:4]):
            row = RGS_DRIVER_ROWS[i]
            try: kb = f"{float(d.get('kbm', '1.00')):.2f}"
            except Exception: kb = "1.00"
            put(row["num"], str(i + 1), align="center", cx=row["num_cx"], max_w=8)
            put(row["fio"], d.get("fio", ""), max_w=255)
            put(row["vu"], d.get("license", ""), align="center", cx=row["vu_cx"], max_w=80)
            put(row["kbm"], kb, align="center", cx=row["kbm_cx"], max_w=40)

    # 14. Коэффициенты + Итого
    centers = rgs_label_centers(page)
    for key, lab in RGS_LABELS.items():
        cx = centers.get(lab, RGS_LABEL_FALLBACK[key])
        half = 30 if key == "premium_total" else 25
        if key == "premium_total":
            val = f"{rub}.{kop}" if rub else ""
        elif key == "tb":
            val = str(data.get("tb", "")).strip()
        else:
            val = rgs_coef(data.get(key, "")) if str(data.get(key, "")).strip() else ""
        if not val: continue
        put([cx - half, 684.5, cx + half, 695.0], val, align="center", cx=cx, max_w=half * 2)

    # 15. Даты внизу
    mn = MONTHS_RU[today.month - 1]
    put([146, 752.5, 164, 765.0], str(today.day), align="center", cx=154.98, max_w=17)
    put([183, 751.5, 240, 765.0], mn, max_w=55)
    put([263, 752.5, 280, 765.0], today.strftime("%y"), max_w=16)
    put([145, 777.5, 163, 790.0], str(today.day), align="center", cx=154.02, max_w=17)
    put([188, 776.0, 245, 790.0], mn, max_w=55)
    put([266.5, 777.5, 283, 790.0], today.strftime("%y"), max_w=16)

    # ===== ИСПОЛНЕНИЕ =====
    for t in tasks:
        r = pymupdf.Rect(t["rect"])
        spans = collect_spans(all_spans, r)
        text = t["text"]

        fname, fsize, fcolor = "ar", 10.0, (0,0,0)
        left_x = r.x0
        base = r.y1 - 0.21 * fsize
        if spans:
            ss = sorted(spans, key=lambda s: s["bbox"][0])
            s0 = ss[0]
            fname = rgs_font_name(s0["font"])
            fsize = s0["size"]
            fcolor = int_to_rgb(s0["color"])
            left_x = s0["bbox"][0]
            base = s0["origin"][1] if "origin" in s0 else s0["bbox"][3] - 0.21 * fsize
            for s in spans: to_delete.append(s["bbox"])

        if not text: continue

        fo = rgs_font_obj(fname)
        max_w = t["max_w"] or r.width
        w = fo.text_length(text, fontsize=fsize)
        if 0 < max_w < w:
            fsize = max(4.0, fsize * max_w / w)
            w = fo.text_length(text, fontsize=fsize)

        if t["align"] == "center":
            cx = t["cx"] if t["cx"] is not None else (r.x0 + r.x1) / 2
            x = cx - w / 2
        else:
            x = left_x
        inserts.append((x, base, text, fname, fsize, fcolor))

    if to_delete:
        for bb in to_delete: page.add_redact_annot(pymupdf.Rect(bb), fill=False)
        page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                              graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)

    page.insert_font(fontname="ar", fontbuffer=AR_BUF)
    page.insert_font(fontname="arbd", fontbuffer=ARBD_BUF)
    page.insert_font(fontname="arbi", fontbuffer=ARBI_BUF)

    for x, b, text, fn, fs, fc in inserts:
        page.insert_text((x, b), text, fontname=fn, fontsize=fs, color=fc)

    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    gc.collect()
    return pdf_bytes

# =========================================================================
# ИНТЕРФЕЙС
# =========================================================================
COMPANY_BUTTONS = {
    "🔴 АльфаСтрахование": ("alfa", "АльфаСтрахование"),
    "🔵 Ингосстрах": ("ingo", "Ингосстрах"),
    "🔴 Росгосстрах": ("rgs", "Росгосстрах"),
}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton("🔴 АльфаСтрахование"), types.KeyboardButton("🔵 Ингосстрах"))
    markup.add(types.KeyboardButton("🔴 Росгосстрах"))
    bot.send_message(message.chat.id, "👋 Привет! Выбери страховую компанию на клавиатуре внизу:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in COMPANY_BUTTONS)
def handle_company_choice(message):
    key, name = COMPANY_BUTTONS[message.text]
    user_choices[message.from_user.id] = key
    bot.reply_to(message, f"✅ Выбрано: *{name}*.\n\nТеперь пришли мне JSON с данными.", parse_mode='Markdown')

@bot.message_handler(content_types=['text'])
def handle_json(message):
    if message.text in COMPANY_BUTTONS:
        return

    insurer_key = user_choices.get(message.from_user.id, "alfa")
    insurer_name = {"alfa": "АльфаСтрахование", "ingo": "Ингосстрах", "rgs": "Росгосстрах"}.get(insurer_key, "АльфаСтрахование")
    raw_text = message.text.strip().replace("```json", "").replace("```", "").strip()

    if not raw_text.startswith("{"):
        bot.reply_to(message, f"Ты выбрал: {insurer_name}. Отправь JSON с данными.")
        return

    try: data = json.loads(raw_text)
    except json.JSONDecodeError:
        bot.reply_to(message, "❌ Ошибка: это не похоже на JSON.")
        return

    if data.get("trailer", "").lower() == "нет":
        data["trailer_old_x"] = ""
        data["trailer_new_x"] = "Х"
    else:
        data["trailer_old_x"] = "Х"
        data["trailer_new_x"] = ""

    drivers = [d for d in data.get("drivers", []) if str(d.get("fio", "")).strip()]
    try:
        if insurer_key == "alfa":
            if drivers:
                bot.reply_to(message, f"📄 {insurer_name}. Водителей: {len(drivers)}. Тип: Ограниченный. ⏳ Генерирую...")
                pdf_data = fill_alfa_limited_pdf(data)
            else:
                bot.reply_to(message, f"📄 {insurer_name}. Водителей: 0. Тип: Неограниченный. ⏳ Генерирую...")
                pdf_data = fill_alfa_pdf(data)
        elif insurer_key == "rgs":
            tipo = "Ограниченный" if drivers else "Неограниченный"
            bot.reply_to(message, f"📄 {insurer_name}. Водителей: {len(drivers)}. Тип: {tipo}. ⏳ Генерирую...")
            pdf_data = fill_rgs_pdf(data)
        else:
            bot.reply_to(message, f"📄 {insurer_name}. ⏳ Генерирую...")
            pdf_data = fill_ingos_pdf(data)

        owner = data.get("owner_fio", "Полис_ОСАГО").strip()
        safe_name = "".join([c for c in owner if c not in r'\/:*?"<>|']).strip() or "Полис_ОСАГО"
        pdf_file = io.BytesIO(pdf_data)
        pdf_file.name = f"{safe_name}.pdf"
        bot.send_document(message.chat.id, pdf_file)
    except Exception as e:
        traceback.print_exc()
        bot.reply_to(message, f"❌ Ошибка: {e}")

@app.route('/')
def home():
    return "Bot is running!"

def run_bot():
    print("Бот запущен и ждет сообщений...")
    bot.polling(none_stop=True)

if __name__ == '__main__':
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
