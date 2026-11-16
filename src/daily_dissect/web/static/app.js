// 今日一拆 · 页面脚本（原型）
// 只做一件事：点"开始拆解"或"继续拆解"时，把按钮上 data-copy 里的指令复制到剪贴板。

async function copyText(text) {
  // 电脑上用 localhost 打开时，浏览器的剪贴板接口可以用
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (err) {
      // 被浏览器拒绝时，换下面的兼容写法
    }
  }
  // 手机通过局域网 http 打开时，剪贴板接口用不了：用一个看不见的文本框来复制
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
