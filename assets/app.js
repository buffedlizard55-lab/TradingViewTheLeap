/* Client-side filtering for the three large tables. No dependencies, no fetch calls,
   so the page works identically on GitHub Pages and from the filesystem. */
(function () {
  "use strict";

  function bind(inputId, selectId, tableId, countId) {
    var input = document.getElementById(inputId);
    var select = selectId ? document.getElementById(selectId) : null;
    var table = document.getElementById(tableId);
    var count = document.getElementById(countId);
    if (!input || !table) return;

    var rows = Array.prototype.slice.call(table.tBodies[0].rows);

    function apply() {
      var q = (input.value || "").trim().toLowerCase();
      var ex = select ? select.value : "";
      var shown = 0;
      rows.forEach(function (row) {
        var text = row.getAttribute("data-search") || "";
        var cls = row.getAttribute("data-class") || "";
        var exc = row.getAttribute("data-ex") || "";
        var hit = (!q || text.indexOf(q) !== -1) &&
                  (!ex || cls === ex || exc === ex);
        row.style.display = hit ? "" : "none";
        if (hit) shown++;
      });
      if (count) {
        count.textContent = shown + " of " + rows.length + " shown";
      }
    }

    input.addEventListener("input", apply);
    if (select) select.addEventListener("change", apply);
    apply();
  }

  function init() {
    bind("ret-q", null, "ret-table", "ret-count");
    bind("vs-q", null, "vs-table", "vs-count");
    bind("ml-q", "ml-class", "ml-table", "ml-count");
    bind("un-q", "un-ex", "un-table", "un-count");

    /* Highlight the active nav item while scrolling. */
    var links = Array.prototype.slice.call(
      document.querySelectorAll("nav.toc a"));
    var sections = links
      .map(function (a) { return document.querySelector(a.getAttribute("href")); })
      .filter(Boolean);
    if (!("IntersectionObserver" in window) || !sections.length) return;

    var byId = {};
    links.forEach(function (a) {
      byId[a.getAttribute("href").slice(1)] = a;
    });

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        links.forEach(function (a) { a.style.background = ""; a.style.color = ""; });
        var active = byId[en.target.id];
        if (active) {
          active.style.background = "#1c2230";
          active.style.color = "#e6edf3";
        }
      });
    }, { rootMargin: "-15% 0px -75% 0px" });

    sections.forEach(function (s) { io.observe(s); });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
