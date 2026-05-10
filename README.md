# Syntax Lens Ambiguity Detective

Week 3 NLP vibe coding assignment: a Streamlit web app that compares dependency parsing and constituency parsing for English sentences, then extracts core dependency arguments for quick inspection.

## Features

- Dependency parsing with spaCy and displaCy SVG rendering.
- Constituency parsing with benepar and svgling when available.
- Streamlit tabs for dependency and constituency views.
- Core argument extractor for `ROOT`, `nsubj`, `dobj`, `obj`, and `pobj`.
- Chinese comments throughout the source code for classroom review.
- Automatic installation or download logic for spaCy and benepar models on first run.

## Default Experiment Sentences

- `The boy saw the man with the telescope.`
- `Fruit flies like a banana.`

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The first launch may take longer because the app downloads `en_core_web_sm` and `benepar_en3` if they are missing.

## Project Files

- `app.py`: Streamlit application source code.
- `requirements.txt`: Python dependencies.
- `Week3_句法双引擎实验报告.docx`: Assignment report document.

## Notes

If benepar installation fails in a local environment, the dependency parsing tab can still run. You can also adapt the constituency parser to an NLTK CFG fallback for stricter classroom environments.
