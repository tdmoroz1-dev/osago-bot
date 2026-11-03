import telebot
import pymupdf
import os, datetime, json, io, gc
from flask import Flask
import threading

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    exit(1)

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

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

COMMON_FIELDS = {
    "policyholder_fio":        (1, [16.0, 306.61, 213.11, 318.79], "reg",  11),
    "owner_fio":               (1, [16.0, 348.79, 213.11, 360.97], "reg",  11),
    "marka":                   (1, [64.69, 402.65, 133.3, 414.83], "reg",  11),
    "model":                   (1, [90.89, 417.65, 140.52, 429.83], "reg",  11),
    "vin":                     (1, [201.46, 413.15, 302.75, 425.33], "reg", 11),
    "gosnomer":                (1, [491.31, 413.15, 546.83, 425.33], "reg", 11),
    "pts_series":              (1, [411.07, 444.77, 446.77, 452.52], "bold", 7),
    "pts_number":              (1, [499.87, 444.77, 520.83, 452.52], "bold", 7),
    "premium_rub":             (1, [450.0, 56.65, 500.0, 68.83],    "bold", 11),
    "premium_kop":             (1, [510.0, 56.65, 525.5, 68.83],    "bold", 11),
    "policy_series":           (1, [259.0, 88.47, 282.8, 100.65],    "bold", 11),
    "policy_number":           (1, [349.0, 88.47, 403.9, 100.65],    "bold", 11),
    
    # Расширенные рамки для дат, чтобы захватить все цифры
    "date_start":              (1, [440.0, 187.21, 580.0, 197.18], "reg",  9),
    "date_end":                (1, [440.0, 207.21, 580.0, 217.18], "reg",  9),
    "date_period_start":       (1, [20.0, 252.21, 160.0, 262.18],    "reg",  9),
    "date_period_end":         (1, [160.0, 252.21, 300.0, 262.18],   "reg",  9),
    "date_issue1":             (1, [100.0, 754.3, 145.0, 762.05],   "reg",  7),
    "date_issue2":             (1, [220.0, 754.3, 265.0, 762.05],  "reg",  7),
    "date_design_1":           (1, [390.0, 730.34, 420.0, 739.2],  "reg",  8),
    "date_design_2":           (1, [420.0, 730.34, 520.0, 739.2],   "reg",  8),
    
    "trailer_old_x":           (1, [220.19, 375.57, 226.01, 382.21], "reg",  6),
    "trailer_new_x":           (1, [248.00, 375.57, 254.00, 382.21], "reg",  6),
    "premium_in_words":        (1, [240.0, 730.34, 400.0, 739.2],  "reg",  8),
    
    # Расширенные рамки для коэффициентов
    "tb":                      (1, [20.0, 703.77, 65.0, 711.52],     "reg",  7),
    "kt":                      (1, [85.0, 703.77, 125.0, 711.52],    "reg",  7),
    "kbm":                     (1, [140.0, 703.77, 180.0, 711.52],   "reg",  7),
    "kvs":                     (1, [195.0, 703.77, 235.0, 711.52],   "reg",  7),
    "ko":                      (1, [250.0, 703.77, 295.0, 711.52],   "reg",  7),
    "ks":                      (1, [310.0, 703.77, 355.0, 711.52],   "reg",  7),
    "kp":                      (1, [370.0, 703.77, 415.0, 711.52],   "reg",  7),
    "km":                      (1, [430.0, 703.77, 475.0, 711.52],   "reg",  7),
    "premium_total":           (1, [490.0, 703.77, 570.0, 711.52],   "reg",  7),
}

CENTER_FIELDS = {
    "premium_rub", "premium_kop", "tb", "kt", "kbm", "kvs", "ko", "ks", "kp", "km",
    "premium_total", "trailer_new_x", "policy_series", "policy_number"
}
DECIMAL_FIELDS = ["kt", "kbm", "kvs", "ko", "ks", "kp", "km"]

LIMITED_CHECKBOX = (1, [392.97, 517.61, 398.03, 525.36], "reg", 7)
UNLIMITED_CHECKBOX = (1, [392.97, 507.08, 398.03, 514.83], "reg", 7)

# ТОЧНЫЕ КООРДИНАТЫ ДЛЯ ТАБЛИЦЫ ВОДИТЕЛЕЙ (Чтобы не налезало на номер строки)
DRIVER_FIELDS = [
    # Ряд 1
    (1, [32.0, 555.9, 330.0, 563.65], "driver1_fio", "reg", 7, False),
    (1, [350.0, 555.9, 480.0, 563.65], "driver1_license", "reg", 7, False),
    (1, [495.0, 555.9, 560.0, 563.65], "driver1_kbm", "reg", 7, True),
    # Ряд 2
    (1, [32.0, 567.27, 330.0, 575.02], "driver2_fio", "reg", 7, False),
    (1, [350.0, 567.27, 480.0, 575.02], "driver2_license", "reg", 7, False),
    (1, [495.0, 567.27, 560.0, 575.02], "driver2_kbm", "reg", 7, True),
    # Ряд 3
    (1, [32.0, 577.27, 330.0, 585.02], "driver3_fio", "reg", 7, False),
    (1, [350.0, 577.27, 480.0, 585.02], "driver3_license", "reg", 7, False),
    (1, [495.0, 577.27, 560.0, 585.02], "driver3_kbm", "reg", 7, True),
    # Ряд 4
    (1, [32.0, 587.27, 330.0, 595.02], "driver4_fio", "reg", 7, False),
    (1, [350.0, 587.27, 480.0, 595.02], "driver4_license", "reg", 7, False),
    (1, [495.0, 587.27, 560.0, 595.02], "driver4_kbm", "reg", 7, True),
    # Ряд 5
    (1, [32.0, 597.27, 330.0, 605.02], "driver5_fio", "reg", 7, False),
    (1, [350.0, 597.27, 480.0, 605.02], "driver5_license", "reg", 7, False),
    (1, [495.0, 597.27, 560.0, 605.02], "driver5_kbm", "reg", 7, True),
]

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

