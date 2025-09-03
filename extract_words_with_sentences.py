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

# 读取本地词典 CSV（西语 → 英语）
def load_translation_dict(dict_csv_path):
    translation_dict = {}
    with open(dict_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            spanish_word = row["spanish"].strip()
            english_word = row["english"].strip()
            translation_dict[spanish_word] = english_word
    return translation_dict

def extract_words_with_sentences(epub_path, dict_csv_path, output_csv):
    # 载入词典
    translation_dict = load_translation_dict(dict_csv_path)

    # 启动转圈线程
    stop_event = threading.Event()
    progress = [0.0]
    spinner_thread = threading.Thread(target=spinner_task, args=(stop_event, progress))
    spinner_thread.start()

    try:
        # 读取 epub 文件
        book = epub.read_epub(epub_path)
        texts = []
        for item in book.get_items():
            if item.get_type() == 9:  # 文本类型 (XHTML)
                soup = BeautifulSoup(item.get_body_content(), "html.parser")
                texts.append(soup.get_text())

        full_text = " ".join(texts)

        # 按句子切分
        sentences = re.split(r'(?<=[.!?])\s+', full_text)
        total_sentences = len(sentences)

        word_counter = Counter()
        word_sentence = {}

        # 遍历句子
        for idx, sentence in enumerate(sentences, 1):
            # 清理换行符和多余空格
            clean_sentence = ' '.join(sentence.replace("\n", " ").replace("\r", " ").split())
            # 去掉句子开头的破折号（英文/中文等）
            clean_sentence = re.sub(r'^[\-\—\–\~\s]+', '', clean_sentence)
            # 去掉 << >> 等特殊符号
            clean_sentence = re.sub(r'[<>]+', '', clean_sentence)
            # 去掉句子首尾各种引号（中文/英文单双引号）
            clean_sentence = re.sub(r'^[“"\'‘]+|[”"\'’]+$', '', clean_sentence)

            # 提取单词（只保留字母和西语字符）
            words = re.findall(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+", clean_sentence)
            for w in words:
                word_counter[w] += 1
                if w not in word_sentence:
                    word_sentence[w] = clean_sentence

            # 更新百分比
            progress[0] = idx / total_sentences * 100

        # 写入 CSV（Anki 填空 + 英语翻译）
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["word", "count", "example_sentence", "translation"])
            for word, freq in word_counter.most_common():
                example = word_sentence[word]
                # 生成 Anki 填空格式
                example_anki = re.sub(r'\b{}\b'.format(re.escape(word)), r'{{c1::\g<0>}}', example, count=1)
                # 获取英语翻译
                translation = translation_dict.get(word, "")
                writer.writerow([word, freq, example_anki, translation])

    finally:
        stop_event.set()
        spinner_thread.join()

if __name__ == "__main__":
    extract_words_with_sentences("harry.epub", "data.csv", "word_with_sentences.csv")