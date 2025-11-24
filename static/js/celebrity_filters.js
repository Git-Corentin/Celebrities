document.addEventListener("DOMContentLoaded", () => {

    function attachPaginationEvents() {
        document.querySelectorAll("#PaginationContainer .page-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();
                refreshCelebrities(btn.dataset.page, true); // Scroll vers le haut lors du changement de page
            });
        });

        const perPageSelect = document.getElementById("per-page-select");
        if (perPageSelect) {
            perPageSelect.replaceWith(perPageSelect.cloneNode(true));
            const newSelect = document.getElementById("per-page-select");
            newSelect.addEventListener("change", () => {
                refreshCelebrities(1, false); // Ne pas scroller lors du changement de nombre de lignes
            });
        }
    }

    function refreshCelebrities(page = 1, scrollToTop = false) {
        const activities = [...document.querySelectorAll(".activity-toggle.selected")].map(btn => btn.dataset.id);
        const perPageSelect = document.getElementById("per-page-select");
        let perPage = perPageSelect ? parseInt(perPageSelect.value) || 50 : 50;
        const sortBy = document.getElementById("sort-select")?.value || "name";

        const params = new URLSearchParams();
        params.append("page", page);
        params.append("per_page", perPage);
        params.append("sort", sortBy);
        activities.forEach(a => params.append("activities[]", a));

        // Sauvegarder la position si on ne scroll pas vers le haut
        const scrollPosition = scrollToTop ? 0 : (window.scrollY || window.pageYOffset);

        fetch(window.location.pathname + "?" + params.toString(), {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(res => res.json())
        .then(data => {
            document.getElementById("CelebListContainer").innerHTML = data.items;
            document.getElementById("PaginationContainer").innerHTML = data.pagination;

            if (scrollToTop) {
                // Scroller vers le début de la liste pour les changements de page
                document.getElementById("CelebListContainer").scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            } else {
                // Garder la position actuelle pour les changements de nombre de lignes
                window.scrollTo(0, scrollPosition);
            }

            attachPaginationEvents();
        });
    }

    // Event delegation pour les boutons toggle
    document.querySelector(".activity-checkbox-wrapper").addEventListener("click", (e) => {
        const btn = e.target.closest(".activity-toggle");
        if (!btn) return;
        btn.classList.toggle("selected");
        refreshCelebrities();
    });

    // Clear / Select All
    document.getElementById("clear-activities").addEventListener("click", () => {
        document.querySelectorAll(".activity-toggle.selected").forEach(btn => btn.classList.remove("selected"));
        refreshCelebrities();
    });

    document.getElementById("select-all-activities").addEventListener("click", () => {
        document.querySelectorAll(".activity-toggle").forEach(btn => btn.classList.add("selected"));
        refreshCelebrities();
    });

    // Filtre catégorie
    document.getElementById("category-filter").addEventListener("change", (e) => {
        const catId = e.target.value;
        document.querySelectorAll(".activity-toggle").forEach(btn => {
            if (catId && btn.dataset.category === catId) {
                btn.classList.add("selected");
            } else {
                btn.classList.remove("selected");
            }
        });
        refreshCelebrities();
    });

    // Initialisation
    attachPaginationEvents();
});