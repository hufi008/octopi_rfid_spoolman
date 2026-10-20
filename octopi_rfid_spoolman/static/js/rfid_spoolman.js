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

            var spoolText = "—";
            if (cardStatus === "recognized" && data.spool_id !== null && data.spool_id !== undefined) {
                spoolText = "Spule " + data.spool_id + " aktiviert";
            } else if (cardStatus === "unknown") {
                spoolText = "in Spoolman eintragen";
            } else if (cardStatus === "error") {
                spoolText = data.message || "Fehler";
            }
            $("#rfid-spoolman-spool").text(spoolText);
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

    $(function () {
        updateRfidSpoolmanStatus();
        window.setInterval(updateRfidSpoolmanStatus, 2000);
    });
})();
