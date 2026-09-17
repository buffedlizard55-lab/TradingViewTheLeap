/* Client-side filtering and live calculator for The Leap Research Lab.
   No dependencies, no fetch calls, works offline and on GitHub Pages. */
(function () {
  "use strict";

  function bindTable(inputId, selectId, tableId, countId, threshId) {
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
        var text = (row.getAttribute("data-search") || "").toLowerCase();
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

  function bindCards(inputId, threshId, containerSelector, itemSelector, countId, attrName) {
    var input = document.getElementById(inputId);
    var thresh = document.getElementById(threshId);
    var count = document.getElementById(countId);
    var items = Array.prototype.slice.call(document.querySelectorAll(itemSelector));
    if (!items.length) return;

    var activeFilter = "";
    var threshBtns = thresh ? Array.prototype.slice.call(thresh.querySelectorAll("button")) : [];

    function apply() {
      var q = input ? (input.value || "").trim().toLowerCase() : "";
      var shown = 0;
      items.forEach(function (item) {
        var text = (item.getAttribute("data-search") || "").toLowerCase();
        var filterVal = item.getAttribute(attrName) || "";
        var matchFilter = !activeFilter || filterVal === activeFilter;
        var matchQ = !q || text.indexOf(q) !== -1;
        var hit = matchFilter && matchQ;
        item.style.display = hit ? "" : "none";
        if (hit) shown++;
      });
      if (count) count.textContent = shown + " of " + items.length + " shown";
    }

    if (input) input.addEventListener("input", apply);
    threshBtns.forEach(function (b) {
      b.addEventListener("click", function () {
        activeFilter = b.getAttribute("data-status") || b.getAttribute("data-sev") || b.getAttribute("data-tier") || "";
        threshBtns.forEach(function (x) { x.classList.remove("active"); });
        b.classList.add("active");
        apply();
      });
    });
    apply();
  }

  function initCalculator() {
    var slider = document.getElementById("calc-slider");
    var targetInput = document.getElementById("calc-target-input");
    var daysInput = document.getElementById("calc-days");
    var presetBtns = Array.prototype.slice.call(document.querySelectorAll("#calc-presets button"));

    var outEquity = document.getElementById("calc-out-equity");
    var outProfit = document.getElementById("calc-out-profit");
    var outCompound = document.getElementById("calc-out-compound");
    var outUnderlying = document.getElementById("calc-out-underlying");
    var outDays = document.getElementById("calc-out-days");

    if (!targetInput || !daysInput || !outEquity) return;

    var balance = 250000;
    var leverage = 20;

    function formatMoney(num) {
      return "$" + Math.round(num).toLocaleString("en-US");
    }

    function calculate() {
      var multiple = parseFloat(targetInput.value) || 2;
      if (multiple < 1.01) multiple = 1.01;
      var days = parseFloat(daysInput.value) || 12.54;
      if (days <= 0.01) days = 0.01;

      var endingEquity = balance * multiple;
      var netProfit = balance * (multiple - 1);
      var dailyCompoundPct = 100 * (Math.pow(multiple, 1.0 / days) - 1);
      var underlyingDailyPct = dailyCompoundPct / leverage;

      var perDayEquityGain = 1.0 + (leverage * 0.01);
      var winningDaysAt1Pct = Math.ceil(Math.log(multiple) / Math.log(perDayEquityGain));

      outEquity.textContent = formatMoney(endingEquity);
      outProfit.textContent = "+" + formatMoney(netProfit) + " net profit";
      outCompound.textContent = "+" + dailyCompoundPct.toFixed(2) + "%/day";
      outUnderlying.textContent = underlyingDailyPct.toFixed(2) + "%/day";
      outDays.textContent = winningDaysAt1Pct + " days";
    }

    if (slider) {
      slider.addEventListener("input", function () {
        targetInput.value = slider.value;
        presetBtns.forEach(function (b) {
          if (parseFloat(b.getAttribute("data-m")) === parseFloat(slider.value)) {
            b.classList.add("active");
          } else {
            b.classList.remove("active");
          }
        });
        calculate();
      });
    }

    targetInput.addEventListener("input", function () {
      if (slider) slider.value = targetInput.value;
      presetBtns.forEach(function (b) {
        if (parseFloat(b.getAttribute("data-m")) === parseFloat(targetInput.value)) {
          b.classList.add("active");
        } else {
          b.classList.remove("active");
        }
      });
      calculate();
    });

    daysInput.addEventListener("input", calculate);

    presetBtns.forEach(function (b) {
      b.addEventListener("click", function () {
        var m = parseFloat(b.getAttribute("data-m")) || 10;
        targetInput.value = m;
        if (slider) slider.value = m;
        presetBtns.forEach(function (x) { x.classList.remove("active"); });
        b.classList.add("active");
        calculate();
      });
    });

    calculate();
  }

  function init() {
    bindTable("ret-q", null, "ret-table", "ret-count", null);
    bindTable("vs-q", null, "vs-table", "vs-count", "vs-thresh");
    bindTable("ml-q", "ml-class", "ml-table", "ml-count", null);
    bindTable("un-q", "un-ex", "un-table", "un-count", null);

    bindCards("hyp-q", "hyp-thresh", "#hypotheses", "article.hyp", "hyp-count", "data-status");
    bindCards("irr-q", "irr-thresh", "#irregularities", "article.hyp", "irr-count", "data-severity");
    bindCards("src-q", "src-thresh", "#src-grid", "details.source-item", "src-count", "data-tier");

    initCalculator();

    /* Highlight the active nav item while scrolling. */
    var links = Array.prototype.slice.call(document.querySelectorAll("nav.toc a"));
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
