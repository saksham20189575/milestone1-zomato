(function () {
  const form = document.getElementById("prefs-form");
  const submitBtn = document.getElementById("submit-btn");
  const localitySelect = document.getElementById("locality-select");
  const localitiesHint = document.getElementById("localities-hint");
  const statusEl = document.getElementById("status");
  const summaryEl = document.getElementById("summary");
  const metaEl = document.getElementById("meta");
  const cardsEl = document.getElementById("cards");
  const resultsSection = document.getElementById("results-section");

  function show(el, cls, text) {
    el.textContent = text;
    el.className = "status " + cls;
    el.classList.remove("hidden");
  }

  function hide(el) {
    el.classList.add("hidden");
    el.textContent = "";
  }

  function setBusy(busy) {
    submitBtn.disabled = busy || localitySelect.options.length <= 1;
    resultsSection.setAttribute("aria-busy", busy ? "true" : "false");
  }

  async function loadLocalities() {
    localitiesHint.classList.remove("hidden");
    localitiesHint.textContent = "Loading localities from catalog…";
    try {
      const res = await fetch("/api/v1/localities", { headers: { Accept: "application/json" } });
      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error("Bad JSON from /api/v1/localities");
      }
      if (!res.ok) throw new Error(data.detail || res.statusText);
      const locs = data.localities || [];
      localitySelect.innerHTML = '<option value="">Select a locality</option>';
      locs.forEach(function (name) {
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = name;
        localitySelect.appendChild(opt);
      });
      localitySelect.disabled = locs.length === 0;
      submitBtn.disabled = locs.length === 0;
      localitiesHint.classList.add("hidden");
      if (locs.length === 0) {
        show(statusEl, "error", "No localities found in catalog. Run ingestion first.");
      }
    } catch (err) {
      localitiesHint.textContent = "";
      localitySelect.disabled = true;
      submitBtn.disabled = true;
      show(statusEl, "error", "Could not load localities: " + String(err.message || err));
    }
  }

  function renderResults(data) {
    hide(statusEl);
    summaryEl.textContent = data.summary || "";
    summaryEl.classList.toggle("hidden", !data.summary);

    const m = data.meta || {};
    metaEl.innerHTML = [
      m.shortlist_size != null ? `<div>Shortlist size: <strong>${m.shortlist_size}</strong></div>` : "",
      m.model ? `<div>Model: <code>${escapeHtml(m.model)}</code></div>` : "",
      m.prompt_version ? `<div>Prompt: <code>${escapeHtml(m.prompt_version)}</code></div>` : "",
      m.filter_reason ? `<div>Filter: <code>${escapeHtml(m.filter_reason)}</code></div>` : "",
      `<div>LLM: ${m.used_llm ? "yes" : "no"}${m.llm_parse_failed ? " (parse fallback)" : ""}</div>`,
    ].join("");
    metaEl.classList.remove("hidden");

    cardsEl.innerHTML = "";
    (data.items || []).forEach(function (item) {
      const li = document.createElement("li");
      li.className = "card";
      const cuisines = Array.isArray(item.cuisines) ? item.cuisines.join(", ") : "";
      const rating = item.rating != null ? String(item.rating) : "—";
      li.innerHTML =
        "<header><span class=\"rank\">#" +
        escapeHtml(String(item.rank)) +
        "</span><h3>" +
        escapeHtml(item.name || "Unknown") +
        "</h3></header>" +
        "<p class=\"facts\">" +
        escapeHtml(cuisines) +
        " · ★ " +
        escapeHtml(rating) +
        " · " +
        escapeHtml(item.cost_display || "") +
        "</p>" +
        "<p class=\"explanation\">" +
        escapeHtml(item.explanation || "") +
        "</p>";
      cardsEl.appendChild(li);
    });

    if (!data.items || data.items.length === 0) {
      show(statusEl, "ok", "No restaurant rows returned. Try relaxing cuisine, rating, or budget.");
    }
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function format422(detail) {
    if (!Array.isArray(detail)) return JSON.stringify(detail, null, 2);
    return detail
      .map(function (e) {
        return (e.loc || []).join(".") + ": " + (e.msg || "");
      })
      .join("\n");
  }

  loadLocalities();

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    hide(summaryEl);
    hide(metaEl);
    cardsEl.innerHTML = "";
    show(statusEl, "loading", "Calling the API…");
    setBusy(true);

    const fd = new FormData(form);
    const location = (fd.get("location") || "").toString().trim();
    const budgetMax = parseInt(fd.get("budget_max_inr"), 10);
    const cuisineRaw = (fd.get("cuisine") || "").toString().trim();
    const minRating = parseFloat(fd.get("min_rating"));
    const enableRelax = form.querySelector('[name="enable_rating_relax"]').checked;
    const extrasRaw = (fd.get("extras") || "").toString().trim();

    const body = {
      location: location,
      budget_max_inr: budgetMax,
      min_rating: minRating,
      enable_rating_relax: enableRelax,
    };
    if (cuisineRaw) body.cuisine = cuisineRaw;
    if (extrasRaw) body.extras = extrasRaw;

    try {
      const res = await fetch("/api/v1/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(body),
      });
      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        show(statusEl, "error", "Non-JSON response (" + res.status + "):\n" + text.slice(0, 500));
        setBusy(false);
        return;
      }
      if (!res.ok) {
        const msg =
          res.status === 422 ? format422(data.detail) : data.detail || data.message || JSON.stringify(data);
        show(statusEl, "error", "Error " + res.status + ":\n" + msg);
        setBusy(false);
        return;
      }
      renderResults(data);
    } catch (err) {
      show(statusEl, "error", String(err.message || err));
    }
    setBusy(false);
  });
})();
