// 拆解详情：按锚点展开对应步骤（已完成默认折叠）
(function () {
  function openStepFromHash() {
    const id = (location.hash || "").replace(/^#/, "");
    if (!id) return;
    const panel = document.getElementById(id);
    if (!panel || !panel.classList.contains("step-panel")) return;
    panel.open = true;
    // sticky 进度条会挡住标题，稍作偏移
    requestAnimationFrame(() => {
      panel.scrollIntoView({ block: "start", behavior: "instant" in window ? "instant" : "auto" });
    });
  }

  openStepFromHash();
  window.addEventListener("hashchange", openStepFromHash);
})();
