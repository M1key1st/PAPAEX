(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {
        var input = document.getElementById("tmdb_q");
        var resultsBox = document.getElementById("tmdb_results");
        if (!input || !resultsBox) return;

        var timer = null;

        input.addEventListener("input", function () {
            clearTimeout(timer);
            var q = input.value.trim();
            if (q.length < 2) {
                resultsBox.style.display = "none";
                return;
            }
            timer = setTimeout(function () { runSearch(q); }, 350);
        });

        function runSearch(q) {
            fetch("/admin/tmdb/search?q=" + encodeURIComponent(q))
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    resultsBox.innerHTML = "";
                    if (!data.enabled) {
                        resultsBox.innerHTML = '<div class="tmdb-result-item">TMDB API kaliti sozlanmagan — maydonlarni qo\'lda to\'ldiring.</div>';
                        resultsBox.style.display = "block";
                        return;
                    }
                    if (!data.results || !data.results.length) {
                        resultsBox.innerHTML = '<div class="tmdb-result-item">Hech narsa topilmadi.</div>';
                        resultsBox.style.display = "block";
                        return;
                    }
                    data.results.forEach(function (item) {
                        var row = document.createElement("div");
                        row.className = "tmdb-result-item";
                        var imgHtml = item.poster ? '<img src="' + item.poster + '" alt="">' : "";
                        row.innerHTML = imgHtml + "<span>" + item.title + (item.year ? " (" + item.year + ")" : "") + "</span>";
                        row.addEventListener("click", function () { importMovie(item.id); });
                        resultsBox.appendChild(row);
                    });
                    resultsBox.style.display = "block";
                });
        }

        function importMovie(tmdbId) {
            resultsBox.innerHTML = '<div class="tmdb-result-item">Yuklanmoqda…</div>';
            fetch("/admin/tmdb/import/" + tmdbId)
                .then(function (r) { return r.json(); })
                .then(function (res) {
                    if (!res.ok) {
                        alert(res.error || "Xatolik yuz berdi.");
                        return;
                    }
                    fillForm(res.data);
                    resultsBox.style.display = "none";
                    input.value = res.data.name;
                });
        }

        function setVal(id, value) {
            var el = document.getElementById(id);
            if (el && value !== null && value !== undefined) el.value = value;
        }

        function fillForm(data) {
            setVal("tmdb_id", data.tmdb_id);
            setVal("imdb_id", data.imdb_id);
            setVal("poster_path", data.poster_path);
            setVal("backdrop_path", data.backdrop_path);
            setVal("poster_local", data.poster_local);
            setVal("backdrop_local", data.backdrop_local);
            setVal("name", data.name);
            setVal("original_name", data.original_name);
            setVal("tagline", data.tagline);
            setVal("summary", data.summary);
            setVal("year", data.year);
            setVal("release_date", data.release_date);
            setVal("runtime", data.runtime);
            setVal("country", data.country);
            setVal("director", data.director);
            setVal("trailer_url", data.trailer_url);

            if (data.genres && data.genres.length) {
                var checkboxes = document.querySelectorAll('#genre-checkboxes input[type="checkbox"]');
                checkboxes.forEach(function (cb) {
                    var label = cb.parentElement.textContent.trim();
                    if (data.genres.indexOf(label) !== -1) cb.checked = true;
                });
            }

            if (data.cast && data.cast.length) {
                var castText = data.cast.map(function (c) {
                    return c.name + " | " + (c.character || "");
                }).join("\n");
                var castEl = document.getElementById("cast_text");
                if (castEl) castEl.value = castText;
            }
        }

        document.addEventListener("click", function (e) {
            if (!resultsBox.contains(e.target) && e.target !== input) {
                resultsBox.style.display = "none";
            }
        });
    });
})();
