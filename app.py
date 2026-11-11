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

# Хранилище выбора пользователей
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

FONT_REG_OBJ = pymupdf.Font(fontbuffer=REG_BUF)
FONT_BLD_OBJ = pymupdf.Font(fontbuffer=BLD_BUF)

# =========================================================================
# ТВОЙ ИДЕАЛЬНЫЙ КОД АЛЬФЫ (НЕ ТРОНУТ НИ ОДИН СИМВОЛ)
# =========================================================================
FIELDS = {
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

CENTER_FIELDS = {
    "marka", "model",
    "premium_thousands", "premium_hundreds", "premium_kop",
    "tb", "kt", "kbm", "kvs", "ko", "ks", "kp", "km",
    "trailer_new_x", "policy_series", "policy_number",
    "premium_total"
}
DECIMAL_FIELDS = ["kt", "kbm", "kvs", "ko", "ks", "kp", "km"]

DRIVER_ROWS = [(555.9, 563.65), (567.27, 575.02), (577.27, 585.02),
               (587.27, 595.02), (597.27, 605.02)]
DRIVER_DY = 1.8
DRIVER_COLS = {"fio": (187.2, 310.0), "license": (392.8, 65.0), "kbm": (518.0, 40.0)}

TOTAL_LABELS = {"tb": "ТБ", "kt": "КТ", "kbm": "КБМ", "kvs": "КВС", "ko": "КО",
                "ks": "КС", "kp": "КП", "km": "КМ", "premium_total": "Итого"}

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

def is_inside(inner, outer):
    r, o = pymupdf.Rect(inner), pymupdf.Rect(outer)
    return (r.x0 >= o.x0 - 0.5 and r.y0 >= o.y0 - 0.5 and r.x1 <= o.x1 + 0.5 and r.y1 <= o.y1 + 0.5)

def collect_spans(page, area):
    out = []
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0: continue
        for ln in b.get("lines", []):
            for sp in ln.get("spans", []):
                if sp.get("text", "").strip() and is_inside(sp["bbox"], area):
                    out.append(sp)
    return out

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
    for key, (pno, rect, fkey, size) in FIELDS.items():
        if key not in data: continue
        val = str(data[key]).strip()
        
        if key in DECIMAL_FIELDS:
            try: val = f"{float(val):.2f}" 
            except ValueError: pass
                
        if key in ["policy_series", "policy_number"] and not val: continue
        by_page.setdefault(pno, []).append((rect, val, fkey, size, key))

    for pno, items in by_page.items():
        page = doc[pno - 1]
        centers = label_centers(page)
        to_delete, inserts = [], []
        for (rect, val, fkey, size, key) in items:
            rect = snap_rect(rect, key, centers)
            spans = collect_spans(page, rect)
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
                    inserts.append((x0, y1 - 0.22 * size, ch, fkey, size, "char"))
            else:
                r = pymupdf.Rect(rect)
                is_center = key in CENTER_FIELDS
                inserts.append((r, val, fkey, size, is_center, "box"))

        if to_delete:
            for bb in to_delete: page.add_redact_annot(pymupdf.Rect(bb), fill=False)
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)

        page.insert_font(fontname="tnew", fontbuffer=REG_BUF)
        page.insert_font(fontname="tnewb", fontbuffer=BLD_BUF)

        for item in inserts:
            if item[-1] == "char":
                x0, baseline, val, fkey, size, _ = item
                fname = "tnewb" if fkey == "bold" else "tnew"
                if val: page.insert_text((x0, baseline), val, fontname=fname, fontsize=size, color=(0,0,0))
            elif item[-1] == "box":
                r, val, fkey, size, is_center, _ = item
                fname = "tnewb" if fkey == "bold" else "tnew"
                
                if is_center:
                    f_obj = FONT_BLD_OBJ if fkey == "bold" else FONT_REG_OBJ
                    text_w = f_obj.text_length(val, fontsize=size)
                    x_new = r.x0 + (r.width - text_w) / 2
                    if text_w >= r.width: x_new = r.x0
                else:
                    x_new = r.x0
                    
                baseline = r.y1 - 0.22 * size
                if val: page.insert_text((x_new, baseline), val, fontname=fname, fontsize=size, color=(0,0,0))

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

    all_fields = dict(FIELDS)
    
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
        try:
            data[f"driver{idx}_kbm"] = f"{float(d.get('kbm', '1.00')):.2f}"
        except:
            data[f"driver{idx}_kbm"] = "1.00"

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
        centers = label_centers(page)
        to_delete, inserts = [], []
        for (rect, val, fkey, size, key) in items:
            rect = snap_rect(rect, key, centers)
            r = pymupdf.Rect(rect)
            spans = collect_spans(page, r)
            
            if key in ["trailer_old_x", "unlimited_checkbox", "limited_checkbox"]:
                if spans:
                    for sp in spans: to_delete.append(sp["bbox"])
                if val: 
                    inserts.append((r, val, fkey, size, True, "box"))
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
                    inserts.append((x0, y1 - 0.22 * size, ch, fkey, size, "char"))
            else:
                is_center = True if key.startswith("driver") else (key in CENTER_FIELDS)
                if key.startswith("driver"):
                    r = pymupdf.Rect(r.x0, r.y0 + DRIVER_DY, r.x1, r.y1 + DRIVER_DY)
                inserts.append((r, val, fkey, size, is_center, "box"))

        if to_delete:
            for bb in to_delete: page.add_redact_annot(pymupdf.Rect(bb), fill=False)
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)

        page.insert_font(fontname="tnew", fontbuffer=REG_BUF)
        page.insert_font(fontname="tnewb", fontbuffer=BLD_BUF)

        for item in inserts:
            if item[-1] == "char":
                x0, baseline, val, fkey, size, _ = item
                fname = "tnewb" if fkey == "bold" else "tnew"
                if val: page.insert_text((x0, baseline), val, fontname=fname, fontsize=size, color=(0,0,0))
            elif item[-1] == "box":
                r, val, fkey, size, is_center, _ = item
                fname = "tnewb" if fkey == "bold" else "tnew"
                
                if is_center:
                    f_obj = FONT_BLD_OBJ if fkey == "bold" else FONT_REG_OBJ
                    text_w = f_obj.text_length(val, fontsize=size)
                    x_new = r.x0 + (r.width - text_w) / 2
                    if text_w >= r.width: x_new = r.x0
                else:
                    x_new = r.x0
                    
                baseline = r.y1 - 0.22 * size
                if val: page.insert_text((x_new, baseline), val, fontname=fname, fontsize=size, color=(0,0,0))

    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    gc.collect()
    return pdf_bytes

