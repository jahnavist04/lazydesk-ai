import io
import json
import re
import time
import zipfile
import hashlib
from pathlib import Path
from collections import defaultdict

import pandas as pd
import streamlit as st

try:
    import ollama
except ImportError:
    ollama = None

# ---------------- PAGE CONFIG ----------------

st.set_page_config(page_title="LazyDesk AI", page_icon="🦥", layout="wide")

# ---------------- DESIGN ----------------

st.markdown("""
<style>
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    background-color: #faf8f5; color: #292323;
}
h1, h2, h3, h4 { color: #641e2b !important; }
p, label, li, [data-testid="stMarkdownContainer"] p { color: #292323; }
[data-testid="stMetric"] {
    background: #ffffff; padding: 16px;
    border: 1px solid #eadfe0; border-radius: 12px;
}
[data-testid="stMetricLabel"] { color: #6b5558; }
[data-testid="stMetricValue"] { color: #641e2b; }
.stButton > button, .stDownloadButton > button {
    background-color: #641e2b; color: white;
    border: 1px solid #641e2b; border-radius: 8px;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    background-color: #7d293a; color: white; border-color: #7d293a;
}
[data-testid="stFileUploader"] {
    background: #ffffff; border: 1px dashed #b78b92;
    border-radius: 12px; padding: 12px;
}
[data-testid="stSidebar"] { background-color: #f0e7e5; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #641e2b !important; }
</style>
""", unsafe_allow_html=True)

# ---------------- HELPERS ----------------

CATEGORIES = {
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".ppt",
                  ".pptx", ".xls", ".xlsx", ".csv", ".md"],
    "Images": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp",
               ".tiff", ".ico"],
    "Videos": [".mp4", ".mov", ".avi", ".mkv", ".webm"],
    "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"],
    "Code": [".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp",
             ".html", ".css", ".json", ".sql", ".sh", ".ipynb"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "Installers": [".exe", ".msi", ".apk", ".dmg", ".deb"],
}
TEXT_EXTS = {".txt", ".md", ".csv", ".py", ".js", ".json", ".html", ".css", ".sql"}


def get_category(filename):
    ext = Path(filename).suffix.lower()
    for category, exts in CATEGORIES.items():
        if ext in exts:
            return category
    return "Others"


def get_hash(file_bytes):
    return hashlib.sha256(file_bytes).hexdigest()


def format_size(size):
    if size < 1024:
        return f"{size} B"
    if size < 1024 ** 2:
        return f"{size / 1024:.1f} KB"
    if size < 1024 ** 3:
        return f"{size / (1024 ** 2):.2f} MB"
    return f"{size / (1024 ** 3):.2f} GB"


def safe_part(text, fallback):
    """Strip anything that could break a path or escape the folder."""
    text = re.sub(r'[<>:"|?*\\]', "", str(text)).replace("..", "").strip(" ./")
    return text or fallback


def safe_folder(folder, fallback):
    parts = [safe_part(p, "") for p in str(folder).split("/")]
    parts = [p for p in parts if p][:2]
    return "/".join(parts) if parts else fallback


def peek_text(file):
    if Path(file.name).suffix.lower() in TEXT_EXTS:
        try:
            return file.getvalue()[:500].decode("utf-8", errors="ignore")
        except Exception:
            return ""
    return ""


def ollama_ready():
    if ollama is None:
        return False
    try:
        ollama.list()
        return True
    except Exception:
        return False


def ai_suggest(file, category, model):
    """Ask the local model for a clean name + folder. Falls back safely."""
    ext = Path(file.name).suffix
    stem = Path(file.name).stem
    fallback = {"name": file.name, "folder": category, "ai": False}
    snippet = peek_text(file)

    prompt = f"""You organize messy files. Reply with JSON only.
Original filename: {file.name}
Detected category: {category}
Content preview: {snippet if snippet else "(not available)"}

Return: {{"name": "<clean, descriptive filename WITHOUT extension, use_underscores>",
"folder": "<{category} or {category}/Subfolder>"}}
Rules: keep the real meaning of the file, never invent facts, max 2 folder levels."""

    try:
        resp = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
        data = json.loads(resp["message"]["content"])
        name = safe_part(data.get("name", stem), stem)
        folder = safe_folder(data.get("folder", category), category)
        return {"name": f"{name}{ext}", "folder": folder, "ai": True}
    except Exception:
        return fallback


