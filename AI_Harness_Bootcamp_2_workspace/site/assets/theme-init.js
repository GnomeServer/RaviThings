/* Applies an explicit Dark or Sand preference before first paint. */
(function () {
  try {
    var script = document.currentScript;
    if (!script || !script.src) return;
    var path = new URL(script.src).pathname;
    var marker = "assets/theme-init.js";
    var at = path.lastIndexOf(marker);
    if (at < 0) return;
    var root = path.slice(0, at);
    if (root.charAt(root.length - 1) !== "/") root += "/";
    var raw = localStorage.getItem("reformation-ui:v1:" + root);
    if (!raw) return;
    var theme = JSON.parse(raw).theme;
    if (theme === "dark" || theme === "sand") {
      document.documentElement.setAttribute("data-sc-theme", theme);
    }
  } catch (error) {
    /* Storage, parse, and URL failures leave the OS theme in place. */
  }
})();
