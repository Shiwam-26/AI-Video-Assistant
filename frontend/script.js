
const API_BASE = "";

const state = {
  page: "home",
  sourceType: "youtube",
  sessionId: null,
  analysis: null,
  chatHistory: [],
  resultTab: "summary",
  busy: false,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const pageNames = {
  home: "Home",
  insights: "Video Insights",
  chat: "AI Chat",
};

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("show");

  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(
    () => toast.classList.remove("show"),
    3400
  );
}

function navigate(page) {
  state.page = page;

  $$(".page").forEach((el) => {
    el.classList.toggle("active", el.id === `page-${page}`);
  });

  $$(".nav-item").forEach((el) => {
    el.classList.toggle("active", el.dataset.page === page);
  });

  $("#currentSection").textContent = pageNames[page] || "Home";
  $("#sidebar").classList.remove("open");

  if (page === "insights") renderInsights();
  if (page === "chat") renderChatContext();

  window.scrollTo({ top: 0, behavior: "smooth" });
}

$$(".nav-item").forEach((button) => {
  button.addEventListener("click", () => {
    navigate(button.dataset.page);
  });
});

$$("[data-go]").forEach((button) => {
  button.addEventListener("click", () => {
    navigate(button.dataset.go);
  });
});

$("#mobileMenu").addEventListener("click", () => {
  $("#sidebar").classList.toggle("open");
});

function setSource(type) {
  state.sourceType = type;

  $$(".source-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.source === type);
  });

  $("#urlGroup").classList.toggle("hidden", type !== "youtube");
  $("#fileGroup").classList.toggle("hidden", type !== "file");
}

$$(".source-tab").forEach((button) => {
  button.addEventListener("click", () => {
    setSource(button.dataset.source);
  });
});

$("#videoFile").addEventListener("change", (event) => {
  const file = event.target.files[0];

  $("#uploadTitle").textContent = file
    ? file.name
    : "Drop your file here or browse";

  $("#uploadSubtitle").textContent = file
    ? `${(file.size / (1024 * 1024)).toFixed(1)} MB · Ready to upload`
    : "MP3, WAV, M4A, MP4, MOV, MKV, WEBM";
});

function setNotice(message, type = "info") {
  const notice = $("#notice");
  notice.textContent = message;
  notice.className = `notice ${type}`;
}

function hideNotice() {
  $("#notice").classList.add("hidden");
}

function setBusy(busy) {
  state.busy = busy;

  $("#analyzeButton").disabled = busy;

  $("#analyzeButton").innerHTML = busy
    ? "<span>◌</span> Analyzing..."
    : "<span>✦</span> Analyze video <span class='button-arrow'>→</span>";

  $("#progressArea").classList.toggle("hidden", !busy);
}

$("#analyzeForm").addEventListener("submit", async (event) => {
  event.preventDefault();

  if (state.busy) return;

  hideNotice();

  const formData = new FormData();

  formData.append("source_type", state.sourceType);
  formData.append("language", $("#language").value);

  if (state.sourceType === "youtube") {
    const url = $("#videoUrl").value.trim();

    if (!url) {
      setNotice("Please paste a YouTube URL first.", "error");
      $("#videoUrl").focus();
      return;
    }

    formData.append("url", url);
  } else {
    const file = $("#videoFile").files[0];

    if (!file) {
      setNotice("Please select an audio or video file.", "error");
      return;
    }

    formData.append("file", file);
  }

  setBusy(true);

  try {
    const response = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Video analysis failed.");
    }

    state.sessionId = data.session_id;
    state.analysis = data;
    state.chatHistory = [];
    state.resultTab = "summary";

    $("#sessionStatus").textContent = "Video analyzed successfully";

    setNotice(
      "Analysis completed! Your summary and insights are ready.",
      "success"
    );

    renderInsights();
    renderChatContext();
    renderChat();

    showToast("Video analysis completed successfully.");
  } catch (error) {
    setNotice(
      error.message || "Something went wrong. Check the backend terminal.",
      "error"
    );
  } finally {
    setBusy(false);
  }
});

const resultTabs = {
  summary: {
    title: "Video summary",
    field: "summary",
  },
  actions: {
    title: "Action items",
    field: "action_items",
  },
  decisions: {
    title: "Key decisions",
    field: "key_decisions",
  },
  questions: {
    title: "Open questions",
    field: "open_questions",
  },
  transcript: {
    title: "Full transcript",
    field: "transcript",
  },
};

function renderInsights() {
  const hasData = Boolean(state.analysis);

  $("#insightsEmpty").classList.toggle("hidden", hasData);
  $("#insightsContent").classList.toggle("hidden", !hasData);

  if (!hasData) return;

  $("#resultTitle").textContent =
    state.analysis.title || "Video Analysis";

  $("#transcriptCount").textContent =
    (state.analysis.transcript || "").length.toLocaleString();

  selectResultTab(state.resultTab);
}

function selectResultTab(tab) {
  state.resultTab = tab;

  $$(".result-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.result === tab);
  });

  const config = resultTabs[tab];

  if (!config || !state.analysis) return;

  $("#resultPanelTitle").textContent = config.title;

  const content =
    state.analysis[config.field] || "No content available for this section.";

  const isTranscript = tab === "transcript";

  $("#resultText").classList.toggle("hidden", isTranscript);
  $("#transcriptBox").classList.toggle("hidden", !isTranscript);
  $("#downloadRow").classList.toggle("hidden", !isTranscript);

  $("#resultText").textContent = isTranscript ? "" : content;

  $("#transcriptBox").value = isTranscript
    ? state.analysis.transcript || ""
    : "";
}

