import spacy
from ebooklib import epub
from bs4 import BeautifulSoup
from collections import Counter
import csv
import sys
import time
import threading
import itertools
import re

# 加载西语 NLP 模型
nlp = spacy.load("es_core_news_sm")

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

# 提取句子（每行拆分 + spaCy 分句 + 批量处理）
def extract_sentences_from_epub(epub_path):
    book = epub.read_epub(epub_path)
    texts = []
    for item in book.get_items():
        if item.get_type() == 9:  # 文本类型 (XHTML)
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            texts.append(soup.get_text())

    full_text = "\n".join(texts).strip()

    # 按换行拆分为潜在句子
    lines = [line.strip() for line in full_text.splitlines() if line.strip()]
    potential_sentences = []

    # 批量处理 spaCy 分句
    for doc in nlp.pipe(lines, batch_size=50):
        for sent in doc.sents:
            s = sent.text.strip()
            if s:
                potential_sentences.append(s)

    return potential_sentences

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

        # 使用 nlp.pipe 批量处理单词统计
        docs = list(nlp.pipe(sentences, batch_size=50))
        for idx, doc in enumerate(docs, 1):
            words = [token.text for token in doc if token.is_alpha]
            for w in words:
                lw = w.lower()
                if lw in known_words or lw in stopwords:
                    continue
                word_counter[w] += 1
                if w not in word_sentence_candidates:
                    word_sentence_candidates[w] = doc.text

            progress[0] = idx / total_sentences * 100

        # 分配句子：低频优先
        word_sentence = {}
        used_sentences = set()

        for word, freq in sorted(word_counter.items(), key=lambda x: x[1]):  # 从低频到高频
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

        # ----------------- 统计信息 -----------------
        # 原书总词数
        original_words = []
        for doc in docs:
            original_words.extend([token.text for token in doc if token.is_alpha])
        original_total_words = len(original_words)

        # 抽取句子总词数
        selected_words = []
        for sentence in used_sentences:
            doc = nlp(sentence)
            selected_words.extend([token.text for token in doc if token.is_alpha])
        selected_total_words = len(selected_words)

        # 压缩比率
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
        "your_book.epub",     # 输入 EPUB
        "lingqs.csv",         # 已学单词列表
        "stopwords_es.txt",   # 停用词列表
        "minimal_sentences.csv"  # 输出 CSV
    )