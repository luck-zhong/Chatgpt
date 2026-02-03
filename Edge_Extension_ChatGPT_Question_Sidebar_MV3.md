# Edge 扩展（Manifest V3）：ChatGPT 对话提问历史侧边栏

> 目标：在 **Edge（Chromium）** 的 ChatGPT 网页里注入一个右侧侧边栏，自动收集当前对话中的 **用户提问**，并提供：  
> - 提问列表（自动更新、去重）  
> - 点击条目滚动定位到对应提问  
> - 搜索过滤  
> - 一键复制全部提问  
>  
> 说明：ChatGPT 页面 DOM 可能改版。本实现采用 **多规则选择器 + MutationObserver + 兜底解析**，尽量稳。

---

## 0. 目录结构

新建文件夹（例如）`chatgpt-question-sidebar/`，放入以下文件：

```
chatgpt-question-sidebar/
  manifest.json
  content.js
  content.css
```

---

## 1) manifest.json（MV3）

> 作用：声明扩展、注入脚本与样式，并限制生效域名（建议同时覆盖 `chat.openai.com` 与 `chatgpt.com`）。

```json
{
  "manifest_version": 3,
  "name": "ChatGPT Question Sidebar",
  "version": "0.1.0",
  "description": "Show a sidebar of user questions for the current ChatGPT conversation.",
  "permissions": ["storage"],
  "host_permissions": [
    "https://chat.openai.com/*",
    "https://chatgpt.com/*"
  ],
  "content_scripts": [
    {
      "matches": [
        "https://chat.openai.com/*",
        "https://chatgpt.com/*"
      ],
      "js": ["content.js"],
      "css": ["content.css"],
      "run_at": "document_idle"
    }
  ]
}
```

---

## 2) content.css（侧边栏样式）

> 侧边栏采用固定定位，不挤压页面内容（overlay）。你也可以改成“挤压”布局，但需要额外改页面容器样式，稳定性更差。

```css
/* 容器本体（避免和网页样式冲突） */
#cqs-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  width: 320px;
  height: 100vh;
  z-index: 999999;
  background: rgba(20, 20, 20, 0.95);
  color: #eaeaea;
  border-left: 1px solid rgba(255, 255, 255, 0.12);
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  display: flex;
  flex-direction: column;
}

/* 头部 */
#cqs-header {
  padding: 12px 12px 8px 12px;
  display: flex;
  gap: 8px;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}

#cqs-title {
  font-size: 14px;
  font-weight: 600;
  flex: 1;
  user-select: none;
}

/* 搜索框 */
#cqs-search {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  margin: 8px 12px 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.06);
  color: #eaeaea;
  outline: none;
}

#cqs-search::placeholder {
  color: rgba(234,234,234,0.6);
}

/* 按钮 */
.cqs-btn {
  padding: 6px 10px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(255,255,255,0.06);
  color: #eaeaea;
  cursor: pointer;
  user-select: none;
  font-size: 12px;
}
.cqs-btn:hover {
  background: rgba(255,255,255,0.10);
}

/* 列表 */
#cqs-list {
  flex: 1;
  overflow: auto;
  padding: 0 8px 12px 8px;
}

.cqs-item {
  padding: 10px 10px;
  margin: 6px 4px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.04);
  cursor: pointer;
}

.cqs-item:hover {
  background: rgba(255,255,255,0.08);
}

.cqs-item-title {
  font-size: 12px;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cqs-item-meta {
  margin-top: 6px;
  font-size: 11px;
  opacity: 0.7;
  display: flex;
  justify-content: space-between;
}

/* 底部状态栏 */
#cqs-footer {
  padding: 10px 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.12);
  font-size: 12px;
  opacity: 0.85;
  display: flex;
  align-items: center;
  gap: 8px;
}

#cqs-status {
  flex: 1;
}

/* 收起/展开 */
#cqs-collapsed {
  position: fixed;
  top: 12px;
  right: 12px;
  z-index: 999999;
  display: none;
}

#cqs-sidebar.cqs-hidden {
  display: none;
}
#cqs-collapsed.cqs-visible {
  display: block;
}
```

---

## 3) content.js（核心逻辑：解析提问 + 侧边栏 UI + 跳转）

> 核心点：
> - `MutationObserver` 监听对话内容变化（继续聊天时自动更新）
> - `findUserMessageNodes()` 使用多条规则寻找“用户消息节点”
> - 为每条提问节点打 `id` 锚点（便于点击跳转）
> - 去重：用文本 hash + 节点顺序生成稳定 key
> - 支持搜索过滤和复制全部提问

```js
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
```

---

## 4) 在 Edge 中加载扩展（开发者模式）

1. 打开 Edge，进入：`edge://extensions/`  
2. 右上角打开 **开发人员模式**  
3. 点击 **加载解压缩的扩展**  
4. 选择你的扩展目录：`chatgpt-question-sidebar/`

然后打开 ChatGPT 页面（`https://chat.openai.com/` 或 `https://chatgpt.com/`），右侧会出现“提问历史”侧边栏。

---

## 5) 常见问题与调试

### Q1：侧边栏出现了但列表为空
通常是 DOM 规则没匹配到用户消息节点。  
重点改 `findUserMessageNodes()`：在 F12 → Elements 里观察用户消息的稳定属性（比如 `data-message-author-role="user"`），加入第一条选择器。

### Q2：列表重复/顺序偶尔变化
使用 `hash(text)+idx` 去重；如果页面启用了懒加载/虚拟滚动，idx 可能变化。  
改进方式：使用页面内部 message-id（如果能找到）当 key。

### Q3：点击跳转不准
如果页面对历史消息采用虚拟滚动，未渲染的旧消息无法跳转。当前实现仅对已渲染内容有效。

---

## 6) 可选增强建议

- **持久化**：用 `chrome.storage.local` 按对话 URL 保存提问列表（刷新不丢）  
- **导出**：导出 Markdown/JSON  
- **分组**：按时间或每 N 条分组折叠  
- **高亮**：定位后高亮 1~2 秒

---

完成 ✅  
如果后续 ChatGPT 改版导致抓不到用户提问，把“用户消息节点”的 HTML 片段（Elements 里复制一小段）发我，我可以帮你把选择器改得更稳。
