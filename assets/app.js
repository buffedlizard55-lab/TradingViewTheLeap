/* Client-side filtering for the large tables. No dependencies, no fetch calls,
   so the page works identically on GitHub Pages and from the filesystem.

   Each table may combine a free-text search (data-search), an optional class/exchange
   <select> (data-class / data-ex), and an optional "verified return multiple" threshold
   group (data-mult + a row of <button data-t="N"> in #<threshId>). */
(function () {
  "use strict";

  function bind(inputId, selectId, tableId, countId, threshId) {
    var input = document.getElementById(inputId);
    var select = selectId ? document.getElementById(selectId) : null;
    var table = document.getElementById(tableId);
    var count = document.getElementById(countId);
    if (!input || !table) return;

    var rows = Array.prototype.slice.call(table.tBodies[0].rows);
    var thr = 0;
    var threshBtns = threshId
      ? Array.prototype.slice.call(document.querySelectorAll("#" + threshId + " button"))
      : [];

    function apply() {
      var q = (input.value || "").trim().toLowerCase();
      var ex = select ? select.value : "";
      var shown = 0;
      rows.forEach(function (row) {
        var text = row.getAttribute("data-search") || "";
        var cls = row.getAttribute("data-class") || "";
        var exc = row.getAttribute("data-ex") || "";
        var mult = parseFloat(row.getAttribute("data-mult")) || 0;
        var hit = (!q || text.indexOf(q) !== -1) &&
                  (!ex || cls === ex || exc === ex) &&
                  (thr <= 0 || mult >= thr);
        row.style.display = hit ? "" : "none";
        if (hit) shown++;
      });
      if (count) count.textContent = shown + " of " + rows.length + " shown";
    }

    input.addEventListener("input", apply);
    if (select) select.addEventListener("change", apply);
    threshBtns.forEach(function (b) {
      b.addEventListener("click", function () {
        thr = parseFloat(b.getAttribute("data-t")) || 0;
        threshBtns.forEach(function (x) { x.classList.remove("active"); });
        b.classList.add("active");
        apply();
      });
    });
    apply();
  }

  function init() {
    bind("ret-q", null, "ret-table", "ret-count", null);
    bind("vs-q", null, "vs-table", "vs-count", "vs-thresh");
    bind("ml-q", "ml-class", "ml-table", "ml-count", null);
    bind("un-q", "un-ex", "un-table", "un-count", null);

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
