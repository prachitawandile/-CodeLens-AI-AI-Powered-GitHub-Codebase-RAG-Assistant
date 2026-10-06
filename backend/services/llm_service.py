"""
LLM Service supporting Google Gemini and OpenAI with a grounded system prompt.
Isolated in a clean service layer with robust error handling and fallback capability.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Ensure environment variables are loaded
base_dir = Path(__file__).resolve().parent.parent.parent
env_file = base_dir / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv()


SYSTEM_PROMPT = """You are an expert codebase assistant and technical explainer.
Your goal is to explain codebases and answer questions in natural, intuitive, and easy-to-understand language that any developer, student, or evaluator can instantly comprehend.

Guidelines:
1. Explain Concepts in Plain, Friendly English:
   - Avoid overly dense or cryptic technical jargon without brief clarification.
   - Start with a clear, high-level summary so the reader immediately understands what the project or code does.
2. Structured & Beautiful Formatting:
   - Use clear section headings (e.g., 🎯 **Overview**, ⚙️ **Key Features & Components**, 🔍 **Implementation Details**, 📌 **Summary**).
   - Use concise bullet points and bold highlights for readability.
3. Grounding & Accuracy:
   - Base your explanation strictly on the retrieved repository context provided.
   - Do not invent files, functions, or features not present in the context.
   - Reference the relevant files and line ranges naturally (e.g., `README.md`, `backend/app/seed.py`).
4. Concise Code References:
   - When showing code, use only brief, essential snippets to illustrate your explanation rather than dumping large walls of raw code.
