# 🦥 LazyDesk AI

An open-source AI-powered digital declutterer that organizes files with human approval.

A local open-weight **Gemma** model (via Ollama) suggests clean names and folders for your messy files. You review and approve everything, and your originals are never touched.

## Why open-source AI?
- **No API keys, no cloud, ₹0 to run.** The model runs through Ollama.
- **Your files stay on the machine running the app.** Nothing is sent to a third-party AI service.
- **Swap models freely.** Type any Ollama model name in the sidebar.

## Features
- 🧠 Local AI suggests a cleaner filename and folder for each file
- 🔎 Exact duplicate detection (SHA-256)
- ✅ Approval table: edit names, change folders, untick what you don't want
- 📦 Download only the approved files as a tidy ZIP
- ⏱️ "Effort saved" stat after each run

## Run it
```
pip install -r requirements.txt
ollama pull gemma3:1b
ollama serve   # skip if the Ollama app is already running
python -m streamlit run app.py
```

## How it works
1. Upload files
2. Click **Suggest names + folders**
3. Review the table, edit or untick anything
4. Download the ZIP

## Notes
- The small 1B model is cautious, and sometimes makes odd folder choices. That's exactly why nothing is applied without your approval.
- For text files it also reads the first 500 characters. For other types it uses the filename only.

Built for the Hacktoberfest Open-Source AI Challenge (Slow and Steady). MIT licensed.