$$(".result-tab").forEach((button) => {
  button.addEventListener("click", () => {
    selectResultTab(button.dataset.result);
  });
});

$("#copyResult").addEventListener("click", async () => {
  if (!state.analysis) return;

  const config = resultTabs[state.resultTab];
  const text = state.analysis[config.field] || "";

  try {
    await navigator.clipboard.writeText(text);
    showToast("Copied to clipboard.");
  } catch {
    showToast("Clipboard access is unavailable in this browser.");
  }
});

$("#downloadTranscript").addEventListener("click", () => {
  const transcript = state.analysis?.transcript || "";

  const blob = new Blob([transcript], {
    type: "text/plain;charset=utf-8",
  });

  const link = document.createElement("a");

  link.href = URL.createObjectURL(blob);
  link.download = "video_transcript.txt";
  link.click();

  URL.revokeObjectURL(link.href);
});

function renderChatContext() {
  const hasData = Boolean(state.analysis);

  $("#chatContextEmpty").classList.toggle("hidden", hasData);
  $("#chatContext").classList.toggle("hidden", !hasData);

  if (hasData) {
    $("#contextTitle").textContent =
      state.analysis.title || "Video Analysis";
  }
}

function renderChat() {
  const container = $("#chatMessages");

  container.innerHTML = "";

  if (state.chatHistory.length === 0) {
    const welcome = document.createElement("div");

    welcome.className = "chat-welcome";

    welcome.innerHTML = `
      <div class="welcome-orb">✦</div>
      <h2>Let's explore your video</h2>
      <p>Ask about the main ideas, decisions, or details in your analyzed video.</p>

      <div class="suggestion-list">
        <button class="suggestion" data-question="What is the main idea of this video?">
          What is the main idea of this video? <span>↗</span>
        </button>

        <button class="suggestion" data-question="Summarize the most important points.">
          Summarize the most important points. <span>↗</span>
        </button>

        <button class="suggestion" data-question="What action items or decisions were mentioned?">
          What action items or decisions were mentioned? <span>↗</span>
        </button>
      </div>
    `;

    container.appendChild(welcome);

    welcome.querySelectorAll("[data-question]").forEach((button) => {
      button.addEventListener("click", () => {
        sendQuestion(button.dataset.question);
      });
    });

    return;
  }

  state.chatHistory.forEach((message) => {
    const row = document.createElement("div");
    row.className = `chat-message ${message.role}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = message.role === "user" ? "You" : "✦";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = message.content;

    row.append(avatar, bubble);
    container.appendChild(row);
  });

  container.scrollTop = container.scrollHeight;
}

async function sendQuestion(question) {
  const cleanQuestion = question.trim();

  if (!cleanQuestion || state.busy) return;

  if (!state.sessionId) {
    showToast("Analyze a video first, then you can chat with it.");
    navigate("home");
    return;
  }

  state.chatHistory.push({
    role: "user",
    content: cleanQuestion,
  });

  renderChat();

  const sendButton = $("#sendButton");
  sendButton.disabled = true;

  const thinking = document.createElement("div");
  thinking.className = "chat-message assistant";
  thinking.id = "thinkingMessage";

  thinking.innerHTML = `
    <div class="message-avatar">✦</div>
    <div class="message-bubble">
      <span class="spinner" style="display:inline-block;vertical-align:middle;width:14px;height:14px"></span>
      Thinking...
    </div>
  `;

  $("#chatMessages").appendChild(thinking);
  $("#chatMessages").scrollTop = $("#chatMessages").scrollHeight;

  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        session_id: state.sessionId,
        question: cleanQuestion,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Could not get an answer.");
    }

    state.chatHistory.push({
      role: "assistant",
      content: data.answer || "No answer was returned.",
    });
  } catch (error) {
    state.chatHistory.push({
      role: "assistant",
      content: `Sorry, I couldn't answer that. ${error.message}`,
    });
  } finally {
    sendButton.disabled = false;
    renderChat();
    $("#chatInput").focus();
  }
}

$("#chatForm").addEventListener("submit", (event) => {
  event.preventDefault();

  const input = $("#chatInput");
  const question = input.value;

  if (!question.trim()) return;

  input.value = "";
  sendQuestion(question);
});

$$("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    sendQuestion(button.dataset.question);
  });
});

$("#clearChat").addEventListener("click", () => {
  state.chatHistory = [];
  renderChat();
});

$("#resetButton").addEventListener("click", () => {
  state.analysis = null;
  state.sessionId = null;
  state.chatHistory = [];
  state.resultTab = "summary";

  $("#videoUrl").value = "";
  $("#videoFile").value = "";

  $("#uploadTitle").textContent = "Drop your file here or browse";
  $("#uploadSubtitle").textContent =
    "MP3, WAV, M4A, MP4, MOV, MKV, WEBM";

  $("#sessionStatus").textContent = "No video analyzed yet";

  hideNotice();
  renderInsights();
  renderChatContext();
  renderChat();
  navigate("home");

  showToast("Workspace has been reset.");
});

// Initial render
renderInsights();
renderChatContext();
renderChat();