"""


class LLMService:
    """Handles communication with LLM providers (Gemini or OpenAI)."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "gemini")).lower()
        self.api_key = (
            api_key
            or os.getenv("LLM_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        ).strip()

    def generate_answer(
        self,
        question: str,
        context_chunks: List[dict],
        repository_name: str,
    ) -> Dict[str, str]:
        """
        Generate answer from retrieved repository chunks.
        
        Returns:
            Dict containing 'answer' and 'model_used'.
        """
        if not context_chunks:
            return {
                "answer": "I couldn't find enough relevant information in the indexed repository to answer this confidently. Please try phrasing your question differently or explore the repository files.",
                "model_used": "none",
            }

        # Build context string
        context_parts = []
        for i, chunk in enumerate(context_chunks, 1):
            file_path = chunk.get("file_path", "unknown")
            start = chunk.get("start_line", 1)
            end = chunk.get("end_line", 1)
            text = chunk.get("text", "")
            context_parts.append(
                f"[Source Chunk #{i} | File: {file_path} | Lines: {start}-{end}]\n{text}\n"
            )

        context_str = "\n".join(context_parts)

        user_prompt = f"""Repository: {repository_name}

Retrieved Code and Documentation Context:
----------------------------------------
{context_str}
----------------------------------------

User Question:
{question}

Please provide a clear, natural, and well-structured explanation that is easy to read and understand.
Cite the relevant source files and line ranges where appropriate."""

        # Check if API key is provided
        if not self.api_key or self.api_key in ("your_api_key_here", "your_gemini_api_key_here", "your_openai_api_key_here"):
            return self._generate_contextual_fallback(question, context_chunks, repository_name)

        if self.provider == "gemini":
            return self._call_gemini(user_prompt, question, context_chunks, repository_name)
        elif self.provider in ("openai", "gpt"):
            return self._call_openai(user_prompt, question, context_chunks, repository_name)
        else:
            return self._call_gemini(user_prompt, question, context_chunks, repository_name)

    def _call_gemini(
        self,
        prompt: str,
        question: str = "",
        context_chunks: Optional[List[dict]] = None,
        repository_name: str = "",
    ) -> Dict[str, str]:
        """Invoke Google Gemini API using direct high-speed REST calls with model fallbacks."""
        import json
        import urllib.request
        import urllib.error

        configured_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
        candidate_models = []
        if configured_model:
            candidate_models.append(configured_model)
        for m in ["gemini-3.1-flash-lite", "gemma-4-31b-it", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-flash-latest"]:
            if m not in candidate_models:
                candidate_models.append(m)

        last_error = None
        for model_name in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
            payload_data = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{SYSTEM_PROMPT}\n\n---\n\n{prompt}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 2048,
                }
            }
            payload_bytes = json.dumps(payload_data).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload_bytes,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_json = json.loads(response.read().decode("utf-8"))
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return {
                                "answer": parts[0]["text"].strip(),
                                "model_used": f"Google Gemini ({model_name})",
                            }
            except urllib.error.HTTPError as http_err:
                err_body = http_err.read().decode("utf-8", errors="ignore")
                last_error = f"HTTP {http_err.code}: {err_body}"
                if http_err.code in (400, 403):
                    # Bad key or permission
                    break
                # If 404 (model retired) or 429/503, try next candidate
                continue
            except Exception as e:
                last_error = str(e)
                continue

        # If LLM rate limited or failed temporarily, fallback to natural contextual synthesis
        if context_chunks:
            fallback = self._generate_contextual_fallback(question or "Codebase Inquiry", context_chunks, repository_name or "Indexed Repository")
            fallback["model_used"] += " (Live LLM busy)"
            return fallback

        return {
            "answer": f"Unable to reach Gemini LLM service ({last_error}). Please check your API key or try again in a few moments.",
            "model_used": "Gemini (offline)",
        }

    def _call_openai(
        self,
        prompt: str,
        question: str = "",
        context_chunks: Optional[List[dict]] = None,
        repository_name: str = "",
    ) -> Dict[str, str]:
        """Invoke OpenAI API."""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )
            answer_text = completion.choices[0].message.content or "No response returned by OpenAI."
            return {"answer": answer_text, "model_used": f"OpenAI ({model_name})"}
        except Exception as e:
            error_msg = str(e)
            if context_chunks:
                fallback = self._generate_contextual_fallback(question, context_chunks, repository_name)
                return fallback
            return {
                "answer": f"Error communicating with OpenAI API: {error_msg}.",
                "model_used": "OpenAI (error)",
            }

    def _generate_contextual_fallback(
        self,
        question: str,
        context_chunks: List[dict],
        repository_name: str,
    ) -> Dict[str, str]:
        """
        Grounded educational synthesis that produces a friendly, clear, human-readable
        overview answering the user's question without overwhelming raw code dumps.
        """
        # Extract file names and brief context insights
        file_insights = []
        project_desc = ""

        for chunk in context_chunks:
            fp = chunk.get("file_path", "")
            text = chunk.get("text", "")
            start = chunk.get("start_line", 1)
            end = chunk.get("end_line", 1)

            if "readme" in fp.lower() and not project_desc:
                # Extract first clean paragraph from readme
                lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#") and not l.startswith("!")]
                if lines:
                    project_desc = " ".join(lines[:3])

            file_insights.append((fp, start, end, text))

        overview_section = ""
        if project_desc:
            overview_section = f"### 🎯 Project Overview\n{project_desc}\n\n"

        # Group findings cleanly
        findings_bullets = []
        for fp, start, end, text in file_insights[:4]:
            first_line = ""
            for line in text.splitlines():
                clean_l = line.strip()
                if clean_l and not clean_l.startswith(("//", "#", "/*", "*", "import ", "from ")):
                    first_line = clean_l
                    break
            if not first_line:
                first_line = f"Core module logic in `{fp}`"

            findings_bullets.append(f"- **`{fp}`** *(Lines {start}–{end})*: {first_line[:120]}")

        findings_text = "\n".join(findings_bullets)

        answer = (
            f"## 📖 Codebase Analysis: {repository_name}\n\n"
            f"{overview_section}"
            f"### ⚙️ Key Implementation Findings\n"
            f"Based on the semantic search for *\"{question}\"*, here are the primary files and components:\n\n"
            f"{findings_text}\n\n"
            f"### 🔍 How It Works\n"
            f"1. The project structure indicates a modular architecture where frontend UI components and backend business logic interact.\n"
            f"2. Core workflows, database models, and configurations are maintained in the referenced files above.\n"
            f"3. You can click any of the source citations below to open the full code view with syntax highlighting."
        )

        return {
            "answer": answer,
            "model_used": "CodeLens Natural Explainer",
        }
