from ebooklib import epub
from bs4 import BeautifulSoup
from collections import Counter
import re
import csv
import sys
import time
import threading
import itertools

# 转圈 + 百分比显示
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

def extract_minimal_sentences(epub_path, known_csv_path, stopwords_path, output_csv):
    known_words = load_known_words(known_csv_path)
    stopwords = load_stopwords(stopwords_path)

    stop_event = threading.Event()
    progress = [0.0]
    spinner_thread = threading.Thread(target=spinner_task, args=(stop_event, progress))
    spinner_thread.start()

    try:
        # 读取 epub
        book = epub.read_epub(epub_path)
        texts = []
        for item in book.get_items():
            if item.get_type() == 9:  # 文本类型 (XHTML)
                soup = BeautifulSoup(item.get_body_content(), "html.parser")
                texts.append(soup.get_text())

        full_text = " ".join(texts)
        sentences = re.split(r'(?<=[.!?])\s+', full_text)
        total_sentences = len(sentences)

        word_counter = Counter()
        word_sentence_candidates = {}

        # 统计单词频率 & 收集候选句子
        for idx, sentence in enumerate(sentences, 1):
            clean_sentence = ' '.join(sentence.replace("\n", " ").replace("\r", " ").split())
            clean_sentence = re.sub(r'^[\-\—\–\~\s]+', '', clean_sentence)
            clean_sentence = re.sub(r'[<>]+', '', clean_sentence)
            clean_sentence = re.sub(r'^[“"\'‘]+|[”"\'’]+$', '', clean_sentence)

            words = re.findall(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+", clean_sentence)
            for w in words:
                lw = w.lower()
                if lw in known_words or lw in stopwords:
                    continue
                word_counter[w] += 1
                # 保存第一个候选句子
                if w not in word_sentence_candidates:
                    word_sentence_candidates[w] = clean_sentence

            progress[0] = idx / total_sentences * 100

        # 分配句子：从低频词开始
        word_sentence = {}
        used_sentences = set()

        for word, freq in sorted(word_counter.items(), key=lambda x: x[1]):  # 从低频到高频
            candidate = word_sentence_candidates.get(word, "")
            if candidate and candidate not in used_sentences:
                word_sentence[word] = candidate
                used_sentences.add(candidate)
            else:
                word_sentence[word] = ""  # 没有新句子 → 留空

        # 最终只输出去重后的句子列表
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["sentence", "words"])
            for sentence in used_sentences:
                words_in_sentence = [w for w, s in word_sentence.items() if s == sentence]
                writer.writerow([sentence, ", ".join(words_in_sentence)])

        # ---- 统计信息 ----
        total_words = len(word_counter)
        covered_words = sum(1 for s in word_sentence.values() if s)
        unique_sentences = len(used_sentences)
        avg_words_per_sentence = covered_words / unique_sentences if unique_sentences > 0 else 0

        print("\n📊 统计结果：")
        print(f"总单词数: {total_words}")
        print(f"覆盖单词数: {covered_words}")
        print(f"最终保留句子数: {unique_sentences}")
        print(f"平均每句覆盖单词数: {avg_words_per_sentence:.2f}")

    finally:
        stop_event.set()
        spinner_thread.join()

if __name__ == "__main__":
    extract_minimal_sentences(
        "atomic.epub",
        "lingqs.csv",
        "stopwords_es.txt",
        "atomic.csv"
    )