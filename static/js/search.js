/**
 * Global search UI — dropdown results, keyboard shortcut
 */
const SearchManager = {
  init() {
    const input = document.getElementById("globalSearch");
    const dropdown = document.getElementById("globalSearchDropdown");
    if (!input || !dropdown) return;

    input.addEventListener("focus", () => {
      if (input.value.trim()) {
        dropdown.classList.add("is-open");
      }
    });

    input.addEventListener("input", () => {
      const query = input.value.trim().toLowerCase();
      if (query.length > 0) {
        this.filterResults(query, dropdown);
        dropdown.classList.add("is-open");
      } else {
        dropdown.classList.remove("is-open");
      }
    });

    document.addEventListener("click", (e) => {
      if (!input.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.remove("is-open");
      }
    });

    document.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        input.focus();
      }
      if (e.key === "Escape") {
        dropdown.classList.remove("is-open");
        input.blur();
      }
    });
  },

  async filterResults(query, dropdown) {
    try {
      const res = await fetch(`/api/search/?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      dropdown.innerHTML = "";
      if (!data.results?.length) {
        dropdown.innerHTML = '<div style="padding:1rem;text-align:center;color:var(--color-text-muted);">No results found</div>';
        dropdown.classList.add("is-open");
        return;
      }
      data.results.forEach((item) => {
        const el = document.createElement("a");
        el.href = item.url;
        el.className = "global-search-result";
        el.innerHTML = `<span class="global-search-result-icon"><i data-lucide="${item.icon}"></i></span><span>${item.label}</span>`;
        dropdown.appendChild(el);
      });
      if (window.lucide) lucide.createIcons({ nodes: [dropdown] });
      dropdown.classList.add("is-open");
    } catch (e) {
      this.filterResultsStatic(query, dropdown);
    }
  },

  filterResultsStatic(query, dropdown) {
    const items = dropdown.querySelectorAll(".global-search-result");
    let visible = 0;
    items.forEach((item) => {
      const text = item.textContent.toLowerCase();
      const match = text.includes(query);
      item.style.display = match ? "flex" : "none";
      if (match) visible++;
    });

    let empty = dropdown.querySelector(".global-search-empty");
    if (visible === 0) {
      if (!empty) {
        empty = document.createElement("div");
        empty.className = "global-search-empty";
        empty.style.cssText = "padding: 1rem; text-align: center; color: var(--color-text-muted); font-size: 0.875rem;";
        empty.textContent = "No results found";
        dropdown.appendChild(empty);
      }
      empty.style.display = "block";
    } else if (empty) {
      empty.style.display = "none";
    }
  },
};

window.SearchManager = SearchManager;
