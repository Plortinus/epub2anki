import re
import csv
from ebooklib import epub
from bs4 import BeautifulSoup
from collections import Counter
import itertools
import sys
import threading
import time

# 转圈进度条
def spinner_task(stop_event, progress):
    spinner = itertools.cycle(['|', '/', '-', '\\'])
    while not stop_event.is_set():
        pct = progress[0]
        sys.stdout.write(f"\r处理中... {next(spinner)} {pct:.1f}%")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r✅ 处理完成！          \n")

# 读取已学单词
def load_known_words(csv_path):
    known_words = set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row["term"].strip()
            if word:
                known_words.add(word.lower())
    return known_words

# 加载停用词
def load_stopwords(path="stopwords_es.txt"):
    stopwords = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            word = line.strip().lower()
            if word:
                stopwords.add(word)
    return stopwords

# 正则分句函数
SPANISH_ABBR = ["Sr", "Sra", "Dr", "Dra", "Ud", "Uds", "etc", "pág", "Cap"]

def split_sentences_regex(text):
    # 替换换行为空格
    text = re.sub(r'\n+', ' ', text)

    # 保护缩写
    for abbr in SPANISH_ABBR:
        text = re.sub(rf'\b{abbr}\.', abbr + "<DOT>", text)

    # 按标点分句
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # 恢复缩写
    sentences = [s.replace("<DOT>", ".").strip() for s in sentences if s.strip()]

    # 按破折号拆句
    final_sentences = []
    for s in sentences:
        parts = re.split(r'\s*—+\s*', s)
        final_sentences.extend([p.strip() for p in parts if p.strip()])

    return final_sentences

# 从 EPUB 提取句子
def extract_sentences_from_epub(epub_path):
    book = epub.read_epub(epub_path)
    texts = []
    for item in book.get_items():
        if item.get_type() == 9:
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            texts.append(soup.get_text())
    full_text = "\n".join(texts).strip()

    # 正则分句
    sentences = split_sentences_regex(full_text)
    return sentences

# 主处理函数
def extract_minimal_sentences(epub_path, known_csv_path, stopwords_path, output_csv):
    known_words = load_known_words(known_csv_path)
    stopwords = load_stopwords(stopwords_path)

    stop_event = threading.Event()
    progress = [0.0]
    spinner_thread = threading.Thread(target=spinner_task, args=(stop_event, progress))
    spinner_thread.start()

    try:
        sentences = extract_sentences_from_epub(epub_path)
        total_sentences = len(sentences)

        word_counter = Counter()
        word_sentence_candidates = {}

        # 遍历每句话，统计单词
        for idx, sentence in enumerate(sentences, 1):
            words = re.findall(r'\b\w+\b', sentence, flags=re.UNICODE)
            for w in words:
                lw = w.lower()
                if lw in known_words or lw in stopwords:
                    continue
                word_counter[w] += 1
                if w not in word_sentence_candidates:
                    word_sentence_candidates[w] = sentence
            progress[0] = idx / total_sentences * 100

        # 低频词优先分配句子
        word_sentence = {}
        used_sentences = set()
        for word, freq in sorted(word_counter.items(), key=lambda x: x[1]):
            candidate = word_sentence_candidates.get(word, "")
            if candidate and candidate not in used_sentences:
                word_sentence[word] = candidate
                used_sentences.add(candidate)
            else:
                word_sentence[word] = ""  # 没有新句子 → 留空

        # 输出 CSV
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["sentence", "words"])
            for sentence in used_sentences:
                words_in_sentence = [w for w, s in word_sentence.items() if s == sentence]
                writer.writerow([sentence, ", ".join(words_in_sentence)])

        # 统计压缩比率
        all_words = re.findall(r'\b\w+\b', " ".join(sentences), flags=re.UNICODE)
        original_total_words = len(all_words)

        selected_words = re.findall(r'\b\w+\b', " ".join(used_sentences), flags=re.UNICODE)
        selected_total_words = len(selected_words)

        compression_ratio = selected_total_words / original_total_words * 100 if original_total_words > 0 else 0
        unique_sentences = len(used_sentences)

        print("\n📊 统计结果：")
        print(f"原书总词数: {original_total_words}")
        print(f"抽取句子总词数: {selected_total_words}")
        print(f"压缩比率: {compression_ratio:.2f}%")
        print(f"最终保留句子数: {unique_sentences}")

    finally:
        stop_event.set()
        spinner_thread.join()


if __name__ == "__main__":
    extract_minimal_sentences(
        "harry1.epub",
        "lingqs.csv",
        "stopwords_es.txt",
        "harry1.csv"
    )