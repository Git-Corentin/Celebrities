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

    const updateBtn = document.getElementById("update-all-button");
    const updateUrl = updateBtn.dataset.updateUrl;
    const progressContainer = document.getElementById("update-progress");
    const progressCount = document.getElementById("progress-count");
    const progressTotal = document.getElementById("progress-total");
    const progressBarFill = document.getElementById("progress-bar-fill");

    function getCsrf() {
    const name = "csrftoken";
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith(name + "=")) {
            return decodeURIComponent(cookie.substring(name.length + 1));
        }
    }
    return null;
}

    if (updateBtn) {
        updateBtn.addEventListener("click", async () => {
            // Récupérer les IDs des célébrités actuellement visibles :
            // on prend les tr qui ont l'attribut data-id
            const ids = await fetch("/celebs/api/all-celeb-ids/")
                .then(r => r.json())
                .then(data => data.ids);

            if (ids.length === 0) {
                alert("Aucune célébrité à mettre à jour !");
                return;
            }

            // UI
            updateBtn.disabled = true;
            progressContainer.style.display = "block";

            progressTotal.textContent = ids.length;
            progressCount.textContent = 0;
            progressBarFill.style.width = "0%";

            const csrf = getCsrf();
            if (!csrf) {
                console.warn("CSRF token absent — la mise à jour risque d'échouer.");
            }

            for (let i = 0; i < ids.length; i++) {
                const id = ids[i];

                try {
                    const resp = await fetch(updateUrl, {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": csrf || "",
                            "X-Requested-With": "XMLHttpRequest",
                            "Content-Type": "application/x-www-form-urlencoded"
                        },
                        body: new URLSearchParams({ celeb_id: id }).toString()
                    });

                    if (!resp.ok) {
                        console.error("Erreur HTTP lors de la mise à jour de", id, resp.status);
                    } else {
                        const json = await resp.json();
                        // optionnel : mettre à jour la valeur affichée dans la colonne Popularité
                        if (json && json.success && json.new_score !== undefined) {
                            // trouver la cellule de popularité dans la même ligne (rowspan rows complicate things)
                            // on met à jour la première cellule trouvée pour cette célébrité
                            const row = document.querySelector(`tr[data-id="${id}"]`);
                            if (row) {
                                // la cellule popularity est la 3e colonne (index 2) dans ton template avec rowspan
                                const popCell = row.querySelectorAll("td")[2]; // prudence : structure dépendante du template
                                if (popCell) popCell.textContent = json.new_score;
                            }
                        }
                    }
                } catch (err) {
                    console.error("Erreur fetch pour", id, err);
                }

                // Mise à jour UI
                progressCount.textContent = i + 1;
                progressBarFill.style.width = ((i + 1) / ids.length * 100) + "%";
            }

            updateBtn.disabled = false;
            // tu peux cacher le progressContainer après un court délai si tu veux
            setTimeout(() => { progressContainer.style.display = "none"; }, 800);
        });
    }

    // Initialisation
    attachPaginationEvents();
});