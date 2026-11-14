(function () {
  "use strict";
  var root = document.documentElement;

  // Theme toggle: cycles light / dark, remembered per browser.
  var themeBtn = document.getElementById("theme-toggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var dark = root.dataset.theme === "dark" ||
        (!root.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
      root.dataset.theme = dark ? "light" : "dark";
      try { localStorage.setItem("mpf-theme", root.dataset.theme); } catch (e) {}
    });
  }

  // Mobile navigation.
  var navBtn = document.getElementById("nav-toggle");
  if (navBtn) {
    navBtn.setAttribute("aria-expanded", "false");
    navBtn.addEventListener("click", function () {
      var open = document.body.classList.toggle("nav-open");
      navBtn.setAttribute("aria-expanded", String(open));
    });
  }
  // Bring the current page's link into view inside the sidebar only. scrollIntoView would also scroll the window,
  // so pages listed low in the sidebar would open part way down.
  var sidebar = document.querySelector(".sidebar");
  var current = sidebar && sidebar.querySelector("a.current");
  if (current) {
    var top = current.getBoundingClientRect().top - sidebar.getBoundingClientRect().top + sidebar.scrollTop;
    if (top + current.offsetHeight > sidebar.scrollTop + sidebar.clientHeight || top < sidebar.scrollTop) {
      sidebar.scrollTop = top - (sidebar.clientHeight - current.offsetHeight) / 2;
    }
  }

  // Copy buttons on code blocks.
  document.querySelectorAll(".doc .highlight").forEach(function (block) {
    var btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.type = "button";
    btn.textContent = "Copy";
    btn.addEventListener("click", function () {
      var code = block.querySelector("code");
      if (!code || !navigator.clipboard) return;
      navigator.clipboard.writeText(code.innerText).then(function () {
        btn.textContent = "Copied";
        setTimeout(function () { btn.textContent = "Copy"; }, 1200);
      });
    });
    block.appendChild(btn);
  });

  // Heading anchors.
  document.querySelectorAll(".doc h2[id], .doc h3[id]").forEach(function (h) {
    var a = document.createElement("a");
    a.className = "anchor";
    a.href = "#" + h.id;
    a.textContent = "#";
    a.setAttribute("aria-label", "Link to this section");
    h.appendChild(a);
  });

  // Search: titles, summaries and headings from /index.json.
  var input = document.getElementById("search");
  var list = document.getElementById("results");
  if (!input || !list) return;
  var index = null, sel = -1, items = [];

  function load() {
    if (index) return Promise.resolve(index);
    return fetch(window.MPF_SEARCH_INDEX).then(function (r) { return r.json(); })
      .then(function (data) { index = data; return data; });
  }

  // Returns [score, anchor]. Every term must match somewhere; an exact match on an anchor id
  // (a setting or event name) links straight to that row.
  function score(page, terms) {
    if (!page._t) {
      page._t = page.t.toLowerCase();
      page._d = (page.d || "").toLowerCase();
      page._h = (page.h || []).join(" ").toLowerCase();
      // event anchors are slugs (ball-started); compare with underscores so `ball_started` matches
      page._k = (page.k || []).map(function (k) { return k.toLowerCase().replace(/-/g, "_"); });
      page._kj = " " + page._k.join(" ") + " ";
      page._b = (page.b || "").toLowerCase();
    }
    var s = 0, anchor = null;
    for (var i = 0; i < terms.length; i++) {
      var term = terms[i], ki, kterm = term.replace(/-/g, "_");
      if (page._t === term || page._t === term + ":") s += 100;
      else if (page._t.indexOf(term) === 0) s += 40;
      else if (page._t.indexOf(term) >= 0) s += 25;
      else if ((ki = page._k.indexOf(kterm)) >= 0) { s += 30; anchor = anchor || page.k[ki]; }
      else if (page._h.indexOf(term) >= 0) s += 8;
      else if (page._kj.indexOf(kterm) >= 0) s += 6;
      else if (page._d.indexOf(term) >= 0) s += 4;
      else if (page._b.indexOf(term) >= 0) s += 2;
      else return [0, null];
    }
    return [s, anchor];
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text) e.textContent = text;
    return e;
  }

  function render(q) {
    var terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    list.textContent = "";
    sel = -1;
    if (!terms.length) { list.hidden = true; return; }
    items = index.map(function (p) { var r = score(p, terms); return [r[0], p, r[1]]; })
      .filter(function (x) { return x[0] > 0; })
      .sort(function (a, b) { return b[0] - a[0]; })
      .slice(0, 12);
    if (!items.length) {
      list.appendChild(el("li", "muted", "No matches"));
    }
    items.forEach(function (x) {
      var p = x[1], anchor = x[2], li = el("li"), a = el("a");
      a.href = p.u + (anchor ? "#" + anchor : "");
      a.appendChild(document.createTextNode(p.t + (anchor ? " › " + anchor : "")));
      a.appendChild(el("small", null, p.s + (p.d ? " · " + p.d : "")));
      li.appendChild(a);
      list.appendChild(li);
    });
    list.hidden = false;
  }

  function move(delta) {
    var links = list.querySelectorAll("a");
    if (!links.length) return;
    if (sel >= 0) links[sel].classList.remove("sel");
    sel = (sel + delta + links.length) % links.length;
    links[sel].classList.add("sel");
    links[sel].scrollIntoView({ block: "nearest" });
  }

  input.addEventListener("input", function () { load().then(function () { render(input.value); }); });
  input.addEventListener("focus", function () { load(); });
  input.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown") { e.preventDefault(); move(1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
    else if (e.key === "Enter") {
      var links = list.querySelectorAll("a");
      var target = links[sel >= 0 ? sel : 0];
      if (target) location.href = target.href;
    } else if (e.key === "Escape") { list.hidden = true; input.blur(); }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "/" && document.activeElement !== input &&
        !/input|textarea/i.test(document.activeElement.tagName)) {
      e.preventDefault();
      input.focus();
    }
  });
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".search")) list.hidden = true;
  });
})();
