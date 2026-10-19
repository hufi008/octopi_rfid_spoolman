(function () {
    function updateRfidSpoolmanStatus() {
        if (typeof OctoPrint === "undefined" || !OctoPrint.simpleApiGet) {
            return;
        }

        OctoPrint.simpleApiGet("rfid_spoolman").done(function (data) {
            var status = data.status || "waiting";
            var labels = {
                waiting: "Bereit",
                recognized: "Erkannt",
                unknown: "Unknown",
                error: "Fehler"
            };
            var colors = {
                waiting: {background: "#e2e3e5", color: "#212529"},
                recognized: {background: "#198754", color: "#ffffff"},
                unknown: {background: "#ffda6a", color: "#212529"},
                error: {background: "#dc3545", color: "#ffffff"}
            };
            var style = colors[status] || colors.waiting;

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

            $("#rfid-spoolman-uid").text(data.uid || "—");
            $("#rfid-spoolman-spool").text(
                data.spool_id === null || data.spool_id === undefined
                    ? (status === "unknown" ? "Unknown" : "—")
                    : "Nr. " + data.spool_id
            );
            $("#rfid-spoolman-message").text(data.message || "");
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
