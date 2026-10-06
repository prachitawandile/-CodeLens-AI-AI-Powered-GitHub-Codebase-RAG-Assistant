/**
 * UI Service for CodeLens AI.
 * Handles DOM manipulation, view toggling, chat rendering, file tree, and modals.
 */

// Color map for languages
const LANG_COLORS = {
  Python: "#3572A5",
  JavaScript: "#f1e05a",
  TypeScript: "#3178c6",
  "React JSX": "#61dafb",
  "React TSX": "#2b7489",
  Java: "#b07219",
  "C++": "#f34b7d",
  C: "#555555",
  HTML: "#e34c26",
  CSS: "#563d7c",
  Markdown: "#083fa1",
  JSON: "#cbcb41",
  YAML: "#cb171e",
  SQL: "#e38c00",
  Other: "#8b949e",
};

const UI = {
  /**
   * Switch between Landing screen and Workspace screen
   */
  switchScreen(screenName) {
    const landing = document.getElementById("screen-landing");
    const workspace = document.getElementById("screen-workspace");
    const activeChip = document.getElementById("active-repo-badge-container");
    const btnNewRepo = document.getElementById("btn-new-repo");

    if (screenName === "workspace") {
      landing.style.display = "none";
      workspace.style.display = "flex";
      activeChip.style.display = "flex";
      btnNewRepo.style.display = "inline-flex";
    } else {
      landing.style.display = "block";
      workspace.style.display = "none";
      activeChip.style.display = "none";
      btnNewRepo.style.display = "none";
    }
  },

  /**
   * Show Toast Notification
   */
  showToast(message, isError = false) {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${isError ? "toast-error" : ""}`;
    toast.innerHTML = `<span>${isError ? "⚠️" : "✓"}</span> <span>${this.escapeHtml(message)}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 250);
    }, 4000);
  },

  /**
   * Show/hide landing input error
   */
  showLandingError(message) {
    const box = document.getElementById("landing-error-box");
    const msg = document.getElementById("landing-error-message");
    if (message) {
      msg.textContent = message;
      box.style.display = "flex";
    } else {
      box.style.display = "none";
    }
  },

  /**
   * Update Progress UI during repository indexing
   */
  updateProgress(status) {
    const progressBox = document.getElementById("landing-progress-box");
    const pctBadge = document.getElementById("progress-pct-badge");
    const fill = document.getElementById("progress-bar-fill");
    const title = document.getElementById("progress-step-title");
    const detail = document.getElementById("progress-step-detail");

    progressBox.style.display = "block";
    pctBadge.textContent = `${status.progress_percentage}%`;
    fill.style.width = `${status.progress_percentage}%`;
    detail.textContent = status.step_message;

    // Check checklist items
    const stepClone = document.getElementById("step-clone");
    const stepScan = document.getElementById("step-scan");
    const stepChunk = document.getElementById("step-chunk");
    const stepEmbed = document.getElementById("step-embed");
    const stepIndex = document.getElementById("step-index");

    const steps = [
      { el: stepClone, threshold: 25 },
      { el: stepScan, threshold: 45 },
      { el: stepChunk, threshold: 60 },
      { el: stepEmbed, threshold: 85 },
      { el: stepIndex, threshold: 100 },
    ];

    steps.forEach(({ el, threshold }) => {
      if (status.progress_percentage >= threshold) {
        el.className = "step-item completed";
        el.querySelector(".step-indicator").textContent = "✓";
      } else if (status.progress_percentage >= threshold - 20) {
        el.className = "step-item active";
        el.querySelector(".step-indicator").textContent = "⟳";
      } else {
        el.className = "step-item";
        el.querySelector(".step-indicator").textContent = "○";
      }
    });

    if (status.status === "cloning") {
      title.textContent = "Cloning repository...";
    } else if (status.status === "scanning") {
      title.textContent = "Scanning source code files...";
    } else if (status.status === "chunking") {
      title.textContent = "Chunking content with line preservation...";
    } else if (status.status === "embedding") {
      title.textContent = "Generating vector embeddings...";
    } else if (status.status === "ready") {
      title.textContent = "Repository Ready ✓";
    }
  },

  /**
   * Populate repository statistics in sidebar and header
   */
  renderRepoStats(status) {
    document.getElementById("header-repo-name").textContent = status.repository_name || "Repository";
    document.getElementById("sidebar-repo-title").textContent = status.repository_name || "Repository";
    document.getElementById("stat-files-count").textContent = status.files_count.toLocaleString();
    document.getElementById("stat-chunks-count").textContent = status.chunks_count.toLocaleString();
    document.getElementById("file-count-badge").textContent = `${status.files_count} files`;

    // Render language bars
    const barsContainer = document.getElementById("languages-bars");
    const tagsContainer = document.getElementById("languages-tags");
    barsContainer.innerHTML = "";
    tagsContainer.innerHTML = "";

    const languages = status.languages || {};
    const entries = Object.entries(languages);

    if (entries.length === 0) {
      tagsContainer.innerHTML = '<span class="lang-tag">No language data</span>';
      return;
    }

    entries.forEach(([lang, pct]) => {
      const color = LANG_COLORS[lang] || LANG_COLORS.Other;
      // Bar segment
      const segment = document.createElement("div");
      segment.className = "lang-bar-segment";
      segment.style.width = `${pct}%`;
      segment.style.backgroundColor = color;
      segment.title = `${lang}: ${pct}%`;
      barsContainer.appendChild(segment);

      // Tag
      const tag = document.createElement("span");
      tag.className = "lang-tag";
      tag.innerHTML = `<span class="lang-tag-dot" style="background-color: ${color};"></span> ${lang} <span style="opacity: 0.7;">${pct}%</span>`;
      tagsContainer.appendChild(tag);
    });
  },

  /**
   * Render File Tree hierarchy in Sidebar
   */
  renderFileTree(treeNodes, onFileClick) {
    const container = document.getElementById("file-tree-container");
    container.innerHTML = "";

    if (!treeNodes || treeNodes.length === 0) {
      container.innerHTML = '<div class="tree-loading">No files indexed in repository.</div>';
      return;
    }

    const fragment = document.createDocumentFragment();

    const buildTreeHTML = (nodes, depth = 0) => {
      const ul = document.createElement("div");
      ul.className = "tree-level";

      nodes.forEach((node) => {
        const row = document.createElement("div");
        row.className = "tree-node-row";
        row.dataset.path = node.path;
        row.dataset.type = node.type;

        // Indentation
        const indentSpan = document.createElement("span");
        indentSpan.className = "tree-indent";
        indentSpan.style.width = `${depth * 14}px`;
        row.appendChild(indentSpan);

        if (node.type === "directory") {
          const icon = document.createElement("span");
          icon.className = "tree-icon";
          icon.textContent = "📁";
          row.appendChild(icon);

          const name = document.createElement("span");
          name.className = "tree-name";
          name.textContent = node.name;
          row.appendChild(name);

          ul.appendChild(row);

          // Subtree
          if (node.children && node.children.length > 0) {
            const childContainer = buildTreeHTML(node.children, depth + 1);
            ul.appendChild(childContainer);

            // Toggle collapse on folder click
            row.addEventListener("click", () => {
              const isHidden = childContainer.style.display === "none";
              childContainer.style.display = isHidden ? "block" : "none";
              icon.textContent = isHidden ? "📁" : "📂";
            });
          }
        } else {
          // File node
          const icon = document.createElement("span");
          icon.className = "tree-icon";
          icon.textContent = "📄";
          row.appendChild(icon);

          const name = document.createElement("span");
          name.className = "tree-name";
          name.textContent = node.name;
          row.appendChild(name);

          row.addEventListener("click", () => {
            // Remove previous active classes
            document.querySelectorAll(".tree-node-row.active").forEach((el) => el.classList.remove("active"));
            row.classList.add("active");
            if (onFileClick) onFileClick(node.path);
          });

          ul.appendChild(row);
        }
      });

      return ul;
    };

    fragment.appendChild(buildTreeHTML(treeNodes, 0));
    container.appendChild(fragment);
  },

  /**
   * Append a chat message to the stream
   */
  appendChatMessage(role, text, sources = [], modelUsed = "") {
    const container = document.getElementById("chat-messages-container");
    const msg = document.createElement("div");
    msg.className = `chat-message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.textContent = role === "user" ? "U" : "◈";

    const body = document.createElement("div");
    body.className = "msg-body";

    // Format markdown-like text
    body.innerHTML = this.formatMarkdown(text);

    // If sources exist, append sources card
    if (sources && sources.length > 0) {
      const sourcesBox = document.createElement("div");
      sourcesBox.className = "sources-card";

      const title = document.createElement("div");
      title.className = "sources-title";
      title.textContent = `Retrieved Sources (${sources.length} citations):`;
      sourcesBox.appendChild(title);

      const list = document.createElement("div");
      list.className = "sources-list";

      sources.forEach((src) => {
        const pill = document.createElement("button");
        pill.type = "button";
        pill.className = "source-pill";
        const scorePct = Math.round(src.similarity_score * 100);
        pill.innerHTML = `<span>📄</span> <strong>${src.file_path}</strong> <span class="source-lines">L${src.start_line}-${src.end_line}</span>`;
        pill.title = `Similarity score: ${scorePct}%. Click to view chunk snippet.`;

        pill.addEventListener("click", () => {
          this.showSourceModal(src);
        });

        list.appendChild(pill);
      });

      sourcesBox.appendChild(list);
      body.appendChild(sourcesBox);
    }

    if (modelUsed && role === "assistant") {
      const modelMeta = document.createElement("div");
      modelMeta.style.fontSize = "11px";
      modelMeta.style.color = "var(--text-muted)";
      modelMeta.style.marginTop = "8px";
      modelMeta.textContent = `Model: ${modelUsed}`;
      body.appendChild(modelMeta);
    }

    msg.appendChild(avatar);
    msg.appendChild(body);
    container.appendChild(msg);

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;

    // Trigger Prism highlight
    if (window.Prism) {
      Prism.highlightAllUnder(body);
    }
  },

  /**
   * Show typing indicator in chat
   */
  showTypingIndicator() {
    const container = document.getElementById("chat-messages-container");
    const indicator = document.createElement("div");
    indicator.id = "chat-typing-indicator";
    indicator.className = "chat-message assistant";
    indicator.innerHTML = `
      <div class="msg-avatar">◈</div>
      <div class="msg-body" style="display: flex; align-items: center; gap: 8px;">
        <div class="spinner-sm"></div>
        <span style="color: var(--text-muted); font-size: 13px;">Retrieving codebase context &amp; generating grounded answer...</span>
      </div>
    `;
    container.appendChild(indicator);
    container.scrollTop = container.scrollHeight;
  },

  /**
   * Remove typing indicator
   */
  removeTypingIndicator() {
    const el = document.getElementById("chat-typing-indicator");
    if (el) el.remove();
  },

  /**
   * Render suggested questions
   */
  renderSuggestedQuestions(questions, onSelect) {
    const container = document.getElementById("suggested-questions-list");
    if (!container) return;
    container.innerHTML = "";

    questions.forEach((q) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "suggested-chip";
      chip.textContent = q;
      chip.addEventListener("click", () => {
        if (onSelect) onSelect(q);
      });
      container.appendChild(chip);
    });
  },

  /**
   * Display file in File Viewer tab
   */
  displayFileInViewer(fileData) {
    // Switch to viewer tab
    document.getElementById("tab-btn-viewer").click();

    document.getElementById("viewer-file-path").textContent = fileData.file_path;
    document.getElementById("tab-viewer-filename").textContent = fileData.file_name;
    document.getElementById("viewer-lang-badge").textContent = fileData.language || "Code";
    document.getElementById("viewer-lines-badge").textContent = `${fileData.lines_count} lines`;

    const codeBlock = document.getElementById("viewer-code-block");
    codeBlock.textContent = fileData.content;

    // Map language to Prism class
    const langLower = (fileData.language || "").toLowerCase();
    let prismLang = "javascript";
    if (langLower.includes("python")) prismLang = "python";
    else if (langLower.includes("markdown")) prismLang = "markdown";
    else if (langLower.includes("html")) prismLang = "html";
    else if (langLower.includes("css")) prismLang = "css";
    else if (langLower.includes("json")) prismLang = "json";
    else if (langLower.includes("java")) prismLang = "java";
    else if (langLower.includes("c++") || langLower.includes("cpp")) prismLang = "cpp";
    else if (langLower.includes("sql")) prismLang = "sql";
    else if (langLower.includes("typescript")) prismLang = "typescript";

    codeBlock.className = `language-${prismLang}`;
    if (window.Prism) {
      Prism.highlightElement(codeBlock);
    }
  },

  /**
   * Show Source Citation Modal
   */
  showSourceModal(source) {
    const modal = document.getElementById("source-modal");
    document.getElementById("modal-file-path").textContent = source.file_path;
    document.getElementById("modal-line-range").textContent = `Lines ${source.start_line} - ${source.end_line}`;
    const scorePct = Math.round(source.similarity_score * 100);
    document.getElementById("modal-score").textContent = `Similarity: ${scorePct}%`;

    const codeEl = document.getElementById("modal-code-snippet");
    codeEl.textContent = source.code_snippet;
    codeEl.className = "language-plaintext";

    const btnOpen = document.getElementById("btn-open-in-viewer");
    btnOpen.onclick = () => {
      modal.style.display = "none";
      if (window.App && window.App.openFileInViewer) {
        window.App.openFileInViewer(source.file_path);
      }
    };

    modal.style.display = "flex";
    if (window.Prism) {
      Prism.highlightElement(codeEl);
    }
  },

  /**
   * Basic markdown formatter for LLM responses
   */
  formatMarkdown(text) {
    if (!text) return "";
    let html = this.escapeHtml(text);

    // Code blocks ```code```
    html = html.replace(/```([\s\S]*?)```/g, (match, code) => {
      return `<pre><code>${code.trim()}</code></pre>`;
    });

    // Inline `code`
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Bold **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    // Italics *text*
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");

    // Headings ### Heading
    html = html.replace(/^### (.*$)/gim, '<h4 style="margin: 10px 0 6px; color: var(--accent-cyan);">$1</h4>');
    html = html.replace(/^## (.*$)/gim, '<h3 style="margin: 12px 0 8px; color: var(--accent-cyan);">$1</h3>');

    // Bullet points * or -
    html = html.replace(/^\s*[-*]\s+(.*$)/gim, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/s, '<ul style="padding-left: 20px; margin: 8px 0;">$1</ul>');

    // Paragraph line breaks
    html = html.replace(/\n\n/g, "<br><br>");

    return html;
  },

  escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },
};
