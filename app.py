
import streamlit as st
import pandas as pd
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="LazyDesk AI",
    page_icon="🦥",
    layout="wide"
)


# ---------------- DESIGN ----------------

st.markdown("""
<style>
.stApp {
    background-color: #faf8f5;
    color: #292323;
}

[data-testid="stAppViewContainer"] {
    background-color: #faf8f5;
}

[data-testid="stHeader"] {
    background-color: #faf8f5;
}

h1, h2, h3, h4 {
    color: #641e2b !important;
}

p, label, li,
[data-testid="stMarkdownContainer"] p {
    color: #292323;
}

[data-testid="stMetric"] {
    background: #ffffff;
    padding: 16px;
    border: 1px solid #eadfe0;
    border-radius: 12px;
}

[data-testid="stMetricLabel"] {
    color: #6b5558;
}

[data-testid="stMetricValue"] {
    color: #641e2b;
}

.stButton > button,
.stDownloadButton > button {
    background-color: #641e2b;
    color: white;
    border: 1px solid #641e2b;
    border-radius: 8px;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    background-color: #7d293a;
    color: white;
    border-color: #7d293a;
}

[data-testid="stFileUploader"] {
    background: #ffffff;
    border: 1px dashed #b78b92;
    border-radius: 12px;
    padding: 12px;
}

[data-testid="stSidebar"] {
    background-color: #f0e7e5;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #641e2b !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HELPERS ----------------

def get_category(filename):
    """Suggest a category based on the file extension."""

    extension = Path(filename).suffix.lower()

    categories = {
        "Documents": [
            ".pdf", ".doc", ".docx", ".txt", ".rtf",
            ".odt", ".ppt", ".pptx", ".xls", ".xlsx",
            ".csv", ".md"
        ],
        "Images": [
            ".png", ".jpg", ".jpeg", ".gif", ".webp",
            ".svg", ".bmp", ".tiff", ".ico"
        ],
        "Videos": [
            ".mp4", ".mov", ".avi", ".mkv", ".webm"
        ],
        "Audio": [
            ".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"
        ],
        "Code": [
            ".py", ".js", ".jsx", ".ts", ".tsx", ".java",
            ".c", ".cpp", ".html", ".css", ".json",
            ".sql", ".sh", ".ipynb"
        ],
        "Archives": [
            ".zip", ".rar", ".7z", ".tar", ".gz"
        ],
        "Installers": [
            ".exe", ".msi", ".apk", ".dmg", ".deb"
        ]
    }

    for category, extensions in categories.items():
        if extension in extensions:
            return category

    return "Others"


def get_hash(file_bytes):
    """Calculate a SHA-256 fingerprint for exact duplicate detection."""
    return hashlib.sha256(file_bytes).hexdigest()


def format_size(size):
    """Convert bytes into a readable size."""
    if size < 1024:
        return f"{size} B"
    if size < 1024 ** 2:
        return f"{size / 1024:.1f} KB"
    if size < 1024 ** 3:
        return f"{size / (1024 ** 2):.2f} MB"
    return f"{size / (1024 ** 3):.2f} GB"


# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.title("🦥 LazyDesk AI")
    st.caption("Your digital decluttering assistant")

    st.divider()

    st.markdown("### How it works")
    st.write("1. Upload your files")
    st.write("2. Analyze file types")
    st.write("3. Detect exact duplicates")
    st.write("4. Review the organization plan")
    st.write("5. Export your results")

    st.divider()

    st.caption("Current version: 0.1.0")
    st.caption("AI integration: Coming next")


# ---------------- HEADER ----------------

st.title("Your files. Less chaos.")
st.write(
    "Drop your files below. LazyDesk will suggest categories, "
    "identify exact duplicates, and prepare an organization plan."
)

st.info(
    "🔒 This version analyzes uploaded files in memory. "
    "It does not modify folders on your computer or delete files."
)

# ---------------- FILE UPLOAD ----------------

uploaded_files = st.file_uploader(
    "Upload files to organize",
    accept_multiple_files=True,
    help="Upload documents, images, videos, audio, code, or archives."
)

# ---------------- ANALYSIS ----------------

if uploaded_files:

    records = []
    hash_groups = defaultdict(list)

    with st.spinner("Analyzing your files..."):

        for file in uploaded_files:
            file_bytes = file.getvalue()
            fingerprint = get_hash(file_bytes)
            category = get_category(file.name)

            record = {
                "Filename": file.name,
                "Category": category,
                "Size": format_size(len(file_bytes)),
                "Size (bytes)": len(file_bytes),
                "SHA-256": fingerprint,
                "Duplicate": False,
                "Suggested Path": f"{category}/{file.name}"
            }

            records.append(record)
            hash_groups[fingerprint].append(file.name)

    # Mark every member of a duplicate group.
    for record in records:
        if len(hash_groups[record["SHA-256"]]) > 1:
            record["Duplicate"] = True

    df = pd.DataFrame(records)

    duplicate_groups = {
        fingerprint: names
        for fingerprint, names in hash_groups.items()
        if len(names) > 1
    }

    duplicate_file_count = sum(
        len(names) for names in duplicate_groups.values()
    )

    unique_duplicate_groups = len(duplicate_groups)
    total_size = sum(record["Size (bytes)"] for record in records)

    # ---------------- METRICS ----------------

    st.divider()
    st.subheader("Your file overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Files analyzed", len(records))
    col2.metric("Categories", df["Category"].nunique())
    col3.metric("Duplicate groups", unique_duplicate_groups)
    col4.metric("Total size", format_size(total_size))

   
# ---------------- CATEGORY SUMMARY ----------------

st.divider()
st.subheader("📂 Category breakdown")

category_summary = (
    df.groupby("Category")
    .agg(
        Files=("Filename", "count"),
        Total_Bytes=("Size (bytes)", "sum")
    )
    .reset_index()
    .sort_values("Files", ascending=False)
)

category_summary["Total Size"] = category_summary[
    "Total_Bytes"
].apply(format_size)

# Simple, readable summary without awkward chart axes
for _, row in category_summary.iterrows():
    col1, col2, col3 = st.columns([3, 1, 2])

    with col1:
        st.write(f"📁 **{row['Category']}**")

    with col2:
        st.write(f"**{row['Files']} files**")

    with col3:
        st.write(row["Total Size"])

st.caption(
    "Counts show how many uploaded files fall into each category."
)

# Clean category chart
chart_data = category_summary[["Category", "Files"]].set_index("Category")

st.bar_chart(chart_data)


    st.dataframe(
        category_summary[["Category", "Files", "Total Size"]],
        use_container_width=True,
        hide_index=True
    )

    # ---------------- FILE TABLE ----------------

    st.divider()
    st.subheader("🗂️ File organizer")

    selected_category = st.selectbox(
        "Filter by category",
        ["All categories"] + sorted(df["Category"].unique().tolist())
    )

    filtered_df = df.copy()

    if selected_category != "All categories":
        filtered_df = filtered_df[
            filtered_df["Category"] == selected_category
        ]

    st.dataframe(
        filtered_df[
            ["Filename", "Category", "Size", "Duplicate", "Suggested Path"]
        ],
        use_container_width=True,
        hide_index=True
    )

    # ---------------- DUPLICATE DETECTOR ----------------

    st.divider()
    st.subheader("🔍 Duplicate detective")

    if duplicate_groups:
        st.warning(
            f"Found {unique_duplicate_groups} groups of exact duplicates, "
            f"containing {duplicate_file_count} files."
        )

        st.caption(
            "Files are grouped by their SHA-256 fingerprints. "
            "Matching fingerprints indicate matching file contents "
            "for practical duplicate detection."
        )

        for index, (fingerprint, names) in enumerate(
            duplicate_groups.items(), start=1
        ):
            with st.expander(f"Duplicate group {index} · {len(names)} files"):
                for name in names:
                    st.write(f"📄 {name}")

                st.code(fingerprint, language=None)

        st.info(
            "No files have been deleted. Review duplicate groups "
            "before deciding what to keep."
        )

    else:
        st.success("No exact duplicate files found in this upload.")

    # ---------------- ORGANIZATION PLAN ----------------

    st.divider()
    st.subheader("✨ Your organization plan")

    st.write(
        "Here is the proposed folder destination for each uploaded file."
    )

    st.dataframe(
        df[["Filename", "Category", "Suggested Path"]],
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "These are suggested paths only. This version does not move "
        "or rename files on your computer."
    )

    # ---------------- EXPORT ----------------

    st.divider()
    st.subheader("📥 Take your results with you")

    csv_data = df.drop(columns=["SHA-256"]).to_csv(index=False)

    st.download_button(
        label="Download organization report (CSV)",
        data=csv_data,
        file_name="lazydesk_organization_report.csv",
        mime="text/csv"
    )

    st.success("Analysis complete! Your files remain unchanged.")

else:
    # ---------------- EMPTY STATE ----------------

    st.divider()

    st.markdown("### Ready when you are.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 📁 Smart categories")
        st.write("Get suggested folders based on file types.")

    with col2:
        st.markdown("#### 🔎 Duplicate detection")
        st.write("Find files with identical contents.")

    with col3:
        st.markdown("#### 📋 Easy export")
        st.write("Download your organization plan as a CSV.")

    st.caption(
        "Tip: Try uploading a few sample files, including two copies "
        "of the same file, to test duplicate detection."
    )
