from ebooklib import epub
from bs4 import BeautifulSoup
from collections import Counter
import re
import csv

def extract_words_from_epub(epub_path, output_csv):
    # 读取 epub 文件
    book = epub.read_epub(epub_path)

    texts = []
    for item in book.get_items():
        if item.get_type() == 9:  # 文本类型 (XHTML)
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            texts.append(soup.get_text())

    # 合并所有章节的文字
    full_text = " ".join(texts)

    # 提取单词（包含英文、西语字符）
    words = re.findall(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+", full_text)

    # 统一为小写
    words = [w.lower() for w in words]

    # 统计词频
    counter = Counter(words)

    # 保存为 CSV 文件
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["word", "count"])
        for word, freq in counter.most_common():
            writer.writerow([word, freq])

    print(f"✅ 处理完成！结果已保存到 {output_csv}")

if __name__ == "__main__":
    extract_words_from_epub("harry.epub", "word_frequency.csv")