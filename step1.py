import csv
import requests
import re

# -----------------------------
# 配置
# -----------------------------
ANKI_CONNECT_URL = 'http://localhost:8765'  # AnkiConnect 地址
OUTPUT_CSV = 'anki_words_list.csv'          # 输出的去重单词列表 CSV

# -----------------------------
# 功能函数
# -----------------------------

def get_all_notes():
    """获取所有卡片的 Note ID"""
    payload = {"action": "findNotes", "version": 6, "params": {"query": ""}}
    response = requests.post(ANKI_CONNECT_URL, json=payload).json()
    note_ids = response.get('result', [])
    return note_ids

def get_notes_info(note_ids):
    """获取所有 Note 的详细信息"""
    if not note_ids:
        return []
    payload = {"action": "notesInfo", "version": 6, "params": {"notes": note_ids}}
    response = requests.post(ANKI_CONNECT_URL, json=payload).json()
    notes_info = response.get('result', [])
    return notes_info

def extract_words_from_notes(notes_info):
    """从所有字段内容中提取单词，去重并小写"""
    words_set = set()
    for note in notes_info:
        for field_value in note['fields'].values():
            text = field_value.get('value', '')
            field_words = re.findall(r'\b[a-zA-Z]+\b', text)
            words_set.update([w.lower() for w in field_words])
    return words_set

def export_words_to_csv(words_set, output_file):
    """将去重单词列表导出到 CSV"""
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Word'])
        for word in sorted(words_set):
            writer.writerow([word])
    print(f"已生成去重单词列表 CSV: {output_file}, 共 {len(words_set)} 个单词")

# -----------------------------
# 主流程
# -----------------------------
def main():
    # 1. 获取所有 Note ID
    note_ids = get_all_notes()
    print(f"获取到 {len(note_ids)} 张卡片")

    # 2. 获取所有 Note 信息
    notes_info = get_notes_info(note_ids)

    # 3. 提取所有单词
    words_set = extract_words_from_notes(notes_info)
    print(f"提取到 {len(words_set)} 个去重单词")

    # 4. 导出 CSV
    export_words_to_csv(words_set, OUTPUT_CSV)

# -----------------------------
# 执行
# -----------------------------
if __name__ == '__main__':
    main()