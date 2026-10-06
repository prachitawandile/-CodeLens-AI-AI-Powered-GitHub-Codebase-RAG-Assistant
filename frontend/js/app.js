/**
 * CodeLens AI - Main Controller.
 * Binds UI interactions, indexing polling loop, chat submissions, and file navigation.
 */

window.App = {
  activeFileNodes: [],
  pollingInterval: null,

  init() {
    this.bindEvents();
    this.checkInitialStatus();
  },

  bindEvents() {
    // Brand logo returns to landing/workspace
    document.getElementById("brand-logo-btn").addEventListener("click", () => {
      // Toggle or return to landing if desired
    });

    // Change repository button
    document.getElementById("btn-new-repo").addEventListener("click", () => {
      UI.switchScreen("landing");
    });

    // Analyze button & form
    document.getElementById("btn-analyze").addEventListener("click", () => {
      this.handleAnalyze();
    });

    document.getElementById("input-repo-url").addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        this.handleAnalyze();
      }
    });

    // Sample repository chips
    document.querySelectorAll(".sample-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        const url = btn.dataset.url;
        document.getElementById("input-repo-url").value = url;
        this.handleAnalyze();
      });
    });

    // Chat form submit
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");

    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      this.handleChatSubmit();
    });

    chatInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.handleChatSubmit();
      }
    });

    // Clear chat
    document.getElementById("btn-clear-chat").addEventListener("click", () => {
      const container = document.getElementById("chat-messages-container");
      // Keep only the first welcome card
      const welcome = container.querySelector(".welcome-card");
      container.innerHTML = "";
      if (welcome) container.appendChild(welcome);
      UI.showToast("Chat cleared.");
    });

    // Clear Repository
    document.getElementById("btn-clear-repo").addEventListener("click", async () => {
      if (confirm("Are you sure you want to clear the active repository and ChromaDB collection?")) {
        try {
          await ApiService.clearRepository();
          UI.switchScreen("landing");
          document.getElementById("landing-progress-box").style.display = "none";
          document.getElementById("input-repo-url").value = "";
          UI.showToast("Repository cleared.");
        } catch (err) {
          UI.showToast(err.message, true);
        }
      }
    });

    // Workspace Tabs
    const tabChat = document.getElementById("tab-btn-chat");
    const tabViewer = document.getElementById("tab-btn-viewer");
    const panelChat = document.getElementById("tab-content-chat");
    const panelViewer = document.getElementById("tab-content-viewer");

    tabChat.addEventListener("click", () => {
      tabChat.classList.add("active");
      tabViewer.classList.remove("active");
      panelChat.classList.add("active");
      panelViewer.classList.remove("active");
    });

    tabViewer.addEventListener("click", () => {
      tabViewer.classList.add("active");
      tabChat.classList.remove("active");
      panelViewer.classList.add("active");
      panelChat.classList.remove("active");
    });

    // Copy code button in viewer
    document.getElementById("btn-copy-code").addEventListener("click", () => {
      const code = document.getElementById("viewer-code-block").textContent;
      navigator.clipboard.writeText(code).then(() => {
        UI.showToast("Code copied to clipboard!");
      });
    });

    // Modals
    document.getElementById("modal-close-btn").addEventListener("click", () => {
      document.getElementById("source-modal").style.display = "none";
    });

    document.getElementById("btn-api-info").addEventListener("click", () => {
      document.getElementById("arch-modal").style.display = "flex";
    });

    document.getElementById("arch-close-btn").addEventListener("click", () => {
      document.getElementById("arch-modal").style.display = "none";
    });

    // Close modals on outside backdrop click
    window.addEventListener("click", (e) => {
      const sourceModal = document.getElementById("source-modal");
      const archModal = document.getElementById("arch-modal");
      if (e.target === sourceModal) sourceModal.style.display = "none";
      if (e.target === archModal) archModal.style.display = "none";
    });

    // File search input filter
    document.getElementById("file-search-input").addEventListener("input", (e) => {
      const query = e.target.value.toLowerCase().trim();
      this.filterFileTree(query);
    });

    // Mobile sidebar toggle
    const mobileBtn = document.getElementById("mobile-toggle-btn");
    const sidebar = document.getElementById("workspace-sidebar");
    const sidebarClose = document.getElementById("sidebar-close-btn");

    if (mobileBtn && sidebar) {
      mobileBtn.addEventListener("click", () => sidebar.classList.toggle("open"));
      sidebarClose.addEventListener("click", () => sidebar.classList.remove("open"));
    }
  },

  /**
   * Check initial backend status on page load
   */
  async checkInitialStatus() {
    try {
      const status = await ApiService.getStatus();
      if (status.is_indexed && status.status === "ready") {
        UI.renderRepoStats(status);
        await this.loadWorkspaceData();
        UI.switchScreen("workspace");
      }
    } catch (e) {
      console.warn("Initial status check:", e);
    }
  },

  /**
   * Handle Repository Analyze trigger
   */
  async handleAnalyze() {
    UI.showLandingError(null);
    const input = document.getElementById("input-repo-url");
    const url = input.value.trim();
    const forceReindex = document.getElementById("chk-force-reindex").checked;
    const btn = document.getElementById("btn-analyze");

    if (!url) {
      UI.showLandingError("Please enter a GitHub repository URL.");
      input.focus();
      return;
    }

    if (!url.toLowerCase().includes("github.com/")) {
      UI.showLandingError("Please enter a valid GitHub repository URL (e.g. https://github.com/owner/repo).");
      input.focus();
      return;
    }

    // Set UI to loading state
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner-sm"></span> <span>Starting...</span>`;

    try {
      await ApiService.analyzeRepository(url, forceReindex);
      // Start polling for real-time progress
      this.startStatusPolling();
    } catch (err) {
      UI.showLandingError(err.message);
      btn.disabled = false;
      btn.innerHTML = `<span class="btn-text">Analyze Repository</span> <span class="btn-icon">→</span>`;
    }
  },

  /**
   * Polling loop for repository indexing status
   */
  startStatusPolling() {
    if (this.pollingInterval) clearInterval(this.pollingInterval);

    this.pollingInterval = setInterval(async () => {
      try {
        const status = await ApiService.getStatus();
        UI.updateProgress(status);

        if (status.status === "ready") {
          clearInterval(this.pollingInterval);
          this.pollingInterval = null;

          const btn = document.getElementById("btn-analyze");
          btn.disabled = false;
          btn.innerHTML = `<span class="btn-text">Analyze Repository</span> <span class="btn-icon">→</span>`;

          UI.showToast("Repository successfully indexed!");
          UI.renderRepoStats(status);
          await this.loadWorkspaceData();
          UI.switchScreen("workspace");
        } else if (status.status === "error") {
          clearInterval(this.pollingInterval);
          this.pollingInterval = null;

          const btn = document.getElementById("btn-analyze");
          btn.disabled = false;
          btn.innerHTML = `<span class="btn-text">Analyze Repository</span> <span class="btn-icon">→</span>`;

          UI.showLandingError(status.error_message || "Repository analysis failed.");
          document.getElementById("landing-progress-box").style.display = "none";
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 800);
  },

  /**
   * Load workspace file tree and suggested questions
   */
  async loadWorkspaceData() {
    try {
      // 1. Fetch file tree
      const tree = await ApiService.getFileTree();
      this.activeFileNodes = tree;
      UI.renderFileTree(tree, (filePath) => this.openFileInViewer(filePath));

      // 2. Fetch suggested questions
      const suggestions = await ApiService.getSuggestedQuestions();
      UI.renderSuggestedQuestions(suggestions, (question) => {
        const input = document.getElementById("chat-input");
        input.value = question;
        this.handleChatSubmit();
      });
    } catch (err) {
      UI.showToast("Failed to load workspace files.", true);
    }
  },

  /**
   * Handle natural-language question submission
   */
  async handleChatSubmit() {
    const input = document.getElementById("chat-input");
    const question = input.value.trim();
    if (!question) return;

    // Reset input
    input.value = "";
    input.style.height = "auto";

    // Append user message
    UI.appendChatMessage("user", question);
    UI.showTypingIndicator();

    const sendBtn = document.getElementById("btn-send-chat");
    sendBtn.disabled = true;

    try {
      const response = await ApiService.askQuestion(question);
      UI.removeTypingIndicator();
      UI.appendChatMessage("assistant", response.answer, response.sources, response.model_used);
    } catch (err) {
      UI.removeTypingIndicator();
      UI.appendChatMessage(
        "assistant",
        `❌ **Error**: ${err.message || "Could not retrieve answer."}`
      );
    } finally {
      sendBtn.disabled = false;
    }
  },

  /**
   * Open file content in File Viewer tab
   */
  async openFileInViewer(filePath) {
    try {
      const fileData = await ApiService.getFileContent(filePath);
      UI.displayFileInViewer(fileData);
      // Close mobile sidebar if open
      document.getElementById("workspace-sidebar").classList.remove("open");
    } catch (err) {
      UI.showToast(err.message, true);
    }
  },

  /**
   * Filter File Explorer
   */
  filterFileTree(query) {
    const rows = document.querySelectorAll(".tree-node-row");
    rows.forEach((row) => {
      const name = row.querySelector(".tree-name")?.textContent.toLowerCase() || "";
      if (!query || name.includes(query)) {
        row.style.display = "flex";
      } else {
        row.style.display = "none";
      }
    });
  },
};

// Initialize application on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  window.App.init();
});
