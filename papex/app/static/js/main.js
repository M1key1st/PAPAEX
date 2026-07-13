(function () {
    "use strict";

    function getCsrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") : "";
    }

    function postJSON(url, body) {
        return fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify(body || {}),
        }).then(function (res) {
            return res.json();
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        var actionBar = document.querySelector(".action-bar");
        if (!actionBar) return;

        var titleId = actionBar.getAttribute("data-title-id");

        var voteButtons = actionBar.querySelectorAll(".js-vote");
        voteButtons.forEach(function (btn) {
            btn.addEventListener("click", function () {
                var value = parseInt(btn.getAttribute("data-value"), 10);
                postJSON("/api/vote/" + titleId, { value: value }).then(function (data) {
                    if (!data.ok) return;
                    var likeCount = actionBar.querySelector(".js-like-count");
                    var dislikeCount = actionBar.querySelector(".js-dislike-count");
                    if (likeCount) likeCount.textContent = data.likes;
                    if (dislikeCount) dislikeCount.textContent = data.dislikes;

                    voteButtons.forEach(function (b) { b.classList.remove("active"); });
                    if (data.vote === value) {
                        btn.classList.add("active");
                    }
                });
            });
        });

        var bookmarkBtn = actionBar.querySelector(".js-bookmark");
        if (bookmarkBtn) {
            bookmarkBtn.addEventListener("click", function () {
                postJSON("/api/bookmark/" + titleId).then(function (data) {
                    if (!data.ok) return;
                    if (data.bookmarked) {
                        bookmarkBtn.classList.add("active");
                        bookmarkBtn.textContent = "🔖 Saqlangan";
                    } else {
                        bookmarkBtn.classList.remove("active");
                        bookmarkBtn.textContent = "🔖 Saqlash";
                    }
                });
            });
        }
    });
})();
