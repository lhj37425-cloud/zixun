// 今日一拆 · 页面脚本
// 只做一件事：点「开始拆解」或「继续拆解」时，把 data-copy 里的整句指令复制到剪贴板。
// 定稿格式：请按照 prompts/dissect.md 拆解 https://github.com/作者/项目名

async function copyText(text) {
  // https / localhost 等安全上下文优先用 Clipboard API
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      // 被拒绝时走下面的兼容写法
    }
  }
  // file:// 打开本地网页时通常不是安全上下文：用看不见的文本框 + execCommand
  const box = document.createElement("textarea");
  box.value = text;
  box.setAttribute("readonly", "");
  box.style.position = "fixed";
  box.style.opacity = "0";
  document.body.appendChild(box);
  box.select();
  box.setSelectionRange(0, text.length);
  let ok = false;
  try {
    ok = document.execCommand("copy");
  } catch (err) {
    ok = false;
  }
  document.body.removeChild(box);
  return ok;
}

const statusRegion = document.getElementById("copy-status");

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-copy]");
  if (!button) return;

  const text = button.dataset.copy;
  const label = button.querySelector(".btn-label");
  const icon = button.querySelector("use");
  const original = button.dataset.label || label.textContent;
  button.dataset.label = original;

  const ok = await copyText(text);

  if (!ok) {
    // 两种复制方法都失败了：弹出这句话，让用户自己长按或 Ctrl+C 复制
    window.prompt("没能自动复制，请手动复制下面这句话：", text);
    if (statusRegion) statusRegion.textContent = "没能自动复制，已弹出要复制的内容";
    return;
  }

  label.textContent = "已复制";
  if (icon) icon.setAttribute("href", "#i-check");
  button.classList.add("is-copied");
  if (statusRegion) statusRegion.textContent = "已复制：" + text + "。去粘贴给 agent 就行";

  clearTimeout(button._resetTimer);
  button._resetTimer = setTimeout(() => {
    label.textContent = original;
    if (icon) icon.setAttribute("href", "#i-copy");
    button.classList.remove("is-copied");
  }, 2500);
});

// ---------- 日期切换 + 手动抓取 ----------
// 翻看已有日期不需要服务；只有「抓取这一天」要连本机服务（scripts/serve.bat）。
const tools = document.querySelector(".day-tools");

if (tools) {
  const indexBox = document.getElementById("day-index");
  const index = indexBox ? JSON.parse(indexBox.textContent) : { days: [], latest: "" };
  const root = tools.dataset.root || "";
  const dateInput = document.getElementById("jump-date");
  const fetchButton = document.getElementById("fetch-day");
  const fetchStatus = document.getElementById("fetch-status");
  const days = new Set(index.days || []);
  const latest = index.latest || "";
  const served = location.protocol === "http:" || location.protocol === "https:";

  const say = (text) => {
    fetchStatus.textContent = text;
  };
  const hrefFor = (value) =>
    value === latest ? root + "index.html" : root + "daily/" + value + ".html";

  if (served) {
    say("可以抓取。这天已有数据的话，旧文件会先备份到 data/backup/。");
  } else {
    say("翻看不需要服务；抓取要先双击 scripts\\serve.bat（或运行 uv run dd serve --open）。");
  }

  dateInput.addEventListener("change", () => {
    const value = dateInput.value;
    if (!value) return;
    if (days.has(value)) {
      window.location.href = hrefFor(value);
      return;
    }
    say(value + " 还没有数据。点「抓取这一天」补抓，历史日期只补资讯。");
  });

  fetchButton.addEventListener("click", async () => {
    const value = dateInput.value;
    if (!value) {
      say("先选一个日期。");
      return;
    }
    if (!served) {
      say("页面是双击打开的，抓取要先启动本地服务：双击 scripts\\serve.bat。");
      return;
    }
    if (value > latest) {
      say("不能抓未来的日期。");
      return;
    }
    if (days.has(value) && !window.confirm(value + " 已经有数据，重抓会覆盖。旧文件会备份到 data/backup/，继续吗？")) {
      return;
    }

    const original = fetchButton.textContent;
    fetchButton.disabled = true;
    fetchButton.textContent = "抓取中…";
    say("正在抓取，可能要 1～2 分钟，别关页面。");

    try {
      const response = await fetch("/api/radar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ date: value }),
      });
      const result = await response.json().catch(() => ({ ok: false, error: "服务返回的内容看不懂" }));
      if (!response.ok || !result.ok) {
        say("没抓成功：" + (result.error || "HTTP " + response.status));
        return;
      }
      say(result.backfill ? "补抓完成（历史日期只补资讯），正在打开…" : "抓取完成，正在打开…");
      window.location.href = hrefFor(value);
    } catch (error) {
      say("没连上本地服务：" + error.message);
    } finally {
      fetchButton.disabled = false;
      fetchButton.textContent = original;
    }
  });
}