# =========================================================================
# КОД ДЛЯ ИНГОССТРАХА (Отдельно, чтобы не мешать Альфе)
# =========================================================================
FIELDS_INGOS = {
    "policyholder_fio":        (1, [30.69, 251.8, 500.0, 263.87], "bold", 10),
    "owner_fio":               (1, [28.35, 274.03, 500.0, 286.1], "bold", 10),
    "marka":                   (1, [70.11, 322.47, 160.0, 334.54], "bold", 10),
    "model":                   (1, [92.21, 334.54, 160.0, 346.61], "bold", 10),
    "vin":                     (1, [185.0, 322.9, 440.0, 335.02], "bold", 10),
    "gosnomer":                (1, [477.95, 331.73, 560.0, 343.8], "bold", 10),
    "premium_str":             (1, [470.0, 40.07, 570.0, 52.14], "bold", 10),
    "policy_number_str":       (1, [273.3, 99.02, 440.0, 115.91], "bold", 14),
    "date_end_top":            (1, [506.14, 162.21, 570.0, 171.87], "bold", 8),
    "date_period_str":         (1, [36.55, 223.93, 195.0, 236.0], "bold", 10),
    "pts_doc_line":            (1, [28.35, 363.31, 400.0, 372.96], "reg", 8),
    "date_issue1":             (1, [26.65, 789.27, 300.0, 798.92], "reg", 8),
    "unlimited_checkbox":      (1, [21.25, 420.22, 359.27, 429.87], "reg", 8),
    "limited_checkbox":        (1, [21.25, 429.87, 246.63, 439.52], "reg", 8),
    "trailer_checkbox":        (1, [250.59, 289.5, 300.92, 299.15], "reg", 8),
    "tb":                      (1, [60.0, 667.2, 90.0, 678.07], "reg", 9),
    "kt":                      (1, [140.0, 667.2, 170.0, 678.07], "reg", 9),
    "kbm":                     (1, [190.0, 667.2, 220.0, 678.07], "reg", 9),
    "kvs":                     (1, [240.0, 667.2, 270.0, 678.07], "reg", 9),
    "ko":                      (1, [295.0, 667.2, 325.0, 678.07], "reg", 9),
    "ks":                      (1, [350.0, 667.2, 380.0, 678.07], "reg", 9),
    "kp":                      (1, [400.0, 667.2, 430.0, 678.07], "reg", 9),
    "km":                      (1, [450.0, 667.2, 480.0, 678.07], "reg", 9),
    "premium_total":           (1, [510.0, 667.2, 570.0, 678.07], "reg", 9),
}

