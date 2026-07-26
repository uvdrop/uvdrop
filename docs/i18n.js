/**
 * uvdrop docs i18n — ja / en / zh
 * Persistence: localStorage key `uvdrop-lang`
 * Auto-detect: navigator.language (ja* → ja, zh* → zh, else en)
 */
(function () {
  "use strict";

  var STORAGE_KEY = "uvdrop-lang";
  var SUPPORTED = ["ja", "en", "zh"];
  var cache = Object.create(null);
  var current = "en";

  function detectLang() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (saved && SUPPORTED.indexOf(saved) !== -1) return saved;
    } catch (e) { /* ignore */ }
    var nav = (navigator.language || navigator.userLanguage || "en").toLowerCase();
    if (nav.indexOf("ja") === 0) return "ja";
    if (nav.indexOf("zh") === 0) return "zh";
    return "en";
  }

  function persist(lang) {
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch (e) { /* ignore */ }
  }

  function loadDict(lang) {
    if (cache[lang]) return Promise.resolve(cache[lang]);
    return fetch("i18n/" + lang + ".json")
      .then(function (res) {
        if (!res.ok) throw new Error("i18n load failed: " + lang);
        return res.json();
      })
      .then(function (dict) {
        cache[lang] = dict;
        return dict;
      });
  }

  function apply(dict) {
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var key = el.getAttribute("data-i18n");
      if (!key || dict[key] == null) return;
      el.textContent = dict[key];
    });
    document.querySelectorAll("[data-i18n-html]").forEach(function (el) {
      var key = el.getAttribute("data-i18n-html");
      if (!key || dict[key] == null) return;
      el.innerHTML = dict[key];
    });
    if (dict["meta.title"]) document.title = dict["meta.title"];
    var meta = document.querySelector('meta[name="description"]');
    if (meta && dict["meta.description"]) {
      meta.setAttribute("content", dict["meta.description"]);
    }
    document.documentElement.lang = current;
    document.querySelectorAll("[data-lang]").forEach(function (btn) {
      var active = btn.getAttribute("data-lang") === current;
      btn.setAttribute("aria-pressed", active ? "true" : "false");
      btn.classList.toggle("is-active", active);
    });
  }

  function setLang(lang) {
    if (SUPPORTED.indexOf(lang) === -1) lang = "en";
    current = lang;
    persist(lang);
    return loadDict(lang)
      .then(apply)
      .catch(function () {
        if (lang !== "en") return setLang("en");
      });
  }

  function bindSwitcher() {
    document.querySelectorAll("[data-lang]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setLang(btn.getAttribute("data-lang"));
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindSwitcher();
    setLang(detectLang());
  });

  window.uvdropI18n = { setLang: setLang, detectLang: detectLang };
})();
