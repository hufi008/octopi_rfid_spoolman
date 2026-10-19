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

            $("#rfid-spoolman-status")
                .text(labels[status] || status)
                .removeClass("text-success text-warning text-error")
                .addClass(status === "recognized" ? "text-success" :
                    (status === "unknown" ? "text-warning" :
                    (status === "error" ? "text-error" : "")));

            $("#rfid-spoolman-uid").text(data.uid || "—");
            $("#rfid-spoolman-spool").text(
                data.spool_id === null || data.spool_id === undefined
                    ? (status === "unknown" ? "Unknown" : "—")
                    : "Nr. " + data.spool_id
            );
            $("#rfid-spoolman-message").text(data.message || "");
        }).fail(function () {
            $("#rfid-spoolman-status").text("Nicht erreichbar");
            $("#rfid-spoolman-message").text("Status konnte nicht geladen werden.");
        });
    }

    $(function () {
        updateRfidSpoolmanStatus();
        window.setInterval(updateRfidSpoolmanStatus, 2000);
    });
})();
