import importlib
import subprocess
import sys
from typing import List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components


# 页面基础配置要尽量在最前面执行，这样 Streamlit 才能正确应用标题、布局等设置。
st.set_page_config(
    page_title="句法双引擎透视仪",
    page_icon="🧠",
    layout="wide",
)


# 这个默认句子正是课件里经典的介词短语附着歧义例子。
DEFAULT_SENTENCE = "The boy saw the man with the telescope."


def install_python_package(package_name: str) -> None:
    """安装 Python 包。

    这里使用当前解释器对应的 pip，避免出现“装到了别的 Python 环境里”的问题。
    """
    subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])


def import_or_install(module_name: str, package_name: Optional[str] = None):
    """导入模块；若模块不存在，则自动尝试安装对应包后再次导入。"""
    install_target = package_name or module_name
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        with st.spinner(f"检测到缺少 `{install_target}`，正在自动安装..."):
            install_python_package(install_target)
        return importlib.import_module(module_name)


@st.cache_resource(show_spinner=False)
def load_spacy_pipeline():
    """加载 spaCy 英文模型。

    如果 `en_core_web_sm` 没有下载，这里会自动拉取。
    """
    # 这里固定到一个对 Python 3.9 更友好的版本，避免课堂环境里误触源码编译。
    spacy = import_or_install("spacy", "spacy==3.7.5")
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        with st.spinner("正在下载 spaCy 英文模型 `en_core_web_sm`，首次启动会稍慢一些..."):
            subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        return spacy.load("en_core_web_sm")


@st.cache_resource(show_spinner=False)
def load_constituency_stack() -> Tuple[Optional[object], Optional[object], Optional[object], Optional[str]]:
    """加载成分句法所需组件。

    返回值依次为：
    1. benepar 模块
    2. nltk 模块
    3. benepar 解析器实例
    4. 错误信息（若成功则为 None）

    之所以把错误信息作为返回值，而不是直接抛异常，是为了让页面在安装失败时仍能正常显示依存分析部分。
    """
    try:
        benepar = import_or_install("benepar")
        nltk = import_or_install("nltk")
        import_or_install("svgling")
    except Exception as exc:  # noqa: BLE001
        return None, None, None, f"安装成分分析依赖失败：{exc}"

    try:
        parser = benepar.Parser("benepar_en3")
    except LookupError:
        with st.spinner("正在下载 Berkeley Neural Parser 模型 `benepar_en3`..."):
            benepar.download("benepar_en3")
        parser = benepar.Parser("benepar_en3")
    except Exception as exc:  # noqa: BLE001
        return None, None, None, f"加载 benepar 模型失败：{exc}"

    return benepar, nltk, parser, None


def render_dependency_view(doc) -> None:
    """渲染依存句法图。"""
    spacy = importlib.import_module("spacy")
    displacy = spacy.displacy

    # 这些样式参数会影响弧线疏密、标签间距和整体可读性。
    svg = displacy.render(
        doc,
        style="dep",
        options={
            "compact": False,
            "distance": 110,
            "bg": "#ffffff",
            "color": "#1f2937",
            "font": "Arial",
        },
    )

    html = f"""
    <div style="overflow-x:auto; background:#ffffff; border:1px solid #e5e7eb;
                border-radius:12px; padding:16px;">
        {svg}
    </div>
    """
    components.html(html, height=420, scrolling=True)


def render_constituency_view(sentence: str) -> None:
    """渲染成分句法树。

    优先使用 benepar 生成成分树，再用 svgling 输出 SVG。
    如果这一链路失败，则在页面里给出清晰提示。
    """
    _, nltk, parser, error_message = load_constituency_stack()
    if error_message:
        st.error(error_message)
        st.info("可以先使用依存关系页签完成实验；若需要成分树，请稍后重试或手动执行 `pip install benepar svgling nltk`。")
        return

    try:
        tokenizer = nltk.tokenize.TreebankWordTokenizer()
        tokens = tokenizer.tokenize(sentence)
        tree = parser.parse(tokens)
    except Exception as exc:  # noqa: BLE001
        st.error(f"生成成分句法树失败：{exc}")
        return

    try:
        svgling = importlib.import_module("svgling")
        svg = svgling.draw_tree(tree)._repr_svg_()
        html = f"""
        <div style="overflow:auto; background:#ffffff; border:1px solid #e5e7eb;
                    border-radius:12px; padding:16px;">
            {svg}
        </div>
        """
        components.html(html, height=520, scrolling=True)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"图形化渲染失败，已退回括号表示法：{exc}")

    # 即使图形化成功，也额外展示括号结构，方便课堂报告里引用。
    st.code(tree.pformat(margin=100), language="text")


