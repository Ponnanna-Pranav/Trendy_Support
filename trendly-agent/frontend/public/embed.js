/**
 * Trendly Support — embeddable widget loader.
 *
 * Drop this on any page:
 *   <script src="https://YOUR-DEPLOYED-URL/embed.js" data-base-url="https://YOUR-DEPLOYED-URL" async></script>
 *
 * Creates a fixed-position iframe docked bottom-right. Starts small (just
 * the launcher bubble) so it doesn't block clicks on the host page, and
 * resizes via postMessage when the visitor opens/closes the chat panel —
 * the same pattern Intercom/Drift-style widgets use, so no cross-origin
 * DOM access is needed between host page and widget.
 */
(function () {
  var currentScript = document.currentScript;
  var baseUrl = (currentScript && currentScript.getAttribute("data-base-url")) || "";
  if (!baseUrl) {
    console.error("[trendly-widget] data-base-url is required on the embed <script> tag.");
    return;
  }
  baseUrl = baseUrl.replace(/\/$/, "");

  var LAUNCHER_SIZE = "88px";
  var PANEL_WIDTH = "412px";
  var PANEL_HEIGHT = "648px";

  var iframe = document.createElement("iframe");
  iframe.src = baseUrl + "/?embed=1";
  iframe.title = "Trendly Support chat";
  iframe.style.position = "fixed";
  iframe.style.bottom = "0";
  iframe.style.right = "0";
  iframe.style.width = LAUNCHER_SIZE;
  iframe.style.height = LAUNCHER_SIZE;
  iframe.style.border = "none";
  iframe.style.background = "transparent";
  iframe.style.zIndex = "2147483000";
  iframe.style.colorScheme = "light";
  iframe.setAttribute("allowtransparency", "true");

  window.addEventListener("message", function (event) {
    var data = event.data;
    if (!data || data.source !== "trendly-widget") return;
    if (data.type === "toggle") {
      if (data.open) {
        iframe.style.width = "min(" + PANEL_WIDTH + ", 100vw)";
        iframe.style.height = "min(" + PANEL_HEIGHT + ", 85vh)";
      } else {
        iframe.style.width = LAUNCHER_SIZE;
        iframe.style.height = LAUNCHER_SIZE;
      }
    }
  });

  document.body.appendChild(iframe);
})();
