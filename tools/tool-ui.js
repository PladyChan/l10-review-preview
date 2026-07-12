(function () {
  const themeKey = "l10-theme";

  function savedTheme() {
    try {
      const value = localStorage.getItem(themeKey);
      return value === "dark" || value === "light" ? value : "";
    } catch (error) {
      return "";
    }
  }

  function applyTheme(theme) {
    if (theme === "dark" || theme === "light") {
      document.documentElement.dataset.theme = theme;
    } else {
      delete document.documentElement.dataset.theme;
    }
  }

  applyTheme(savedTheme());

  window.addEventListener("storage", (event) => {
    if (event.key === themeKey) applyTheme(savedTheme());
  });

  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin) return;
    if (event.data?.type !== "l10-theme") return;
    applyTheme(event.data.theme);
  });

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

  window.L10ToolUI = { applyTheme, init, savedTheme, syncFullscreenButton };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => init(document), { once: true });
  } else {
    init(document);
  }
})();
