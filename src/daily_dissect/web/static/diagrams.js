// 今日一拆 · 把页面里的 Mermaid 代码画成流程图（原型）
// 只有拆解详情页加载它；mermaid.min.js 放在 assets/vendor/，不从网上加载。
// 系统在亮色、暗色之间切换时，流程图会用对应的主题重画。

(function () {
  if (!window.mermaid) return;

  const blocks = Array.from(document.querySelectorAll("pre.mermaid"));
  if (blocks.length === 0) return;

  // 画图会把代码换成图片，所以先把原始代码记下来，换主题时要用
  blocks.forEach((block) => {
    block.dataset.source = block.textContent;
  });

  const darkMode = window.matchMedia("(prefers-color-scheme: dark)");

  function render() {
    blocks.forEach((block) => {
      block.removeAttribute("data-processed");
      block.textContent = block.dataset.source;
    });
    window.mermaid.initialize({
      startOnLoad: false,
      theme: darkMode.matches ? "dark" : "neutral",
      securityLevel: "strict",
      fontFamily: getComputedStyle(document.body).fontFamily,
    });
    window.mermaid.run({ nodes: blocks });
  }

  render();
  darkMode.addEventListener("change", render);
})();
