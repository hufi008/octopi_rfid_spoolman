(function () {
    function updateRfidSpoolmanStatus() {
        if (typeof OctoPrint === "undefined" || !OctoPrint.simpleApiGet) {
            return;
        }

        OctoPrint.simpleApiGet("rfid_spoolman").done(function (data) {
            var status = data.reader_status || data.status || "starting";
            var cardStatus = data.card_status || "waiting";
            var labels = {
                starting: "Startet",
                online: "Online",
                error: "Fehler"
            };
            var colors = {
                starting: {background: "#e2e3e5", color: "#212529"},
                online: {background: "#198754", color: "#ffffff"},
                error: {background: "#dc3545", color: "#ffffff"}
            };
            var style = colors[status] || colors.starting;

            $("#rfid-spoolman-status")
                .text(labels[status] || status)
                .css({
                    display: "inline-block",
                    padding: "2px 7px",
                    "border-radius": "4px",
                    "font-weight": "bold",
                    "background-color": style.background,
                    color: style.color
                });

            $("#rfid-spoolman-uid")
                .text(data.uid || "—")
                .css({
                    display: "inline-block",
                    padding: "2px 5px",
                    "border-radius": "3px",
                    "background-color": "#ffffff",
                    color: "#212529"
                });

            var spoolHtml = "";
            if (cardStatus === "recognized" && data.spool) {
                var spool = data.spool;
                var name = [spool.material ? "[" + spool.material + "]" : "", spool.filament_name || ""]
                    .filter(Boolean).join(" ");
                var title = name + (spool.vendor ? " (" + spool.vendor + ")" : "");
                var remainingWeight = Number(spool.remaining_weight);
                var initialWeight = Number(spool.initial_weight);
                var remainingLength = Number(spool.remaining_length);

                spoolHtml = "<p><strong>" + escapeHtml(title || ("Spule " + spool.id)) + "</strong></p>";
                if (Number.isFinite(remainingWeight) && Number.isFinite(initialWeight)) {
                    spoolHtml += "<p><strong>" + remainingWeight.toFixed(1) + " g / " +
                        initialWeight.toFixed(0) + " g</strong></p>";
                }
                if (Number.isFinite(remainingLength)) {
                    spoolHtml += "<p>Restlänge: " + (remainingLength / 1000).toFixed(1) + " m</p>";
                }
                spoolHtml += "<small>Spule " + escapeHtml(String(spool.id)) + " aktiviert</small>";
            } else if (cardStatus === "unknown") {
                spoolHtml = "<p>Unbekannter Tag – in Spoolman zuordnen.</p>";
            } else if (cardStatus === "error") {
                spoolHtml = "<p>" + escapeHtml(data.message || "Fehler") + "</p>";
            } else {
                spoolHtml = "<p>Warte auf RFID-Tag.</p>";
            }
            $("#rfid-spoolman-spool").html(spoolHtml);
            $("#rfid-spoolman-message").text("");
        }).fail(function () {
            $("#rfid-spoolman-status")
                .text("Nicht erreichbar")
                .css({
                    display: "inline-block",
                    padding: "2px 7px",
                    "border-radius": "4px",
                    "font-weight": "bold",
                    "background-color": "#dc3545",
                    color: "#ffffff"
                });
            $("#rfid-spoolman-message").text("Status konnte nicht geladen werden.");
        });
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    $(function () {
        updateRfidSpoolmanStatus();
        window.setInterval(updateRfidSpoolmanStatus, 2000);
    });
})();