def fill_pdf_to_memory(data):
    drivers = data.get("drivers", [])
    is_limited = len(drivers) > 0
    
    template_name = "template_limited.pdf" if is_limited else "template.pdf"
    doc = pymupdf.open(template_name)
    
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

    data["premium_rub"] = str(data.get("premium_thousands", "")) + str(data.get("premium_hundreds", ""))
    data["premium_total"] = str(data.get("premium_total_thousands", "")) + str(data.get("premium_total_kop", ""))

    all_fields = dict(COMMON_FIELDS)
    all_fields["limited_checkbox"] = LIMITED_CHECKBOX
    all_fields["unlimited_checkbox"] = UNLIMITED_CHECKBOX
    data["limited_checkbox"] = "X" if is_limited else ""
    data["unlimited_checkbox"] = "" if is_limited else "X"
    
    if is_limited:
        for i, driver in enumerate(drivers[:5]):
            idx = i + 1
            data[f"driver{idx}_fio"] = driver.get("fio", "")
            data[f"driver{idx}_license"] = driver.get("license", "")
            data[f"driver{idx}_kbm"] = driver.get("kbm", "")
            try:
                data[f"driver{idx}_kbm"] = f"{float(data[f'driver{idx}_kbm']):.2f}"
            except:
                pass

        for df in DRIVER_FIELDS:
            all_fields[df[2]] = (df[0], df[1], df[3], df[4])
            if df[5]: CENTER_FIELDS.add(df[2])

    by_page = {}
    for key, (pno, rect, fkey, size) in all_fields.items():
        if key not in data: continue
        val = str(data[key]).strip()
        
        if key in DECIMAL_FIELDS:
            try: val = f"{float(val):.2f}"
            except: pass
                
        if key in ["policy_series", "policy_number"] and not val: continue
        by_page.setdefault(pno, []).append((rect, val, fkey, size, key))

    for pno, items in by_page.items():
        page = doc[pno - 1]
        to_delete, inserts = [], []
        for (rect, val, fkey, size, key) in items:
            spans = collect_spans(page, rect)
            if key == "trailer_old_x" and not spans: continue
            if spans:
                for sp in spans: to_delete.append(sp["bbox"])
            
            # ДЛЯ ДАТ ТЕПЕРЬ ВСТАВЛЯЕМ ЦЕЛОЙ СТРОКОЙ (чтобы избежать разрывов)
            if key in ["date_start", "date_end", "date_period_start", "date_period_end"]:
                if not spans: continue
                # Убираем старые данные и ставим новые одной строкой с пробелами
                clean_val = " ".join(list(val.replace(".", "").replace(" ", "")))
                r = pymupdf.Rect(rect)
                inserts.append((r, clean_val, fkey, size, False, "box"))
            elif key in ["date_issue1", "date_issue2", "date_design_1", "date_design_2"]:
                if not spans: continue
                r = pymupdf.Rect(rect)
                inserts.append((r, val, fkey, size, False, "box"))
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
            r, val, fkey, size, is_center, _ = item
            fname = "tnewb" if fkey == "bold" else "tnew"
            
            if is_center:
                f_obj = FONT_BLD_OBJ if fkey == "bold" else FONT_REG_OBJ
                text_w = f_obj.text_length(val, fontsize=size)
                x_new = r.x0 + (r.width - text_w) / 2
                if text_w >= r.width: x_new = r.x0
            else:
                x_new = r.x0
                
            baseline = r.y1 - 0.18 * size
            if val: page.insert_text((x_new, baseline), val, fontname=fname, fontsize=size, color=(0,0,0))

    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    gc.collect()
    return pdf_bytes

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Пришли мне JSON.\n\nДля ограниченного полиса добавь массив drivers, например:\n\"drivers\": [\n  {\"fio\": \"ИВАНОВ ИВАН\", \"license\": \"99 88 123456\", \"kbm\": \"0.95\"}\n]")

@bot.message_handler(content_types=['text'])
def handle_json(message):
    raw_text = message.text.strip().replace("```json", "").replace("```", "").strip()
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

    bot.reply_to(message, "⏳ Генерирую полис...")
    try:
        pdf_data = fill_pdf_to_memory(data)
        owner = data.get("owner_fio", "Полис_ОСАГО").strip()
        safe_name = "".join([c for c in owner if c not in r'\/:*?"<>|']).strip() or "Полис_ОСАГО"
        
        pdf_file = io.BytesIO(pdf_data)
        pdf_file.name = f"{safe_name}.pdf"
        bot.send_document(message.chat.id, pdf_file)
    except Exception as e:
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
