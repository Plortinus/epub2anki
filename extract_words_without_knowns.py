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

# 读取已学单词（lingqs.csv 的第一列 term）
def load_known_words(csv_path):
    known_words = set()
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row["term"].strip()
            if word:
                known_words.add(word.lower())
    return known_words

# 从 stopwords_es.txt 文件加载停用词
def load_stopwords(path="stopwords_es.txt"):
    stopwords = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            word = line.strip().lower()
            if word:
                stopwords.add(word)
    return stopwords

def extract_words_with_sentences(epub_path, known_csv_path, stopwords_path, output_csv, fill_in_blank=True):
    known_words = load_known_words(known_csv_path)
    stopwords = load_stopwords(stopwords_path)

    stop_event = threading.Event()
    progress = [0.0]
    spinner_thread = threading.Thread(target=spinner_task, args=(stop_event, progress))
    spinner_thread.start()

    try:
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
        word_sentence = {}       # key: word, value: assigned sentence
        used_sentences = set()   # 已被分配句子

        for idx, sentence in enumerate(sentences, 1):
            clean_sentence = ' '.join(sentence.replace("\n", " ").replace("\r", " ").split())
            clean_sentence = re.sub(r'^[\-\—\–\~\s]+', '', clean_sentence)
            clean_sentence = re.sub(r'[<>]+', '', clean_sentence)
            clean_sentence = re.sub(r'^[“"\'‘]+|[”"\'’]+$', '', clean_sentence)

            # 提取所有单词，不再限制西语
            words = re.findall(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+", clean_sentence)
            for w in words:
                lw = w.lower()
                if lw in known_words or lw in stopwords:
                    continue
                word_counter[w] += 1
                if w not in word_sentence:
                    if clean_sentence not in used_sentences:
                        word_sentence[w] = clean_sentence
                        used_sentences.add(clean_sentence)
                    else:
                        word_sentence[w] = clean_sentence  # 必须共享也分配

            progress[0] = idx / total_sentences * 100

        # 写入 CSV
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["word", "count", "example_sentence"])
            for word, freq in word_counter.most_common():
                example = word_sentence.get(word, "")
                if fill_in_blank:
                    example_anki = re.sub(r'\b{}\b'.format(re.escape(word)), r'{{c1::\g<0>}}', example, count=1)
                else:
                    example_anki = re.sub(r'\b{}\b'.format(re.escape(word)), r'<b>\g<0></b>', example, count=1)
                writer.writerow([word, freq, example_anki])

    finally:
        stop_event.set()
        spinner_thread.join()

if __name__ == "__main__":
    extract_words_with_sentences(
        "atomic.epub",
        "lingqs.csv",
        "stopwords_es.txt",
        "atomic.csv",
        fill_in_blank=False    # True → 填空题, False → 高亮单词
    )