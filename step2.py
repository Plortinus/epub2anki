import re
import csv
from ebooklib import epub
from bs4 import BeautifulSoup
from collections import Counter
from tqdm import tqdm
import spacy

# ================= 初始化 =================
nlp = spacy.load("es_core_news_sm")  # 轻量西语模型

# -----------------------------
# 读取已知单词
# -----------------------------
def load_known_words(path):
    words = set()
    try:
        with open(path, encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    words.add(row[0].strip().lower())
    except FileNotFoundError:
        print(f"⚠️ 文件 {path} 未找到，返回空集合")
    return words

# -----------------------------
# 加载停用词
# -----------------------------
def load_stopwords(path):
    stopwords = set()
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                w = line.strip().lower()
                if w:
                    stopwords.add(w)
    except FileNotFoundError:
        print(f"⚠️ 文件 {path} 未找到，返回空集合")
    return stopwords

# -----------------------------
# 提取 EPUB 文本
# -----------------------------
def extract_text_from_epub(epub_path):
    book = epub.read_epub(epub_path)
    texts = []
    for item in book.get_items():
        if item.get_type() == 9:  # 文本类型
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            texts.append(soup.get_text())
    return "\n".join(texts)

# -----------------------------
# 主函数
# -----------------------------
def extract_unknown_words_with_pos(epub_path, known_csv, stopwords_txt, output_csv):
    known_words = load_known_words(known_csv)
    stopwords = load_stopwords(stopwords_txt)

    print("📌 提取文本...")
    full_text = extract_text_from_epub(epub_path)

    print("📌 分词...")
    words = re.findall(r'\b[^\W\d_]+\b', full_text, flags=re.UNICODE)
    words = [w.lower() for w in words]

    print("📌 筛选生词...")
    unknown_words = [w for w in words if w not in known_words and w not in stopwords]

    counter = Counter(unknown_words)
    sorted_words = sorted(counter.items(), key=lambda x: x[1], reverse=True)
    print(f"📌 生词数量: {len(sorted_words)}")

    # ================= 获取词性 =================
    print("📌 获取词性...")
    # 批量处理，减少内存压力
    all_unknowns = [word for word, freq in sorted_words]
    word_pos_map = {}
    for i in tqdm(range(0, len(all_unknowns), 5000)):
        batch = all_unknowns[i:i+5000]
        doc = nlp(" ".join(batch))
        for token in doc:
            word_pos_map[token.text.lower()] = token.pos_

    # ================= 写入 CSV =================
    print(f"💾 输出 CSV: {output_csv}")
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["word", "frequency", "pos"])
        for word, freq in sorted_words:
            pos = word_pos_map.get(word, "X")  # 如果没找到词性，标记为 X
            writer.writerow([word, freq, pos])

# -----------------------------
# 脚本入口
# -----------------------------
if __name__ == "__main__":
    extract_unknown_words_with_pos(
        "deepwork.epub",
        "anki_words_list.csv",
        "stopwords_es.txt",
        "deepwork_unknown_words_pos.csv"
    )