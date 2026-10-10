/* Carnet de rencontres — un seul fichier, sans dépendance.
   Chaque bloc ne s'active que si les éléments de sa page sont présents. */
(() => {
  "use strict";
  document.documentElement.classList.add("js");

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const csrf = () => $('meta[name="csrf-token"]')?.content || "";
  const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmtViews = (v) => {
    v = Number(v) || 0;
    if (v >= 1e6) return (v / 1e6).toFixed(1).replace(".", ",").replace(",0", "") + " M";
    if (v >= 1e4) return Math.round(v / 1e3) + " k";
    if (v >= 1e3) return (v / 1e3).toFixed(1).replace(".", ",").replace(",0", "") + " k";
    return String(Math.round(v));
  };

  /* ───────────── Partout ───────────── */

  $$(".toast").forEach((t) => {
    const close = () => t.remove();
    $(".toast-close", t)?.addEventListener("click", close);
    if (!t.classList.contains("toast-error")) setTimeout(close, 6000);
  });

  document.addEventListener("submit", (e) => {
    const form = e.target;
    const msg = form.dataset.confirm;
    if (msg && !confirm(msg)) { e.preventDefault(); return; }
    const btn = e.submitter;
    if (btn?.dataset.busy) {
      btn.classList.add("is-busy");
      btn.textContent = btn.dataset.busy;
      setTimeout(() => { btn.disabled = true; }, 0);
    }
  });

  // « Retour à la liste » : revient exactement où on était (filtres, page, défilement)
  $$("[data-back]").forEach((a) => a.addEventListener("click", (e) => {
    try {
      const ref = new URL(document.referrer);
      if (ref.origin === location.origin && ref.pathname === new URL(a.href).pathname) {
        e.preventDefault();
        history.back();
      }
    } catch (_) { /* pas de referrer */ }
  }));

  /* ───────────── Liste : filtres sans rechargement ───────────── */

  const filters = $("#filters");
  const results = $("#results");

  if (filters && results) {
    let controller = null;
    const F = filters.elements;
    const fold = (s) => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");

    /* ── Retour arrière : on revient au même endroit de la page ── */
    const SCROLL_KEY = "celebs:list-scroll";
    if ("scrollRestoration" in history) history.scrollRestoration = "manual";
    const saveScroll = () => {
      try { sessionStorage.setItem(SCROLL_KEY, JSON.stringify({ url: location.href, y: window.scrollY })); } catch (_) {}
    };
    const restoreScroll = () => {
      let saved = null;
      try { saved = JSON.parse(sessionStorage.getItem(SCROLL_KEY) || "null"); } catch (_) {}
      if (!saved || saved.url !== location.href) return;
      const go = () => window.scrollTo(0, saved.y);
      go();
      requestAnimationFrame(go);
      document.fonts?.ready.then(go);
      window.addEventListener("load", go, { once: true });
    };
    window.addEventListener("scroll", debounce(saveScroll, 150), { passive: true });
    window.addEventListener("pagehide", saveScroll);
    const nav = performance.getEntriesByType?.("navigation")[0];
    if (nav?.type === "back_forward" || nav?.type === "reload") restoreScroll();
    window.addEventListener("pageshow", (e) => { if (e.persisted) restoreScroll(); });

    /* ── Construction de l'URL ── */
    const formUrl = () => {
      const params = new URLSearchParams();
      // Un secteur coché couvre déjà ses activités : inutile de les répéter dans l'URL
      const sectors = new Set($$("input[data-cat]:checked", filters).map((i) => i.value));
      for (const [k, v] of new FormData(filters)) {
        if (String(v).trim() === "") continue;
        if (k === "act") {
          const input = filters.querySelector(`input[name=act][value="${CSS.escape(v)}"]`);
          if (input && sectors.has(input.dataset.actCat)) continue;
        }
        params.append(k, v);
      }
      if (params.get("sort") === "name") params.delete("sort");
      if (params.get("view") === "table") params.delete("view");
      if (params.get("per") === "50") params.delete("per");
      const qs = params.toString();
      return location.pathname + (qs ? "?" + qs : "");
    };

    const syncHidden = (url) => {
      const params = new URL(url, location.href).searchParams;
      F.sort.value = params.get("sort") || "name";
      F.view.value = params.get("view") || "table";
      F.per.value = params.get("per") || "50";
    };

    const load = async (url, { scroll = false } = {}) => {
      controller?.abort();
      controller = new AbortController();
      results.classList.add("is-loading");
      try {
        const res = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" }, signal: controller.signal });
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();
        results.innerHTML = data.results;
        history.replaceState(null, "", url);
        syncHidden(url);
        updateFilterCount();
        if (scroll) results.closest(".results-wrap").scrollIntoView({ behavior: "smooth", block: "start" });
        saveScroll();
      } catch (err) {
        if (err.name !== "AbortError") { console.error(err); location.href = url; }
      } finally {
        results.classList.remove("is-loading");
      }
    };
    const refresh = () => load(formUrl());

    /* ── Secteurs ↔ activités ── */
    const syncSectorFromActivities = (catId) => {
      const sector = filters.querySelector(`input[data-cat="${catId}"]`);
      const acts = $$(`input[data-act-cat="${catId}"]`, filters);
      if (sector && acts.length) sector.checked = acts.every((a) => a.checked);
    };

    filters.addEventListener("submit", (e) => { e.preventDefault(); refresh(); });
    filters.addEventListener("change", (e) => {
      const t = e.target;
      if (t.classList.contains("facet-find") || t === F.q) return;
      if (t.dataset.cat) {
        // Cocher un secteur coche toutes ses activités (et inversement)
        $$(`input[data-act-cat="${t.dataset.cat}"]`, filters).forEach((a) => { a.checked = t.checked; });
      } else if (t.dataset.actCat) {
        syncSectorFromActivities(t.dataset.actCat);
      }
      refresh();
    });
    F.q.addEventListener("input", debounce(refresh, 300));
    F.loc.addEventListener("input", debounce(refresh, 400));

    /* ── Champ « Filtrer la liste » des activités ── */
    $$(".facet-find", filters).forEach((input) => {
      const box = $(input.dataset.find);
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") e.preventDefault(); });
      input.addEventListener("input", () => {
        const needle = fold(input.value.trim());
        $$(".chip", box).forEach((chip) => {
          chip.hidden = !!needle && !fold(chip.dataset.name).includes(needle);
        });
        $$(".activity-group", box).forEach((g) => { g.hidden = !$$(".chip:not([hidden])", g).length; });
      });
    });

    const toggle = $(".filters-toggle", filters);
    toggle?.addEventListener("click", () => {
      const open = filters.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open);
    });

    const updateFilterCount = () => {
      if (!toggle) return;
      const n = [F.q.value, $$("input[name=cat]:checked", filters).length, $$("input[name=act]:checked", filters).length,
        F.loc.value, F.from.value || F.to.value, F.year.value, F.nophoto.checked].filter(Boolean).length;
      toggle.innerHTML = "Filtres" + (n ? ` <span class="count-pill">${n}</span>` : "");
    };

    const resetAll = () => {
      $$("input[type=text], input[type=search], input[type=date]", filters).forEach((i) => { i.value = ""; });
      $$("input[type=checkbox]", filters).forEach((i) => { i.checked = false; });
      F.year.value = "";
      $$(".chip, .activity-group", filters).forEach((c) => { c.hidden = false; });
      refresh();
    };

    /* ── Suggestions de la barre de recherche ── */
    const searchBox = $(".search", filters);
    const searchList = $("#search-options");
    let sItems = [];
    let sActive = -1;
    const closeSearch = () => { searchList.hidden = true; F.q.setAttribute("aria-expanded", "false"); sActive = -1; };
    const KIND = { person: "Personne", activity: "Activité", sector: "Secteur" };
    const renderSearch = () => {
      if (!sItems.length) { closeSearch(); return; }
      searchList.innerHTML = sItems.map((it, i) => {
        const mark = it.type === "person"
          ? (it.avatar ? `<span class="s-mark s-person"><img src="${esc(it.avatar)}" alt=""></span>`
                       : `<span class="s-mark s-person">${esc(it.initials)}</span>`)
          : `<span class="s-mark s-${it.type}" aria-hidden="true"></span>`;
        return `<li role="option" data-i="${i}" aria-selected="${i === sActive}" class="s-row s-row-${it.type}">
          ${mark}<span class="s-text"><span class="s-label">${esc(it.label)}</span>
          <small class="s-kind">${KIND[it.type]}${it.meta ? ", " + esc(it.meta) : ""}</small></span></li>`;
      }).join("");
      searchList.hidden = false;
      F.q.setAttribute("aria-expanded", "true");
    };
    const fetchSearch = debounce(async () => {
      const q = F.q.value.trim();
      if (!q) { sItems = []; closeSearch(); return; }
      try {
        const data = await fetch(`${searchBox.dataset.suggestUrl}?q=${encodeURIComponent(q)}`).then((r) => r.json());
        if (F.q.value.trim() !== q) return;
        sItems = data.items || [];
        sActive = -1;
        if (document.activeElement === F.q) renderSearch();
      } catch (_) { closeSearch(); }
    }, 120);
    const pickSearch = (it) => {
      closeSearch();
      if (it.type === "person") { saveScroll(); location.href = it.url; return; }
      F.q.value = "";
      if (it.type === "activity") {
        const input = filters.querySelector(`input[name=act][value="${it.id}"]`);
        if (input) { input.checked = true; syncSectorFromActivities(input.dataset.actCat); }
      } else {
        const input = filters.querySelector(`input[data-cat="${it.id}"]`);
        if (input) {
          input.checked = true;
          $$(`input[data-act-cat="${it.id}"]`, filters).forEach((a) => { a.checked = true; });
        }
      }
      refresh();
    };
    F.q.addEventListener("input", fetchSearch);
    F.q.addEventListener("focus", () => { if (F.q.value.trim()) fetchSearch(); });
    F.q.addEventListener("blur", () => setTimeout(closeSearch, 150));
    F.q.addEventListener("keydown", (e) => {
      if (searchList.hidden) return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        sActive = (sActive + (e.key === "ArrowDown" ? 1 : -1) + sItems.length) % sItems.length;
        renderSearch();
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (sActive >= 0) pickSearch(sItems[sActive]); else closeSearch();
      } else if (e.key === "Escape") {
        closeSearch();
      }
    });
    searchList.addEventListener("mousedown", (e) => {
      const li = e.target.closest("li[data-i]");
      if (li) { e.preventDefault(); pickSearch(sItems[Number(li.dataset.i)]); }
    });

    /* ── Clics et menus dans la zone des résultats ── */
    document.addEventListener("click", (e) => {
      const reset = e.target.closest("[data-reset]");
      if (reset && (filters.contains(reset) || results.contains(reset))) { e.preventDefault(); resetAll(); return; }

      const link = e.target.closest("#results a[href^='?']");
      if (link && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        load(location.pathname + link.getAttribute("href"), { scroll: !!link.dataset.page });
        return;
      }
      // Lien vers une fiche : on mémorise la position pour le retour
      if (e.target.closest("#results a[href]")) saveScroll();
    });

    results.addEventListener("change", (e) => {
      const param = e.target.dataset.param;
      if (!param) return;
      F[param].value = e.target.value;
      refresh();
    });

    /* ── Mise à jour de la popularité par lots ── */
    const runner = $("#pop-runner");
    let running = false;
    let stopRequested = false;

    window.addEventListener("beforeunload", (e) => { if (running) { e.preventDefault(); e.returnValue = ""; } });

    runner && $("[data-stop]", runner).addEventListener("click", () => { stopRequested = true; });

    results.addEventListener("click", async (e) => {
      const btn = e.target.closest("[data-update-popularity]");
      if (!btn || running) return;
      running = true; stopRequested = false;
      btn.disabled = true;

      const sep = location.search ? "&" : "?";
      const listing = await fetch(location.pathname + location.search + sep + "with_ids=1",
        { headers: { "X-Requested-With": "XMLHttpRequest" } }).then((r) => r.json());
      const ids = listing.ids || [];
      const set = (sel, v) => { $(sel, runner).textContent = v; };
      runner.hidden = false;
      set("[data-total]", ids.length); set("[data-done]", 0); set("[data-errors]", 0);
      $("[data-fill]", runner).style.width = "0%";

      let done = 0, errors = 0;
      for (let i = 0; i < ids.length && !stopRequested; i += 8) {
        const body = new URLSearchParams();
        ids.slice(i, i + 8).forEach((id) => body.append("ids", id));
        try {
          const res = await fetch(btn.dataset.url, {
            method: "POST",
            headers: { "X-CSRFToken": csrf(), "X-Requested-With": "XMLHttpRequest" },
            body,
          });
          if (!res.ok) throw new Error(res.status);
          const data = await res.json();
          for (const r of data.results) {
            if (!r.ok) { errors++; continue; }
            const cell = $(`tr[data-id="${r.id}"] [data-pop]`, results);
            if (cell) {
              cell.innerHTML = `<span class="pop-value">${fmtViews(r.score)}</span>`;
              cell.classList.add("is-updated");
            }
          }
        } catch (_) {
          errors += Math.min(8, ids.length - i);
        }
        done = Math.min(ids.length, i + 8);
        set("[data-done]", done); set("[data-errors]", errors);
        $("[data-fill]", runner).style.width = (done / ids.length * 100) + "%";
      }

      running = false;
      btn.disabled = false;
      $("strong", runner).textContent = stopRequested ? "Mise à jour arrêtée" : "Popularité à jour";
      setTimeout(() => { runner.hidden = true; $("strong", runner).textContent = "Mise à jour de la popularité"; load(location.pathname + location.search); }, 2500);
    });
  }

  /* ───────────── Formulaire célébrité ───────────── */

  const form = $("#celeb-form");
  if (form) {
    const mode = form.dataset.mode;
    const nameInput = $("#id_name");
    const status = $("#name-status");
    const existingId = $("#existing-id");
    const newFields = $("#new-celeb-fields");
    const suggestions = $("#photo-suggestions");
    const preview = $("#photo-preview");
    const fileInput = $("#id_image");
    const urlInput = $("#id_image_url");
    const originalName = nameInput.value;
    const originalPreview = preview.innerHTML;

    /* Nom : déjà dans le carnet ? */
    let lastQuery = "";
    const checkName = debounce(async () => {
      const name = nameInput.value.trim();
      if (name === lastQuery) return;
      lastQuery = name;
      if (name.length < 2 || (mode === "edit" && name === originalName)) {
        status.innerHTML = ""; existingId.value = ""; newFields.hidden = false;
        return;
      }
      const data = await fetch(`${form.dataset.checkUrl}?name=${encodeURIComponent(name)}`).then((r) => r.json());
      if (nameInput.value.trim() !== name) return;

      if (data.exists && (mode === "add")) {
        const avatar = data.avatar ? `<span class="avatar"><img src="${esc(data.avatar)}" alt=""></span>` : "";
        status.innerHTML = `<div class="known">${avatar}<span><a href="${esc(data.url)}">${esc(data.name)}</a> est déjà dans le carnet
          (${data.count} rencontre${data.count > 1 ? "s" : ""}). Celle-ci sera la n°${data.count + 1}.</span></div>`;
        existingId.value = data.celebrity_id;
        newFields.hidden = true;
        return;
      }
      existingId.value = "";
      newFields.hidden = false;
      if (data.exists && mode === "edit") {
        status.innerHTML = `Attention, une autre fiche porte déjà ce nom : <a href="${esc(data.url)}">${esc(data.name)}</a>.`;
      } else if (data.similar?.length) {
        status.innerHTML = `<span class="similar">Noms proches dans le carnet : ${data.similar
          .map((s) => `<a href="${esc(s.url)}">${esc(s.name)}</a>`).join("")}</span>`;
      } else {
        status.innerHTML = mode === "add" ? "Nouvelle personne dans le carnet." : "";
      }
      if (mode === "add") loadSuggestions(name);
    }, 300);
    nameInput.addEventListener("input", checkName);
    if (mode === "add" && nameInput.value) checkName();

    /* Photos proposées (Wikimedia Commons) */
    let photoQuery = "";
    const loadSuggestions = debounce(async (name) => {
      if (!suggestions || name.length < 3 || name === photoQuery) return;
      photoQuery = name;
      suggestions.innerHTML = '<span class="suggestion-skel"></span>'.repeat(5);
      try {
        const data = await fetch(`${form.dataset.imagesUrl}?name=${encodeURIComponent(name)}`).then((r) => r.json());
        if (photoQuery !== name) return;
        if (!data.results?.length) {
          suggestions.innerHTML = `<p class="muted suggestions-note">Aucune photo trouvée sur Wikimedia pour « ${esc(name)} ». Importez la vôtre.</p>`;
          return;
        }
        suggestions.innerHTML = data.results.map((r) => `
          <button type="button" class="suggestion" aria-pressed="false" data-url="${esc(r.url)}"
                  title="${esc(r.source)}${r.license ? ", " + esc(r.license) : ""}">
            <img src="${esc(r.thumb)}" alt="Photo proposée" loading="lazy" referrerpolicy="no-referrer">
          </button>`).join("");
      } catch (_) {
        suggestions.innerHTML = '<p class="muted suggestions-note">Impossible de joindre Wikimedia pour le moment.</p>';
      }
    }, 650);

    $("[data-load-suggestions]")?.addEventListener("click", (e) => {
      e.target.hidden = true;
      photoQuery = "";
      loadSuggestions(nameInput.value.trim());
    });

    suggestions?.addEventListener("click", (e) => {
      const btn = e.target.closest(".suggestion");
      if (!btn) return;
      const already = btn.getAttribute("aria-pressed") === "true";
      $$(".suggestion", suggestions).forEach((b) => b.setAttribute("aria-pressed", "false"));
      if (already) {
        urlInput.value = "";
        preview.innerHTML = originalPreview;
        return;
      }
      btn.setAttribute("aria-pressed", "true");
      urlInput.value = btn.dataset.url;
      fileInput.value = "";
      $("#upload-name").textContent = "";
      preview.innerHTML = `<img src="${esc(btn.dataset.url)}" alt="Photo choisie" referrerpolicy="no-referrer">`;
    });

    fileInput?.addEventListener("change", () => {
      const file = fileInput.files[0];
      if (!file || !file.type.startsWith("image/")) return;
      urlInput.value = "";
      $$(".suggestion", suggestions).forEach((b) => b.setAttribute("aria-pressed", "false"));
      $("#upload-name").textContent = file.name;
      const reader = new FileReader();
      reader.onload = (ev) => { preview.innerHTML = `<img src="${ev.target.result}" alt="Aperçu">`; };
      reader.readAsDataURL(file);
    });

    /* Activités : étiquettes + autocomplétion au clavier */
    const hidden = $("#id_activities");
    // Le JS remplace le champ texte par le sélecteur à étiquettes
    $("#activity-picker").hidden = false;
    $("#activities-raw").hidden = true;
    const tagList = $("#activity-tags");
    const search = $("#activity-search");
    const options = $("#activity-options");
    let tags = (hidden.value || "").split(",").map((s) => s.trim()).filter(Boolean);
    let items = [];
    let active = -1;

    const renderTags = () => {
      hidden.value = tags.join(", ");
      tagList.innerHTML = tags.map((t, i) =>
        `<li>${esc(t)}<button type="button" data-remove="${i}" aria-label="Retirer ${esc(t)}">×</button></li>`).join("");
    };
    const addTag = (name) => {
      name = name.trim().replace(/\s+/g, " ");
      if (name && !tags.some((t) => t.toLowerCase() === name.toLowerCase())) tags.push(name);
      renderTags();
      search.value = "";
      closeOptions();
      search.focus();
    };
    const closeOptions = () => { options.hidden = true; search.setAttribute("aria-expanded", "false"); active = -1; };
    const renderOptions = () => {
      const q = search.value.trim();
      const exact = items.some((it) => it.name.toLowerCase() === q.toLowerCase());
      const list = items.filter((it) => !tags.some((t) => t.toLowerCase() === it.name.toLowerCase()));
      const rows = list.map((it) => ({ label: esc(it.name), meta: esc(it.category || ""), value: it.name }));
      if (q && !exact) rows.push({ label: `Créer « ${esc(q)} »`, meta: "nouvelle", value: q });
      if (!rows.length) { closeOptions(); return; }
      active = Math.min(active, rows.length - 1);
      options.innerHTML = rows.map((r, i) =>
        `<li role="option" data-value="${esc(r.value)}" aria-selected="${i === active}"><span>${r.label}</span><small>${r.meta}</small></li>`).join("");
      options.hidden = false;
      search.setAttribute("aria-expanded", "true");
    };
    const fetchOptions = debounce(async () => {
      const data = await fetch(`${form.dataset.activitiesUrl}?q=${encodeURIComponent(search.value.trim())}`).then((r) => r.json());
      items = data.items || [];
      active = search.value.trim() ? 0 : -1;
      if (document.activeElement === search) renderOptions();
    }, 150);

    search.addEventListener("input", fetchOptions);
    search.addEventListener("focus", fetchOptions);
    search.addEventListener("keydown", (e) => {
      const rows = $$("li", options);
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (options.hidden) { renderOptions(); return; }
        active = (active + (e.key === "ArrowDown" ? 1 : -1) + rows.length) % rows.length;
        rows.forEach((r, i) => r.setAttribute("aria-selected", i === active));
        rows[active]?.scrollIntoView({ block: "nearest" });
      } else if (e.key === "Enter" || e.key === ",") {
        if (!search.value.trim() && active < 0) return;
        e.preventDefault();
        const row = rows[active];
        addTag(row && !options.hidden ? row.dataset.value : search.value);
      } else if (e.key === "Backspace" && !search.value && tags.length) {
        tags.pop(); renderTags();
      } else if (e.key === "Escape") {
        closeOptions();
      }
    });
    options.addEventListener("mousedown", (e) => {
      const li = e.target.closest("li");
      if (li) { e.preventDefault(); addTag(li.dataset.value); }
    });
    search.addEventListener("blur", () => setTimeout(closeOptions, 120));
    tagList.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-remove]");
      if (btn) { tags.splice(Number(btn.dataset.remove), 1); renderTags(); search.focus(); }
    });
    $("#activity-picker").addEventListener("click", (e) => { if (e.target.id === "activity-picker") search.focus(); });
    renderTags();

    // Ne pas soumettre le formulaire par Entrée dans le nom
    nameInput.addEventListener("keydown", (e) => { if (e.key === "Enter") e.preventDefault(); });
  }
})();
