import csv
import requests
from tqdm import tqdm
import os
import time

# -----------------------------
# 配置
# -----------------------------
DEEPL_API_KEY = "460e5508-e201-4d3d-8d0e-51efa83dba77:fx"
DEEPL_URL = "https://api-free.deepl.com/v2/translate"
INPUT_CSV = "deepwork.csv"
OUTPUT_CSV = "deepwork_translated.csv"
TARGET_LANG = "ZH"   # 西语 -> 中文
BATCH_SIZE = 50      # 每批请求多少句

# -----------------------------
# 批量调用 DeepL
# -----------------------------
def translate_batch(sentences, target_lang="ZH"):
    params = {
        "auth_key": DEEPL_API_KEY,
        "target_lang": target_lang,
        "source_lang": "ES"
    }
    data = list(params.items()) + [("text", s) for s in sentences]
    response = requests.post(DEEPL_URL, data=data, timeout=20)
    response.raise_for_status()
    result = response.json()
    return [t["text"] for t in result["translations"]]

# -----------------------------
# 主流程
# -----------------------------
# 读取原始 CSV
with open(INPUT_CSV, "r", encoding="utf-8") as infile:
    reader = list(csv.DictReader(infile))

# 读取已翻译 CSV，如果存在
translated_dict = {}
if os.path.exists(OUTPUT_CSV):
    with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
        out_reader = csv.DictReader(f)
        for row in out_reader:
            translated_dict[row["sentence"]] = row.get("translation", "")

# 筛选需要翻译的句子
to_translate = [row for row in reader if row["sentence"] not in translated_dict or not translated_dict[row["sentence"]]]

# 批量翻译并显示进度
for i in tqdm(range(0, len(to_translate), BATCH_SIZE), desc="翻译进度"):
    batch = [row["sentence"] for row in to_translate[i:i+BATCH_SIZE]]
    batch_translations = translate_batch(batch)
    for s, t in zip(batch, batch_translations):
        translated_dict[s] = t

# 写回 CSV（保留原始顺序）
with open(OUTPUT_CSV, "w", encoding="utf-8", newline="") as outfile:
    fieldnames = list(reader[0].keys()) + ["translation"]
    writer = csv.DictWriter(outfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for row in reader:
        row["translation"] = translated_dict.get(row["sentence"], "")
        writer.writerow(row)

print(f"✅ 翻译完成，结果保存在 {OUTPUT_CSV}")