def build_zip(rows, files):
    buffer = io.BytesIO()
    used = set()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, row in rows.iterrows():
            if not row["Approve"]:
                continue
            name = safe_part(row["New name"], files[i].name)
            folder = safe_folder(row["Folder"], "Others")
            path = f"{folder}/{name}"
            n = 1
            while path in used:  # avoid overwriting same-named files
                path = f"{folder}/{Path(name).stem}_{n}{Path(name).suffix}"
                n += 1
            used.add(path)
            zf.writestr(path, files[i].getvalue())
    buffer.seek(0)
    return buffer


# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.title("🦥 LazyDesk AI")
    st.caption("Your digital decluttering assistant")
    st.divider()

    model_name = st.text_input("Local model", value="gemma3:4b",
                               help="Try gemma3:1b if your laptop is slow.")
    if ollama_ready():
        st.success(f"Model: {model_name} (local, offline)")
    else:
        st.warning("Ollama not detected. Using extension-only sorting.\n\n"
                   "Run: `ollama serve` then `ollama pull gemma3:4b`")

    st.divider()
    st.markdown("### How it works")
    st.write("1. Upload your files")
    st.write("2. Local AI suggests names + folders")
    st.write("3. You approve what you like")
    st.write("4. Download a tidy ZIP")
    st.divider()
    st.caption("🔒 Files never leave your laptop. Originals are never touched.")
    st.caption("Version 0.2.0")

# ---------------- HEADER ----------------

st.title("Your files. Less chaos.")
st.write("Drop your files below. A local open-source model suggests clean names "
         "and folders. Nothing moves until you approve it.")

uploaded_files = st.file_uploader(
    "Upload files to organize",
    accept_multiple_files=True,
    help="Documents, images, videos, audio, code, or archives.",
)

# ---------------- ANALYSIS ----------------

