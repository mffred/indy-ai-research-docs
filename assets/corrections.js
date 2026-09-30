/* Puts a "suggest a correction" flag next to each section of a document page: every h2, each
   campaign card on /flock-cancellations and each open department on /budget. The flag opens the
   GitHub correction form (.github/ISSUE_TEMPLATE/correction.yml) with the page and section filled in.
   Loaded on every page by _src/build.py; pages render some sections in the browser, so it rescans
   whenever the content changes. */
(function () {
  var SITE = "https://airesearch.myfriendfred.org";
  var FORM = "https://github.com/mffred/indy-ai-research-docs/issues/new";
  var ICON = '<svg viewBox="0 0 16 16" aria-hidden="true" shape-rendering="crispEdges">' +
    '<rect class="pole" x="3" y="1" width="2" height="14"/><path class="cloth" d="M5 2h8l-2 3 2 3H5z"/></svg>';

  var win = document.querySelector("[data-ps-title]");
  var path = location.pathname.replace(/\/+$/, "") || "/";
  if (!win || path === "/") return; // the home page is an index, not a document

  function formUrl(section) {
    var q = new URLSearchParams({
      template: "correction.yml",
      title: "Correction: " + section,
      page: SITE + path,
      claim: "Section: " + section + "\n\n"
    });
    return FORM + "?" + q.toString().replace(/\+/g, "%20"); // spaces as %20; a literal + is already %2B
  }

  function flag(section, label) {
    var a = document.createElement("a");
    a.className = "fix";
    a.href = formUrl(section);
    a.target = "_blank";
    a.rel = "noopener";
    a.title = "Suggest a correction to this section";
    a.setAttribute("aria-label", "Suggest a correction to “" + section + "”");
    a.innerHTML = ICON + (label ? "<span>" + label + "</span>" : "");
    return a;
  }

  function text(el) { return el ? el.textContent.replace(/\s+/g, " ").trim() : ""; }

  function scan() {
    win.querySelectorAll("h2").forEach(function (h) {
      if (h.querySelector(".fix") || h.closest("a")) return;
      h.appendChild(flag(text(h)));
    });
    win.querySelectorAll(".card .title-row").forEach(function (row) {
      if (row.querySelector(".fix")) return;
      row.appendChild(flag(text(row.querySelector("h3"))));
    });
    win.querySelectorAll(".dept.open > .detail").forEach(function (d) {
      if (d.querySelector(":scope > .fix-row")) return;
      var name = text(d.parentElement.querySelector(".dept-name small")) || text(d.parentElement.querySelector(".dept-name b"));
      var row = document.createElement("div");
      row.className = "fix-row";
      row.appendChild(flag(name, "Suggest a correction"));
      d.insertBefore(row, d.firstChild);
    });
  }

  var queued = false;
  new MutationObserver(function () {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () { queued = false; scan(); });
  }).observe(win, { childList: true, subtree: true });
  scan();
})();
