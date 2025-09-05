# EPUB 转 Anki 单词提取工具

这个项目可以从 EPUB 电子书中提取单词，用于制作 Anki 卡片。

## 安装依赖

```bash
pip install -r requirements.txt
```

或者手动安装：
```bash
pip install ebooklib beautifulsoup4
```

## 使用方法

### 1. 提取所有单词
```bash
python extract_words.py
```

### 2. 提取未知单词（排除已学单词）
```bash
python extract_words_without_knowns.py
```

### 3. 提取单词和例句
```bash
python extract_words_with_sentences.py
```

## 依赖包说明

- `ebooklib`: 用于解析 EPUB 格式电子书
- `beautifulsoup4`: 用于解析 HTML 内容