def escape_markdown_cell(value: object) -> str:
    """转义 Markdown 表格中的竖线，避免列错位。"""
    return str(value).replace("|", "\\|")


def render_markdown_table(rows: List[dict], columns: List[str]) -> None:
    """把字典列表渲染成 Markdown 表格。

    这样做可以避免课堂环境里因为 DataFrame 依赖导致页面额外出错。
    """
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = [
        "| " + " | ".join(escape_markdown_cell(row.get(column, "")) for column in columns) + " |"
        for row in rows
    ]
    st.markdown("\n".join([header, separator, *body]))


def extract_core_arguments(doc) -> List[dict]:
    """抽取课堂要求的核心论元与根节点。"""
    relation_notes = {
        "ROOT": "句子的核心谓词或中心词",
        "nsubj": "名词性主语",
        "dobj": "直接宾语",
        "obj": "宾语（spaCy 某些版本会用 obj 代替 dobj）",
        "pobj": "介词宾语",
    }

    rows = []
    for token in doc:
        if token.dep_ not in {"ROOT", "nsubj", "dobj", "obj", "pobj"}:
            continue

        normalized_relation = "dobj" if token.dep_ == "obj" else token.dep_
        rows.append(
            {
                "依存关系": normalized_relation,
                "词": token.text,
                "词性": token.pos_,
                "中心词": "-" if token.dep_ == "ROOT" else token.head.text,
                "说明": relation_notes[token.dep_],
            }
        )

    return rows


def build_token_table(doc) -> List[dict]:
    """额外生成一个逐词分析表，方便做“歧义侦探”观察。"""
    return [
        {
            "词": token.text,
            "词性": token.pos_,
            "词形还原": token.lemma_,
            "依存关系": token.dep_,
            "中心词": token.head.text if token.dep_ != "ROOT" else "-",
        }
        for token in doc
    ]


st.title("句法双引擎透视仪与“歧义侦探”")
st.caption("同一句话，切换成分句法与依存句法两种视角，观察模型如何做出结构决策。")

# 顶部输入框：默认文本直接使用作业要求中的经典歧义句。
sentence = st.text_input("请输入英文句子", value=DEFAULT_SENTENCE)

try:
    nlp = load_spacy_pipeline()
    doc = nlp(sentence)
except Exception as exc:  # noqa: BLE001
    st.error(f"spaCy 初始化失败：{exc}")
    st.stop()


with st.expander("当前模型状态", expanded=False):
    st.write(
        {
            "spaCy 模型": "en_core_web_sm",
            "成分分析模型": "benepar_en3（若安装成功）",
            "当前输入长度": len(doc),
        }
    )


dep_tab, con_tab = st.tabs(["依存关系", "成分结构"])

with dep_tab:
    st.subheader("依存句法图")
    st.write("观察词与词之间的支配关系，特别注意主语、宾语以及介词短语附着到哪个中心词上。")
    render_dependency_view(doc)

with con_tab:
    st.subheader("成分句法树")
    st.write("观察短语如何层层嵌套，特别留意 `with the telescope` 最终并入了哪一层短语。")
    render_constituency_view(sentence)


st.markdown("---")
st.subheader("核心论元提取器")
st.write("根据依存分析结果，抽取主语 `nsubj`、直接宾语 `dobj`、介词宾语 `pobj` 与根节点 `ROOT`。")

argument_df = extract_core_arguments(doc)
if not argument_df:
    st.warning("当前句子中没有抽取到目标依存关系。你可以换一句更完整的句子再试试。")
else:
    render_markdown_table(argument_df, ["依存关系", "词", "词性", "中心词", "说明"])


st.subheader("逐词分析表")
st.write("这个表对完成“Fruit flies like a banana.” 的歧义观察尤其有帮助。")
render_markdown_table(build_token_table(doc), ["词", "词性", "词形还原", "依存关系", "中心词"])


st.info(
    "课堂实验建议：先输入默认句子观察介词短语附着，再输入 “Fruit flies like a banana.” 查看 `flies` 被标成名词还是动词。"
)
