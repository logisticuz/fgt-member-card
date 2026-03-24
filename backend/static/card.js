const CARD_COOKIE = "fgc_card_id";
const CARD_URL_BASE = "https://membercard.fgctrollhattan.se/";

document.addEventListener("DOMContentLoaded", () => {
    const path = window.location.pathname.replace(/^\/+|\/+$/g, "");
    const params = new URLSearchParams(window.location.search);
    const cardId = path || params.get("id");

    // If we have a card ID in the URL, show it
    if (cardId) {
        loadCard(cardId);
        return;
    }

    // Check cookie for saved card
    const savedCard = getCookie(CARD_COOKIE);
    if (savedCard) {
        loadCard(savedCard);
        return;
    }

    // No card — show landing with personnummer form
    showLanding();
});

// --- Pages ---

function showLanding() {
    document.getElementById("landing").classList.remove("hidden");
    setupVerifyForm();
}

function showError() {
    document.getElementById("error").classList.remove("hidden");
}

function showCard(data, cardId) {
    document.getElementById("member-name").textContent = data.name;
    document.getElementById("card-id").textContent = cardId;

    // Player stats
    const statsEl = document.getElementById("player-stats");
    if (data.total_events > 0 || data.favorite_game) {
        statsEl.classList.remove("hidden");
        if (data.total_events > 0) {
            document.getElementById("stat-events").textContent = data.total_events + " events";
        }
        if (data.favorite_game) {
            document.getElementById("stat-game").textContent = data.favorite_game;
        }
    }

    // QR code
    new QRCode(document.getElementById("qr-code"), {
        text: CARD_URL_BASE + cardId,
        width: 200,
        height: 200,
        colorDark: "#000000",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.M,
    });

    // Save to cookie so they don't need to verify again
    setCookie(CARD_COOKIE, cardId, 365);

    document.getElementById("card-page").classList.remove("hidden");
}

// --- API calls ---

async function loadCard(cardId) {
    try {
        const res = await fetch("/api/card/" + cardId);
        if (!res.ok) {
            // Invalid card — clear cookie and show error
            deleteCookie(CARD_COOKIE);
            showError();
            return;
        }

        const data = await res.json();
        showCard(data, cardId);
    } catch (err) {
        console.error("Fel vid laddning:", err);
        showError();
    }
}

// --- Verify form ---

function setupVerifyForm() {
    const form = document.getElementById("verify-form");
    const btn = document.getElementById("verify-btn");
    const errorEl = document.getElementById("verify-error");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        errorEl.classList.add("hidden");

        const tag = document.getElementById("tag").value.trim();
        const pnr = document.getElementById("personnummer").value.trim();
        if (!tag || !pnr) return;

        btn.disabled = true;
        btn.textContent = "Verifierar...";

        try {
            const res = await fetch("/api/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ personnummer: pnr, tag: tag }),
            });

            const data = await res.json();

            if (!data.ok) {
                errorEl.textContent = data.error || "Något gick fel";
                errorEl.classList.remove("hidden");
                btn.disabled = false;
                btn.textContent = "Hämta mitt kort";
                return;
            }

            // Success — redirect to card
            window.location.href = "/" + data.card_id;
        } catch (err) {
            errorEl.textContent = "Kunde inte ansluta. Försök igen.";
            errorEl.classList.remove("hidden");
            btn.disabled = false;
            btn.textContent = "Hämta mitt kort";
        }
    });
}

// --- Cookie helpers ---

function setCookie(name, value, days) {
    const d = new Date();
    d.setTime(d.getTime() + days * 24 * 60 * 60 * 1000);
    document.cookie = name + "=" + value + ";expires=" + d.toUTCString() + ";path=/;SameSite=Lax";
}

function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? match[2] : null;
}

function deleteCookie(name) {
    document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;SameSite=Lax";
}
