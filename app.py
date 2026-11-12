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

def is_inside(inner, outer):
    r, o = pymupdf.Rect(inner), pymupdf.Rect(outer)
    return (r.x0 >= o.x0 - 0.5 and r.y0 >= o.y0 - 0.5 and r.x1 <= o.x1 + 0.5 and r.y1 <= o.y1 + 0.5)

# ОПТИМИЗАЦИЯ: фильтруем готовый список спанов, а не парсим страницу заново
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
# ИНГОССТРАХ
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

# Таблица водителей Ингос: строки и центры колонок (из скана бланка).
# Если ФИО/права съедут вбок — правь только числа центров ниже.
INGOS_DRIVER_ROWS = [(483.44, 495.51), (496.01, 508.08), (508.58, 520.65),
                     (521.15, 533.22), (533.72, 545.79)]
INGOS_DRIVER_COLS = {"fio": (220.0, 350.0), "license": (445.7, 88.0), "kbm": (537.8, 60.0)}

def get_font_name(font_str):
    if "Tahoma" in font_str:
        return "thmb" if "Bold" in font_str or "Bd" in font_str else "thm"
    if "Times" in font_str:
        return "tnewb" if "Bold" in font_str else "tnew"
    return "thm"

def int_to_rgb(c):
    return ((c >> 16) & 255) / 255.0, ((c >> 8) & 255) / 255.0, (c & 255) / 255.0

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

    # ВСЁ время считаем по Москве (иначе ночью даты разъезжаются на день)
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

    # НОМЕР ПОЛИСА: пусто в JSON -> НЕ трогаем то, что в шаблоне
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
            y0, y1 = INGOS_DRIVER_ROWS[i]
            for col, (cx, w) in INGOS_DRIVER_COLS.items():
                all_fields[f"driver{i+1}_{col}"] = (1, [cx - w / 2, y0, cx + w / 2, y1])
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

            is_center = (key in CENTER_FIELDS_INGOS) or key.startswith("driver")
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
# ИНТЕРФЕЙС
# =========================================================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn_alfa = types.KeyboardButton("🔴 АльфаСтрахование")
    btn_ingo = types.KeyboardButton("🔵 Ингосстрах")
    markup.add(btn_alfa, btn_ingo)
    bot.send_message(message.chat.id, "👋 Привет! Выбери страховую компанию на клавиатуре внизу:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["🔴 АльфаСтрахование", "🔵 Ингосстрах"])
def handle_company_choice(message):
    if "Альфа" in message.text:
        user_choices[message.from_user.id] = "alfa"
        bot.reply_to(message, "✅ Выбрано: *АльфаСтрахование*.\n\nТеперь пришли мне JSON с данными.", parse_mode='Markdown')
    else:
        user_choices[message.from_user.id] = "ingo"
        bot.reply_to(message, "✅ Выбрано: *Ингосстрах*.\n\nТеперь пришли мне JSON с данными.", parse_mode='Markdown')

@bot.message_handler(content_types=['text'])
def handle_json(message):
    if message.text in ["🔴 АльфаСтрахование", "🔵 Ингосстрах"]:
        return

    insurer_key = user_choices.get(message.from_user.id, "alfa")
    insurer_name = "АльфаСтрахование"
