# Local Setup and Execution Guide (Windows)

This document provides clear, step-by-step instructions for setting up, configuring, and running the **AI-Powered GitHub Codebase RAG Assistant** on Windows.

---

## 1. Prerequisites

Before starting, ensure you have the following installed on your machine:
1. **Python 3.10, 3.11, or 3.12** (Python 3.11 is recommended).
   - Check version: `python --version` or `py -3.11 --version`
2. **Git for Windows** (Optional but recommended for fast shallow cloning).
   - Check version: `git --version`
   - *Note: If Git is not installed, the application automatically falls back to downloading repository ZIP archives.*

---

## 2. Step-by-Step Installation

### Step 1: Open Terminal in Project Root
Open Windows PowerShell or Command Prompt in the repository folder:
```powershell
cd c:\Users\adity\OneDrive\Desktop\rag
```

### Step 2: Create a Python Virtual Environment
Use Python 3.11 (or your installed Python version):
```powershell
py -3.11 -m venv .venv
```
*(Alternatively: `python -m venv .venv`)*

### Step 3: Activate the Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

> [!TIP]
> **PowerShell Execution Policy Error?**
> If PowerShell shows an error about script execution being disabled, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Then run `.\.venv\Scripts\Activate.ps1` again.

### Step 4: Install Dependencies
Install all required Python packages into the virtual environment:
```powershell
pip install -r requirements.txt
```

---

## 3. Environment Configuration

### Step 1: Copy Environment Template
Copy the `.env.example` file to create your active `.env`:
```powershell
Copy-Item .env.example .env
```

### Step 2: Configure Your LLM API Key
Open `.env` in any text editor (Notepad, VS Code):
```ini
# Choose your preferred provider: 'gemini' or 'openai'
LLM_PROVIDER=gemini

# Add your Google Gemini API Key:
LLM_API_KEY=AIzaSy...your_gemini_api_key_here
```

> [!NOTE]
> - **Free Google Gemini API Key**: You can obtain a free API key at [Google AI Studio](https://aistudio.google.com/).
> - **Offline Demo Mode**: If no API key is configured, the application operates in an educational fallback mode that demonstrates semantic retrieval, displays exact source chunks and similarity scores, and prompts you to add your key for live conversational synthesis.

---

## 4. Running the Application

Start the FastAPI application with Uvicorn:
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Accessing the Web Application
Open your web browser and navigate to:
- **Web User Interface**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 5. Running Automated Tests

Run the complete test suite (15 unit and integration tests) using `pytest`:
```powershell
.\.venv\Scripts\pytest.exe -v tests
```

---

## 6. Troubleshooting Common Windows Issues

### Issue 1: `huggingface_hub symlink warning`
- **Symptom**: A warning message appears saying Windows does not support symlinks.
- **Explanation**: This is normal on standard non-admin Windows accounts. Hugging Face simply copies the model files rather than symlinking them. It does not affect functionality.
- **Resolution**: You can silence this warning by adding `HF_HUB_DISABLE_SYMLINKS_WARNING=1` to `.env`.

### Issue 2: `Git clone failed`
- **Symptom**: Git returns an authentication or connection error.
- **Explanation & Resolution**: The application automatically falls back to fetching the repository archive as a `.zip` from GitHub and unzipping it locally, ensuring that analysis continues seamlessly even if Git is blocked or unavailable.

### Issue 3: `ChromaDB SQLite error`
- **Symptom**: ChromaDB complains about SQLite version.
- **Resolution**: Python 3.11 includes SQLite 3.39+, which fully meets ChromaDB's requirements. Ensure you are using the `.venv` created with Python 3.11.
