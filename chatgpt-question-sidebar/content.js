(() => {
  "use strict";

  // ====== 工具函数 ======
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // 简单 hash，用于去重（非加密）
  function hashText(s) {
    let h = 2166136261;
    for (let i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return (h >>> 0).toString(16);
  }

  function normalizeText(t) {
    return (t || "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function truncate(t, n = 44) {
    const s = normalizeText(t);
    return s.length > n ? s.slice(0, n) + "…" : s;
  }

  function getConversationRoot() {
    // 兜底策略：优先找到包含对话消息的主区域
    // ChatGPT 页面会变，这里尽量宽松
    const candidates = [
      document.querySelector("main"),
      document.querySelector('[role="main"]'),
      document.body
    ].filter(Boolean);

    return candidates[0];
  }

  // ====== 识别用户消息节点（最关键：页面改版时主要改这里） ======
  function findUserMessageNodes() {
    const root = getConversationRoot();
    if (!root) return [];

    // 多策略：
    // 1) 直接找 role="user"（若存在）
    let nodes = Array.from(root.querySelectorAll('[data-message-author-role="user"], [data-testid="user-message"], [role="user"]'));

    // 2) 兜底：粗筛短文本块（不够完美，但通常能用）
    if (nodes.length === 0) {
      const possible = Array.from(root.querySelectorAll("article, div"));
      nodes = possible.filter((el) => {
        const txt = normalizeText(el.innerText);
        if (txt.length < 1) return false;
        if (txt.length > 2000) return false;

        const bad = /(Regenerate|Copy|Share|Retry|Stop generating)/i.test(txt);
        if (bad) return false;

        return txt.length < 600;
      });

      nodes = nodes.filter((el) => {
        const parent = el.parentElement;
        if (!parent) return true;
        const ptxt = normalizeText(parent.innerText);
        const etxt = normalizeText(el.innerText);
        return ptxt !== etxt;
      });
    }

    nodes = nodes
      .filter(Boolean)
      .sort((a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));

    return nodes;
  }

  function extractQuestionTextFromNode(node) {
    const clone = node.cloneNode(true);
    clone.querySelectorAll("button, svg, nav, footer, header").forEach((x) => x.remove());
    return normalizeText(clone.innerText);
  }

  // ====== UI 注入 ======
  function ensureSidebar() {
    if (document.getElementById("cqs-sidebar")) return;

    const sidebar = document.createElement("div");
    sidebar.id = "cqs-sidebar";
    sidebar.innerHTML = `
      <div id="cqs-header">
        <div id="cqs-title">提问历史</div>
        <button class="cqs-btn" id="cqs-btn-copy" title="复制全部提问">复制</button>
        <button class="cqs-btn" id="cqs-btn-hide" title="收起侧边栏">收起</button>
      </div>
      <input id="cqs-search" placeholder="搜索提问…" />
      <div id="cqs-list"></div>
      <div id="cqs-footer">
        <div id="cqs-status">0 条</div>
        <button class="cqs-btn" id="cqs-btn-refresh" title="重新扫描">刷新</button>
      </div>
    `;

    const collapsed = document.createElement("button");
    collapsed.id = "cqs-collapsed";
    collapsed.className = "cqs-btn";
    collapsed.textContent = "提问";
    collapsed.title = "展开提问侧边栏";

    document.body.appendChild(sidebar);
    document.body.appendChild(collapsed);

    sidebar.querySelector("#cqs-btn-hide").addEventListener("click", () => {
      sidebar.classList.add("cqs-hidden");
      collapsed.classList.add("cqs-visible");
    });

    collapsed.addEventListener("click", () => {
      sidebar.classList.remove("cqs-hidden");
      collapsed.classList.remove("cqs-visible");
    });

    sidebar.querySelector("#cqs-btn-refresh").addEventListener("click", () => {
      scanAndRender(true);
    });

    sidebar.querySelector("#cqs-btn-copy").addEventListener("click", async () => {
      const data = state.questions.map((q, i) => `${i + 1}. ${q.text}`).join("\n");
      try {
        await navigator.clipboard.writeText(data);
        setStatus(`已复制 ${state.questions.length} 条`);
        setTimeout(() => setStatus(`${state.filteredCount} 条`), 1200);
      } catch (e) {
        console.warn("Clipboard failed:", e);
        setStatus("复制失败（请检查权限）");
        setTimeout(() => setStatus(`${state.filteredCount} 条`), 1200);
      }
    });

    sidebar.querySelector("#cqs-search").addEventListener("input", (ev) => {
      state.query = normalizeText(ev.target.value).toLowerCase();
      render();
    });
  }

  // ====== 状态 ======
  const state = {
    questions: [],       // { key, text, nodeId, index }
    query: "",
    filteredCount: 0,
    lastScanSig: ""
  };

  function setStatus(s) {
    const el = document.getElementById("cqs-status");
    if (el) el.textContent = s;
  }

  function ensureNodeId(node, key) {
    if (node.id && node.id.startsWith("cqs-q-")) return node.id;
    const id = `cqs-q-${key}`;
    node.id = id;
    return id;
  }

  function buildQuestionsFromDOM() {
    const nodes = findUserMessageNodes();
    const qs = [];
    nodes.forEach((node, idx) => {
      const text = extractQuestionTextFromNode(node);
      if (!text) return;
      const key = `${hashText(text)}-${idx}`;
      const nodeId = ensureNodeId(node, key);
      qs.push({ key, text, nodeId, index: idx });
    });

    // 去重
    const seen = new Set();
    const unique = [];
    for (const q of qs) {
      const sig = `${q.key}-${q.nodeId}-${q.text}`;
      if (seen.has(sig)) continue;
      seen.add(sig);
      unique.push(q);
    }
    return unique;
  }

  function render() {
    const list = document.getElementById("cqs-list");
    if (!list) return;

    const q = state.query;
    const filtered = !q
      ? state.questions
      : state.questions.filter((x) => x.text.toLowerCase().includes(q));

    state.filteredCount = filtered.length;
    list.innerHTML = "";

    filtered.forEach((item) => {
      const el = document.createElement("div");
      el.className = "cqs-item";
      el.innerHTML = `
        <div class="cqs-item-title">${truncate(item.text, 60)}</div>
        <div class="cqs-item-meta">
          <span>#${item.index + 1}</span>
          <span>${item.text.length}字</span>
        </div>
      `;
      el.addEventListener("click", () => {
        const target = document.getElementById(item.nodeId);
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "center" });
          const old = target.style.outline;
          target.style.outline = "2px solid rgba(255,255,255,0.55)";
          setTimeout(() => (target.style.outline = old), 600);
        }
      });
      list.appendChild(el);
    });

    setStatus(`${state.filteredCount} 条`);
  }

  function scanAndRender(force = false) {
    const qs = buildQuestionsFromDOM();
    const sig = qs.map((x) => x.key).join("|");
    if (!force && sig === state.lastScanSig) return;

    state.lastScanSig = sig;
    state.questions = qs;
    render();
  }

  // ====== 监听对话变化 ======
  let observer = null;
  function startObserver() {
    const root = getConversationRoot();
    if (!root) return;

    if (observer) observer.disconnect();

    let timer = null;
    observer = new MutationObserver(() => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => scanAndRender(false), 200);
    });

    observer.observe(root, { childList: true, subtree: true });
  }

  // ====== 初始化 ======
  async function init() {
    ensureSidebar();

    for (let i = 0; i < 10; i++) {
      scanAndRender(true);
      if (state.questions.length > 0) break;
      await sleep(400);
    }

    startObserver();

    // 单页应用：监控 URL 变化以重新扫描
    let lastHref = location.href;
    setInterval(() => {
      if (location.href !== lastHref) {
        lastHref = location.href;
        scanAndRender(true);
      }
    }, 800);
  }

  init().catch(console.error);
})();
