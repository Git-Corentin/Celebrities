document.addEventListener("DOMContentLoaded", () => {

    // Vérifier si on est sur la page celebrity_list
    const isCelebrityList = document.getElementById("CelebListContainer") !== null;

    // Variable pour suivre si une mise à jour est en cours
    let updateInProgress = false;

    // Fonction pour sauvegarder l'état actuel
    function saveListState() {
        if (!isCelebrityList) return;

        const state = {
            page: getCurrentPage(),
            perPage: document.getElementById("per-page-select")?.value || 50,
            sortBy: currentSort, // Sauvegarder directement currentSort
            activities: [...document.querySelectorAll(".activity-toggle.selected")].map(btn => btn.dataset.id),
            category: document.getElementById("category-filter")?.value || "",
            scrollPosition: window.scrollY || window.pageYOffset,
            timestamp: Date.now()
        };
        sessionStorage.setItem('celebrityListState', JSON.stringify(state));
    }

    // Fonction pour obtenir la page courante
    function getCurrentPage() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('page') || 1;
    }

    // Fonction pour obtenir le tri courant
    function getCurrentSort() {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('sort') || 'name';
    }

    // Variable pour suivre le tri actuel
    let currentSort = getCurrentSort();

    // Fonction pour restaurer l'état sauvegardé
    function restoreListState() {
        const savedState = sessionStorage.getItem('celebrityListState');
        if (!savedState) return false;

        const state = JSON.parse(savedState);

        // Vérifier que l'état n'est pas trop ancien (plus de 1 heure)
        if (Date.now() - state.timestamp > 3600000) {
            sessionStorage.removeItem('celebrityListState');
            return false;
        }

        // Masquer TOUT le contenu pendant la restauration pour éviter le flash
        const container = document.getElementById("CelebListContainer");
        const pagination = document.getElementById("PaginationContainer");
        const toggleFiltersBtn = document.getElementById("toggle-filters");
        const updateBtn = document.getElementById("update-all-button");
        const filtersForm = document.getElementById("filters-form");

        if (container) container.style.opacity = '0';
        if (pagination) pagination.style.opacity = '0';
        if (toggleFiltersBtn) toggleFiltersBtn.style.opacity = '0';
        if (updateBtn) updateBtn.style.opacity = '0';
        if (filtersForm) filtersForm.style.opacity = '0';

        // Restaurer le tri
        if (state.sortBy) {
            currentSort = state.sortBy;
        }

        // Restaurer le nombre de lignes
        const perPageSelect = document.getElementById("per-page-select");
        if (perPageSelect && state.perPage) {
            perPageSelect.value = state.perPage;
        }

        // Restaurer la catégorie
        const categoryFilter = document.getElementById("category-filter");
        if (categoryFilter && state.category) {
            categoryFilter.value = state.category;
        }

        // Restaurer les activités sélectionnées
        if (state.activities && state.activities.length > 0) {
            document.querySelectorAll(".activity-toggle").forEach(btn => {
                if (state.activities.includes(btn.dataset.id)) {
                    btn.classList.add("selected");
                }
            });
        }

        // Restaurer la page et rafraîchir
        refreshCelebrities(state.page, false, () => {
            // Réafficher TOUT le contenu
            if (container) container.style.opacity = '1';
            if (pagination) pagination.style.opacity = '1';
            if (toggleFiltersBtn) toggleFiltersBtn.style.opacity = '1';
            if (updateBtn) updateBtn.style.opacity = '1';
            if (filtersForm) filtersForm.style.opacity = '1';

            // Mettre à jour l'apparence des liens de tri
            updateSortIndicators();

            // Restaurer la position de scroll après le chargement
            setTimeout(() => {
                window.scrollTo({
                    top: state.scrollPosition,
                    behavior: 'instant'
                });
            }, 50);
        });

        return true;
    }

    // Fonction pour mettre à jour les indicateurs de tri
    function updateSortIndicators() {
        document.querySelectorAll(".sort-link").forEach(link => {
            link.classList.remove("sort-asc", "sort-desc");

            const sortField = link.dataset.sort;
            if (currentSort === sortField) {
                link.classList.add("sort-asc");
            } else if (currentSort === `-${sortField}`) {
                link.classList.add("sort-desc");
            }
        });
    }

    function attachPaginationEvents() {
        document.querySelectorAll("#PaginationContainer .page-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.preventDefault();

                // Vérifier si une mise à jour est en cours
                if (updateInProgress) {
                    if (!confirm("Une mise à jour des popularités est en cours. Si vous changez de page, elle sera interrompue. Continuer ?")) {
                        return;
                    }
                }

                refreshCelebrities(btn.dataset.page, true);
            });
        });

        const perPageSelect = document.getElementById("per-page-select");
        if (perPageSelect) {
            perPageSelect.replaceWith(perPageSelect.cloneNode(true));
            const newSelect = document.getElementById("per-page-select");
            newSelect.addEventListener("change", () => {
                // Vérifier si une mise à jour est en cours
                if (updateInProgress) {
                    if (!confirm("Une mise à jour des popularités est en cours. Si vous continuez, elle sera interrompue. Continuer ?")) {
                        return;
                    }
                }

                refreshCelebrities(1, false);
            });
        }

        // Attacher les événements de tri
        document.querySelectorAll(".sort-link").forEach(link => {
            link.addEventListener("click", (e) => {
                e.preventDefault();

                if (updateInProgress) {
                    alert("Veuillez attendre la fin de la mise à jour des popularités.");
                    return;
                }

                const newSort = link.dataset.sort;

                // Si on clique sur le même critère, inverser l'ordre
                if (currentSort === newSort) {
                    currentSort = `-${newSort}`;
                } else if (currentSort === `-${newSort}`) {
                    currentSort = newSort;
                } else {
                    // Premier clic : ordre par défaut selon le champ
                    if (newSort === 'popularity_score') {
                        // Pour la popularité, commencer par décroissant
                        currentSort = `-${newSort}`;
                    } else {
                        // Pour les autres (nom, activités), commencer par croissant
                        currentSort = newSort;
                    }
                }

                // Mettre à jour l'apparence des liens
                updateSortIndicators();

                refreshCelebrities(1, false);
            });
        });

        // Mettre à jour les indicateurs de tri à chaque attachement
        updateSortIndicators();

        // Sauvegarder l'état avant de quitter la page sur tous les liens
        document.querySelectorAll("a:not(.page-btn):not(.sort-link)").forEach(link => {
            // Ne pas attacher si c'est un lien externe ou avec target="_blank"
            if (link.hostname === window.location.hostname && !link.target) {
                link.addEventListener("click", (e) => {
                    // Vérifier si une mise à jour est en cours
                    if (updateInProgress) {
                        if (!confirm("Une mise à jour des popularités est en cours. Si vous quittez la page, elle sera interrompue. Continuer ?")) {
                            e.preventDefault();
                            return;
                        }
                    }

                    saveListState();
                });
            }
        });
    }

    function refreshCelebrities(page = 1, scrollToTop = false, callback = null) {
        const activities = [...document.querySelectorAll(".activity-toggle.selected")].map(btn => btn.dataset.id);
        const perPageSelect = document.getElementById("per-page-select");
        let perPage = perPageSelect ? parseInt(perPageSelect.value) || 50 : 50;

        const params = new URLSearchParams();
        params.append("page", page);
        params.append("per_page", perPage);
        params.append("sort", currentSort);
        activities.forEach(a => params.append("activities[]", a));

        const scrollPosition = scrollToTop ? 0 : (window.scrollY || window.pageYOffset);

        fetch(window.location.pathname + "?" + params.toString(), {
            headers: { "X-Requested-With": "XMLHttpRequest" }
        })
        .then(res => res.json())
        .then(data => {
            document.getElementById("CelebListContainer").innerHTML = data.items;
            document.getElementById("PaginationContainer").innerHTML = data.pagination;

            if (scrollToTop) {
                document.getElementById("CelebListContainer").scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            } else {
                window.scrollTo(0, scrollPosition);
            }

            attachPaginationEvents();

            // Sauvegarder l'état après chaque changement
            if (isCelebrityList) {
                saveListState();
            }

            // Appeler le callback si fourni
            if (callback) callback();
        });
    }

    // Sauvegarder l'état quand on scroll (avec debounce)
    let scrollTimeout;
    if (isCelebrityList) {
        window.addEventListener("scroll", () => {
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                saveListState();
            }, 200);
        });
    }

    // Event delegation pour les boutons toggle
    if (isCelebrityList) {
        document.querySelector(".activity-checkbox-wrapper").addEventListener("click", (e) => {
            const btn = e.target.closest(".activity-toggle");
            if (!btn) return;

            // Vérifier si une mise à jour est en cours
            if (updateInProgress) {
                alert("Veuillez attendre la fin de la mise à jour des popularités.");
                return;
            }

            btn.classList.toggle("selected");
            refreshCelebrities();
        });

        // Clear / Select All
        document.getElementById("clear-activities").addEventListener("click", () => {
            if (updateInProgress) {
                alert("Veuillez attendre la fin de la mise à jour des popularités.");
                return;
            }

            document.querySelectorAll(".activity-toggle.selected").forEach(btn => btn.classList.remove("selected"));
            refreshCelebrities();
        });

        document.getElementById("select-all-activities").addEventListener("click", () => {
            if (updateInProgress) {
                alert("Veuillez attendre la fin de la mise à jour des popularités.");
                return;
            }

            document.querySelectorAll(".activity-toggle").forEach(btn => btn.classList.add("selected"));
            refreshCelebrities();
        });

        // Filtre catégorie
        document.getElementById("category-filter").addEventListener("change", (e) => {
            if (updateInProgress) {
                alert("Veuillez attendre la fin de la mise à jour des popularités.");
                e.target.value = "";
                return;
            }

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
    }

    const updateBtn = document.getElementById("update-all-button");
    const updateUrl = updateBtn?.dataset.updateUrl;
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
            if (updateInProgress) {
                alert("Une mise à jour est déjà en cours.");
                return;
            }

            const ids = await fetch("/celebs/api/all-celeb-ids/")
                .then(r => r.json())
                .then(data => data.ids);

            if (ids.length === 0) {
                alert("Aucune célébrité à mettre à jour !");
                return;
            }

            updateInProgress = true;
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
                        if (json && json.success && json.new_score !== undefined) {
                            const row = document.querySelector(`tr[data-id="${id}"]`);
                            if (row) {
                                const popCell = row.querySelectorAll("td")[2];
                                if (popCell) popCell.textContent = json.new_score;
                            }
                        }
                    }
                } catch (err) {
                    console.error("Erreur fetch pour", id, err);
                }

                progressCount.textContent = i + 1;
                progressBarFill.style.width = ((i + 1) / ids.length * 100) + "%";
            }

            updateInProgress = false;
            updateBtn.disabled = false;
            setTimeout(() => { progressContainer.style.display = "none"; }, 800);
        });
    }

    // Avertir l'utilisateur s'il essaie de quitter pendant une mise à jour
    window.addEventListener('beforeunload', (e) => {
        if (updateInProgress) {
            e.preventDefault();
            e.returnValue = 'Une mise à jour des popularités est en cours. Si vous quittez, elle sera interrompue.';
            return e.returnValue;
        }
    });

    // Gérer le bouton "Retour" du navigateur
    window.addEventListener('pageshow', (event) => {
        if (event.persisted || (performance.getEntriesByType("navigation")[0]?.type === 'back_forward')) {
            // L'utilisateur est revenu via le bouton retour
            if (isCelebrityList) {
                const hasState = sessionStorage.getItem('celebrityListState');
                if (hasState) {
                    restoreListState();
                }
            }
        }
    });

    // Initialisation - TOUJOURS vérifier s'il y a un état à restaurer
    if (isCelebrityList) {
        const hasState = sessionStorage.getItem('celebrityListState');

        if (hasState) {
            // Essayer de restaurer l'état
            const restored = restoreListState();
            if (!restored) {
                // Si la restauration échoue, initialisation normale
                attachPaginationEvents();
                saveListState();
            }
        } else {
            // Pas d'état sauvegardé, initialisation normale
            attachPaginationEvents();
            saveListState();
        }
    }
});