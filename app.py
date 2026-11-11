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

FONT_REG_OBJ = pymupdf.Font(fontbuffer=REG_BUF)
FONT_BLD_OBJ = pymupdf.Font(fontbuffer=BLD_BUF)

# ТВОЙ РАБОЧИЙ КОД АЛЬФЫ (без изменений)
FIELDS = {
    "policyholder_fio":        (1, [16.0, 306.65, 230.53, 318.83], "reg",  11),
    "owner_fio":               (1, [16.0, 348.83, 230.86, 361.01], "reg",  11),
    "marka":                   (1, [64.69, 402.65, 133.3, 414.83], "reg",  11),
    "model":                   (1, [90.89, 417.65, 140.52, 429.83], "reg",  11),
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
    "kt":                      (1, [88.0, 703.77, 120.0, 711.52],    "reg",  7),
    "kbm":                     (1, [143.0, 703.77, 174.0, 711.52],   "reg",  7),
    "kvs":                     (1, [199.0, 703.77, 230.0, 711.52],   "reg",  7),
    "ko":                      (1, [256.0, 703.77, 290.0, 711.52],   "reg",  7),
    "ks":                      (1, [315.0, 703.77, 349.0, 711.52],   "reg",  7),
    "kp":                      (1, [373.0, 703.77, 407.0, 711.52],   "reg",  7),
    "km":                      (1, [428.0, 703.77, 465.0, 711.52],   "reg",  7),
    "premium_total":           (1, [500.0, 703.77, 560.0, 711.52],   "reg",  7),
}

CENTER_FIELDS = {
    "premium_thousands", "premium_hundreds", "premium_kop",
    "tb", "kt
