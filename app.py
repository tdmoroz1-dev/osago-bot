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

FIELDS = {
    "policyholder_fio":        (1, [22.0, 306.61, 250.0, 318.79], "reg",  11),
    "owner_fio":               (1, [22.0, 348.79, 250.0, 360.97], "reg",  11),
    "marka":                   (1, [60.0, 402.65, 150.0, 414.83], "reg",  11),
    "model":                   (1, [85.0, 417.65, 160.0, 429.83], "reg",  11),
    "vin":                     (1, [200.0, 413.15, 315.0, 425.33], "reg", 11),
    "gosnomer":                (1, [480.0, 413.15, 560.0, 425.33], "reg", 11),
    "pts_series":              (1, [405.0, 444.77, 450.0, 452.52], "bold", 7),
    "pts_number":              (1, [490.0, 444.77, 530.0, 452.52], "bold", 7),
    "premium_rub":             (1, [440.0, 56.65, 500.0, 68.83],    "bold", 11),
    "premium_kop":             (1, [505.0, 56.65, 530.0, 68.83],    "bold", 11),
    "policy_series":           (1, [259.0, 88.47, 282.8, 100.65],    "bold", 11),
    "policy_number":           (1, [349.0, 88.47, 403.9, 100.65],    "bold", 11),
    
    "date_start":              (1, [440.0, 187.21, 570.0, 197.18], "reg",  9),
    "date_end":                (1, [440.0, 207.21, 570.0, 217.18], "reg",  9),
    "date_period_start":       (1, [25.0, 252.21, 150.0, 262.18],    "reg",  9),
    "date_period_end":         (1, [160.0, 252.21, 285.0, 262.18],   "reg",  9),
    
    "date_issue1":             (1, [100.0, 754.3, 145.0, 762.05],   "reg",  7),
    "date_issue2":             (1, [220.0, 754.3, 265.0, 762.05],  "reg",  7),
    "footer_text":             (1, [15.0, 730.34, 550.0, 739.2],  "reg",  8),
    "trailer_old_x":           (1, [220.19, 375.57, 226.01, 382.21], "reg",  6),
    "trailer_new_x":           (1, [248.00, 375.57, 254.00, 382.21], "reg",  6),
    "tb":                      (1, [33.0, 703.77, 53.0, 711.52],     "reg",  7),
    "kt":                      (1, [93.0, 703.77, 113.0, 711.52],    "reg",  7),
    "kbm":                     (1, [148.0, 703.77, 169.0, 711.52],   "reg",  7),
    "kvs":                     (1, [206.0, 703.77, 226.0, 711.52],   "reg",  7),
    "ko":                      (1, [264.0, 703.77, 284.0, 711.52],   "reg",  7),
    "ks":                      (1, [322.0, 703.77, 342.0, 711.52],   "reg",  7),
    "kp":                      (1, [380.0, 703.77, 400.0, 711.52],   "reg",  7),
    "km":                      (1, [438.0, 703.77, 458.0, 711.52],   "reg",  7),
    "premium_total":           (1, [495.0, 703.77, 563.0, 711.52],   "reg",  7),
}

CENTER_FIELDS = {
    "premium_rub", "premium_kop", "tb", "kt", "kbm", "kvs", "ko", "ks", "kp", "km",
    "premium_total", "trailer_new_x", "policy_series", "policy_number",
    "vin", "gosnomer", "pts_series", "pts_number", "date_issue1", "date_issue2"
}
DECIMAL_FIELDS = ["kt", "kbm", "kvs", "ko", "ks", "kp", "km"]

LIMITED_CHECKBOX = (1, [392.97, 517.61, 398.03, 525.36], "reg", 7)
UNLIMITED_CHECKBOX = (1, [392.97, 507.08, 398.03, 514.83], "reg", 7)

DRIVER_FIELDS = [
    (1, [30.0, 555.9, 340.0, 563.65], "driver1_fio", "reg", 7, True),
    (1, [360.0, 555.75, 425.0, 563.5], "driver1_license", "reg", 7, True),
    (1, [500.0, 555.9, 540.0, 563.65], "driver1_kbm", "reg", 7, True),
    (1, [30.0, 567.27, 340.0, 575.02], "driver2_fio", "reg", 7, True),
    (1, [360.0, 567.27, 425.0, 575.02], "driver2_license", "reg", 7, True),
    (1, [500.0, 567.27, 540.0, 575.02], "driver2_kbm", "reg", 7, True),
    (1, [30.0, 577.27, 340.0, 585.02], "driver3_fio", "reg", 7, True),
    (1, [360.0, 577.27, 425.0, 585.02], "driver3_license", "reg", 7, True),
    (1, [500.0, 577.27, 540.0, 585.02], "driver3_kbm", "reg", 7, True),
    (1, [30.0, 587.27, 340.0, 595.02], "driver4_fio", "reg", 7, True),
    (1, [360.0, 587.27, 425.0, 595.02], "driver4_license", "reg", 7, True),
    (1, [500.0, 587.27, 540.0, 595.02], "driver4_kbm", "reg", 7, True),
    (1, [30.0, 597.27, 340.0, 605.02], "driver5_fio", "reg", 7, True),
    (1, [360.0, 597.27, 425.0, 605.02], "driver5_license", "reg", 7, True),
    (1, [500.0, 597.27, 540.0, 605.02], "driver5_kbm", "reg", 7, True),
]

