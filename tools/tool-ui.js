(function () {
  function syncFullscreenButton(button, isFullPageTool) {
    if (!button) return;
    const label = isFullPageTool ? "返回文章" : "全屏查看";
    button.textContent = label;
    button.setAttribute("aria-label", label);
    button.title = label;
  }

  function init(root) {
    const scope = root || document;
    const toolbar = scope.querySelector(".toolbar");
    if (!toolbar || toolbar.dataset.toolUiReady === "true") return;
    toolbar.dataset.toolUiReady = "true";

    scope.querySelectorAll(".segmented").forEach((group) => {
      if (!group.hasAttribute("role")) group.setAttribute("role", "group");
      if (!group.hasAttribute("tabindex")) group.setAttribute("tabindex", "0");
    });

    scope.querySelectorAll('input[type="range"]').forEach((input) => {
      if (!input.hasAttribute("aria-label")) input.setAttribute("aria-label", "缩放比例");
    });
  }

  window.L10ToolUI = { init, syncFullscreenButton };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => init(document), { once: true });
  } else {
    init(document);
  }
})();