if uploaded_files:

    records = []
    hash_groups = defaultdict(list)

    for file in uploaded_files:
        data = file.getvalue()
        fp = get_hash(data)
        cat = get_category(file.name)
        records.append({
            "Filename": file.name,
            "Category": cat,
            "Size": format_size(len(data)),
            "Size (bytes)": len(data),
            "SHA-256": fp,
            "Duplicate": False,
        })
        hash_groups[fp].append(file.name)

    for r in records:
        if len(hash_groups[r["SHA-256"]]) > 1:
            r["Duplicate"] = True

    df = pd.DataFrame(records)
    duplicate_groups = {k: v for k, v in hash_groups.items() if len(v) > 1}
    duplicate_file_count = sum(len(v) for v in duplicate_groups.values())
    total_size = sum(r["Size (bytes)"] for r in records)

    # ---------------- METRICS ----------------

    st.divider()
    st.subheader("Your file overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Files analyzed", len(records))
    c2.metric("Categories", df["Category"].nunique())
    c3.metric("Duplicate groups", len(duplicate_groups))
    c4.metric("Total size", format_size(total_size))

    # ---------------- CATEGORY SUMMARY ----------------

    st.divider()
    st.subheader("📂 Category breakdown")

    summary = (
        df.groupby("Category")
        .agg(Files=("Filename", "count"), Total_Bytes=("Size (bytes)", "sum"))
        .reset_index()
        .sort_values("Files", ascending=False)
    )
    summary["Total Size"] = summary["Total_Bytes"].apply(format_size)

    left, right = st.columns([1, 1])
    with left:
        st.dataframe(summary[["Category", "Files", "Total Size"]],
                     hide_index=True)
    with right:
        st.bar_chart(summary[["Category", "Files"]].set_index("Category"))

    # ---------------- DUPLICATES ----------------

    st.divider()
    st.subheader("🔍 Duplicate detective")

    if duplicate_groups:
        st.warning(f"Found {len(duplicate_groups)} groups of exact duplicates "
                   f"({duplicate_file_count} files).")
        for i, (fp, names) in enumerate(duplicate_groups.items(), start=1):
            with st.expander(f"Duplicate group {i} · {len(names)} files"):
                for n in names:
                    st.write(f"📄 {n}")
                st.code(fp, language=None)
    else:
        st.success("No exact duplicates found.")

    # ---------------- AI PLAN ----------------

    st.divider()
    st.subheader("🧠 Let the sloth do it")

    signature = tuple((f.name, f.size) for f in uploaded_files)
    if st.session_state.get("signature") != signature:
        st.session_state["signature"] = signature
        st.session_state.pop("plan", None)
        st.session_state.pop("stats", None)

    if st.button("✨ Suggest names + folders"):
        start = time.time()
        rows = []
        progress = st.progress(0.0, text="Sloth is thinking... slowly...")
        use_ai = ollama_ready()

        for i, file in enumerate(uploaded_files):
            cat = get_category(file.name)
            if use_ai:
                s = ai_suggest(file, cat, model_name)
            else:
                s = {"name": file.name, "folder": cat, "ai": False}
            rows.append({
                "Approve": True,
                "Filename": file.name,
                "New name": s["name"],
                "Folder": s["folder"],
                "AI": "🧠" if s["ai"] else "📁",
            })
            progress.progress((i + 1) / len(uploaded_files))

        progress.empty()
        st.session_state["plan"] = pd.DataFrame(rows)
        st.session_state["stats"] = {
            "seconds": time.time() - start,
            "count": len(rows),
        }

    if "plan" in st.session_state:
        st.write("Review the plan. Edit any name or folder, untick what you "
                 "don't want. 🧠 = AI suggestion, 📁 = extension fallback.")

        edited = st.data_editor(
            st.session_state["plan"],
            hide_index=True,
            disabled=["Filename", "AI"],
            column_config={
                "Approve": st.column_config.CheckboxColumn("Approve"),
            },
            key="plan_editor",
        )

        approved = int(edited["Approve"].sum())
        stats = st.session_state["stats"]
        saved_min = max(1, round(stats["count"] * 30 / 60))

        m1, m2, m3 = st.columns(3)
        m1.metric("Files sorted", stats["count"])
        m2.metric("Time taken", f"{stats['seconds']:.0f} sec")
        m3.metric("Effort saved", f"~{saved_min} min")

        st.download_button(
            label=f"📦 Download {approved} approved files as tidy ZIP",
            data=build_zip(edited, uploaded_files),
            file_name="lazydesk_organized.zip",
            mime="application/zip",
            disabled=approved == 0,
        )
        st.caption("Your original files are never modified. The ZIP contains "
                   "renamed copies in your approved folders.")

    # ---------------- EXPORT ----------------

    st.divider()
    st.download_button(
        "Download analysis report (CSV)",
        data=df.drop(columns=["SHA-256"]).to_csv(index=False),
        file_name="lazydesk_report.csv",
        mime="text/csv",
    )

else:
    st.divider()
    st.markdown("### Ready when you are.")
    a, b, c = st.columns(3)
    with a:
        st.markdown("#### 🧠 Local AI naming")
        st.write("Gemma runs on your laptop. No cloud, no API keys.")
    with b:
        st.markdown("#### 🔎 Duplicate detection")
        st.write("Finds files with identical contents.")
    with c:
        st.markdown("#### ✅ You approve everything")
        st.write("Edit, untick, then download a tidy ZIP.")
    st.caption("Tip: upload a few messy files plus two identical copies "
               "to see duplicate detection.")