# ВОЗВРАЩАЕМ ПРОПАВШИЕ ФУНКЦИИ
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
    raw_drivers = data.get("drivers", [])
    valid_drivers = [d for d in raw_drivers if str(d.get("fio", "")).strip() and str(d.get("license", "")).strip()]
    is_limited = len(valid_drivers) > 0
    
    doc = pymupdf.open("template.pdf")
    
    tz = datetime.timezone(datetime.timedelta(hours=3))
    today = datetime.datetime.now(tz).date()
    try: next_year = today.replace(year=today.year + 1)
    except ValueError: next_year = today.replace(year=today.year + 1, day=28)
    end_date = next_year - datetime.timedelta(days=1)
    
    d_start = " ".join(list(today.strftime("%d.%m.%Y")))
    d_end = " ".join(list(end_date.strftime("%d.%m.%Y")))
    
    data["date_issue1"] = today.strftime("%d.%m.%Y")
    data["date_issue2"] = today.strftime("%d.%m.%Y")
    
    total_str = str(data.get("premium_total_thousands", "")) + str(data.get("premium_total_kop", ""))
    if "." in total_str:
        rub_str, kop_str = total_str.split(".")
    else:
        rub_str = str(data.get("premium_thousands", "")) + str(data.get("premium_hundreds", ""))
        kop_str = str(data.get("premium_kop", ""))
    
    if len(kop_str) == 1: kop_str = "0" + kop_str
    if len(kop_str) > 2: kop_str = kop_str[:2]

    data["premium_rub"] = rub_str
    data["premium_kop"] = kop_str
    data["premium_total"] = f"{rub_str}.{kop_str}"
    data["footer_text"] = f"ТС в режиме использования такси не подлежит. Страховая премия: {rub_str} рублей {kop_str} копеек. Дата оформления: {today.strftime('%d.%m.%Y 00:00:00 UTC+03:00.')}"

    all_fields = dict(FIELDS)
    all_fields["limited_checkbox"] = LIMITED_CHECKBOX
    all_fields["unlimited_checkbox"] = UNLIMITED_CHECKBOX
    
    data["limited_checkbox"] = "X" if is_limited else ""
    data["unlimited_checkbox"] = "" if is_limited else "X"
    
    for i in range(1, 6):
        data[f"driver{i}_fio"] = ""
        data[f"driver{i}_license"] = ""
        data[f"driver{i}_kbm"] = ""
        
    if is_limited:
        for i, driver in enumerate(valid_drivers[:5]):
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
        val = str(data.get(key, "")).strip()
        if key in DECIMAL_FIELDS:
            try: val = f"{float(val):.2f}"
            except: pass
        by_page.setdefault(pno, []).append((rect, val, fkey, size, key))

    for pno, items in by_page.items():
        page = doc[pno - 1]
        to_delete, inserts = [], []
        
        for (rect, val, fkey, size, key) in items:
            r = pymupdf.Rect(rect)
            spans = collect_spans(page, r)
            
            if key == "date_start": val = d_start
            elif key == "date_end": val = d_end
            elif key == "date_period_start": val = d_start
            elif key == "date_period_end": val = d_end

            if key in ["date_period_start", "date_period_end"]:
                if not spans: continue
                char_boxes = []
                for sp in spans:
                    text = sp['text'].strip()
                    if not all(c.isdigit() or c == '.' for c in text):
                        continue
                    x0, y0, x1, y1 = sp['bbox']
                    if len(text) == 1: 
                        char_boxes.append((x0, y0, x1, y1))
                    else:
                        w = (x1 - x0) / len(text)
                        for i in range(len(text)): 
                            char_boxes.append((x0 + i*w, y0, x0 + (i+1)*w, y1))
                char_boxes.sort(key=lambda b: b[0])
                clean_val = val.replace(" ", "")
                for i, ch in enumerate(clean_val):
                    if i >= len(char_boxes): break
                    x0, y0, x1, y1 = char_boxes[i]
                    to_delete.append(pymupdf.Rect([x0, y0, x1, y1]))
                    inserts.append((x0, y1 - 0.18 * size, ch, fkey, size, "char"))
            
            elif val:
                to_delete.append(r)
                is_center = key in CENTER_FIELDS
                inserts.append((r, val, fkey, size, is_center, "box"))
            else:
                if key.startswith("driver") or key in ["trailer_old_x", "unlimited_checkbox", "limited_checkbox"]:
                    if spans:
                        for sp in spans: to_delete.append(sp["bbox"])

        if to_delete:
            for bb in to_delete: page.add_redact_annot(bb, fill=False)
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
                if not val: continue
                fname = "tnewb" if fkey == "bold" else "tnew"
                
                if is_center:
                    f_obj = FONT_BLD_OBJ if fkey == "bold" else FONT_REG_OBJ
                    text_w = f_obj.text_length(val, fontsize=size)
                    x_new = r.x0 + (r.width - text_w) / 2
                    if text_w >= r.width: x_new = r.x0
                else:
                    x_new = r.x0
                    
                baseline = r.y1 - 0.18 * size
                page.insert_text((x_new, baseline), val, fontname=fname, fontsize=size, color=(0,0,0))

    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()
    gc.collect()
    return pdf_bytes

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Пришли мне JSON.")

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

    valid_drivers = [d for d in data.get("drivers", []) if str(d.get("fio", "")).strip() and str(d.get("license", "")).strip()]
    status_msg = "Ограниченный" if len(valid_drivers) > 0 else "Неограниченный"
    
    bot.reply_to(message, f"Найдено водителей: {len(valid_drivers)}. Тип полиса: {status_msg}. ⏳ Генерирую...")
    
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