def fill_ingos_pdf(data):
    doc = pymupdf.open("template_ingos.pdf")
    today = datetime.date.today()
    try: next_year = today.replace(year=today.year + 1)
    except ValueError: next_year = today.replace(year=today.year + 1, day=28)
    end_date = next_year - datetime.timedelta(days=1)

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

    months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    month_name = months[today.month - 1]
    
    data["premium_str"] = f"{total_rub} руб. {total_kop} коп."
    data["policy_number_str"] = f"№ {data.get('policy_series', '')} {data.get('policy_number', '')}"
    data["date_end_top"] = f"{end_date.strftime('%d.%m.%Y')} г."
    data["date_period_str"] = f"{today.strftime('%d.%m.%Y')} г. по {end_date.strftime('%d.%m.%Y')} г."
    data["pts_doc_line"] = f"Вид документа СВИДЕТЕЛЬСТВО О РЕГИСТРАЦИИ серия {data.get('pts_series', '')} номер {data.get('pts_number', '')}"
    data["date_issue1"] = f"Дата выдачи полиса «{today.day}» {month_name} {today.year} г."
    
    drivers = [d for d in data.get("drivers", []) if str(d.get("fio", "")).strip()]
    if drivers:
        data["unlimited_checkbox"] = "[ ] неограниченного количества лиц..."
        data["limited_checkbox"] = "[V] лиц, допущенных к управлению..."
    else:
        data["unlimited_checkbox"] = "[V] неограниченного количества лиц..."
        data["limited_checkbox"] = "[ ] лиц, допущенных к управлению..."
        
    if data.get("trailer", "").lower() == "нет":
        data["trailer_checkbox"] = "[] да, [X] нет."
    else:
        data["trailer_checkbox"] = "[X] да, [] нет."

    try:
        tot_r = int(float(formatted_total))
        tot_k = int(round((float(formatted_total) - tot_r) * 100))
        data["premium_total"] = f"{tot_r:,}".replace(',', ' ') + f",{tot_k:02d}"
    except: 
        data["premium_total"] = formatted_total

    all_fields = dict(FIELDS_INGOS)
    
    by_page = {}
    for key, (pno, rect, fkey, size) in all_fields.items():
        if key not in data: continue
        val = str(data[key]).strip()
        
        if key in DECIMAL_FIELDS:
            try: val = f"{float(val):.2f}" 
            except ValueError: pass
                
        by_page.setdefault(pno, []).append((rect, val, fkey, size, key))

    for pno, items in by_page.items():
        page = doc[pno - 1]
        to_delete, inserts = [], []
        for (rect, val, fkey, size, key) in items:
            r = pymupdf.Rect(rect)
            spans = collect_spans(page, r)
            
            if spans:
                for sp in spans: to_delete.append(sp["bbox"])
            
            is_center = (key in CENTER_FIELDS) or key == "premium_total"
            inserts.append((r, val, fkey, size, is_center, "box"))

        if to_delete:
            for bb in to_delete: page.add_redact_annot(pymupdf.Rect(bb), fill=False)
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)

        page.insert_font(fontname="tnew", fontbuffer=REG_BUF)
        page.insert_font(fontname="tnewb", fontbuffer=BLD_BUF)

        for item in inserts:
            r, val, fkey, size, is_center, _ = item
            if not val: continue
            fname = "tnewb" if fkey == "bold" else "tnew"
            
            if is_center:
                f_obj = FONT_BLD_OBJ if fkey == "bold" else FONT_REG_OBJ
                text_w = f_obj.text_length(val, fontsize=size)
                x_new = r.x0 + (r.width - text_w) / 2
                if text_w >= r.width: x_new = r.x0
            else:
                x_new = r.x0
                
            baseline = r.y1 - 0.22 * size
            page.insert_text((x_new, baseline), val, fontname=fname, fontsize=size, color=(0,0,0))

    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    gc.collect()
    return pdf_bytes

# =========================================================================
# ИНТЕРФЕЙС БОТА
# =========================================================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_alfa = types.InlineKeyboardButton("🔵 АльфаСтрахование", callback_data="set_alfa")
    btn_ingo = types.InlineKeyboardButton("🟢 Ингосстрах", callback_data="set_ingo")
    markup.add(btn_alfa, btn_ingo)
    
    bot.send_message(message.chat.id, "👋 Привет! Выбери страховую компанию:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_'))
def callback_set_insurer(call):
    insurer_key = call.data.replace('set_', '')
    user_choices[call.from_user.id] = insurer_key
    
    insurer_name = "АльфаСтрахование" if insurer_key == "alfa" else "Ингосстрах"
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id,
        text=f"✅ Выбрано: *{insurer_name}*.\n\nТеперь пришли мне JSON с данными для полиса.",
        parse_mode='Markdown'
    )

@bot.message_handler(content_types=['text'])
def handle_json(message):
    insurer_key = user_choices.get(message.from_user.id, "alfa")
    insurer_name = "АльфаСтрахование" if insurer_key == "alfa" else "Ингосстрах"
    
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
