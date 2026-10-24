(function () {
    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/>/g, "&gt;").replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function updateStatus() {
        if (typeof OctoPrint === "undefined" || !OctoPrint.simpleApiGet) return;
        OctoPrint.simpleApiGet("rfid_spoolman").done(function (data) {
            var status = data.reader_status || data.status || "starting";
            var labels = {starting: "Startet", online: "Online", error: "Fehler"};
            var colors = {
                starting: {background: "#e2e3e5", color: "#212529"},
                online: {background: "#198754", color: "#ffffff"},
                error: {background: "#dc3545", color: "#ffffff"}
            };
            var style = colors[status] || colors.starting;
            $("#rfid-spoolman-status").text(labels[status] || status).css({
                display: "inline-block", padding: "2px 7px", "border-radius": "4px",
                "font-weight": "bold", "background-color": style.background, color: style.color
            });
            $("#rfid-spoolman-uid").text(data.uid || "—").css({
                display: "inline-block", padding: "2px 5px", "border-radius": "3px",
                "background-color": "#ffffff", color: "#212529"
            });

            var spoolHtml = "";
            if (data.card_status === "recognized" && data.spool) {
                var spool = data.spool;
                var name = [spool.material ? "[" + spool.material + "]" : "", spool.filament_name || ""]
                    .filter(Boolean).join(" ");
                var title = name + (spool.vendor ? " (" + spool.vendor + ")" : "");
                var remainingWeight = Number(spool.remaining_weight);
                var initialWeight = Number(spool.initial_weight);
                var remainingLength = Number(spool.remaining_length);
                spoolHtml = "<p><strong>#" + escapeHtml(String(spool.id)) + " " +
                    escapeHtml(title || "Unbekannte Spule") + "</strong></p>";
                if (Number.isFinite(remainingWeight) && Number.isFinite(initialWeight)) {
                    spoolHtml += "<p><strong>" + remainingWeight.toFixed(1) + " g / " +
                        initialWeight.toFixed(0) + " g</strong></p>";
                }
                if (Number.isFinite(remainingLength)) {
                    spoolHtml += "<p>Restlänge: " + (remainingLength / 1000).toFixed(1) + " m</p>";
                }
            } else if (data.card_status === "unknown") {
                spoolHtml = "<p>Unbekannter Tag – in Spoolman zuordnen.</p>";
            } else if (data.card_status === "error") {
                spoolHtml = "<p>" + escapeHtml(data.message || "Fehler") + "</p>";
            } else {
                spoolHtml = "<p>Warte auf RFID-Tag.</p>";
            }
            $("#rfid-spoolman-spool").html(spoolHtml);

            var hxStatus = data.hx711_status || "starting";
            $("#hx711-status").text(
                hxStatus === "online" ? "Online" : (hxStatus === "error" ? "Fehler" : "Startet")
            );
            $("#hx711-message").text(data.hx711_message || "");
            $("#hx711-raw").text(Number.isFinite(Number(data.hx711_raw)) ? Math.round(Number(data.hx711_raw)) : "—");
            $("#hx711-weight").text(
                data.hx711_calibrated && Number.isFinite(Number(data.hx711_weight_g))
                    ? Number(data.hx711_weight_g).toFixed(1) + " g"
                    : "Nicht kalibriert"
            );
            var offsetText = Number.isFinite(Number(data.hx711_offset)) ? Math.round(Number(data.hx711_offset)) : "—";
            $("#hx711-offset, #hx711-settings-offset").text(offsetText);
            $("#hx711-settings-status").text(
                hxStatus === "online" ? "Online" : (hxStatus === "error" ? "Fehler" : "Startet")
            );
            $("#hx711-settings-raw").text(
                Number.isFinite(Number(data.hx711_raw)) ? Math.round(Number(data.hx711_raw)) : "—"
            );
            $("#hx711-settings-calibration").text(
                data.hx711_calibrated && Number.isFinite(Number(data.hx711_reference_unit))
                    ? "Kalibriert"
                    : "Nicht kalibriert"
            );
            $("#rfid-spoolman-message").text("");
        }).fail(function () {
            $("#rfid-spoolman-status").text("Nicht erreichbar");
            $("#rfid-spoolman-message").text("Status konnte nicht geladen werden.");
        });
    }

    function runScaleCommand(command, payload) {
        OctoPrint.simpleApiCommand("rfid_spoolman", command, payload || {})
            .done(function (data) {
                $("#hx711-settings-message").text(data.message || "Aktion abgeschlossen.");
                updateStatus();
            })
            .fail(function (xhr) {
                var message = "Aktion fehlgeschlagen.";
                if (xhr.responseJSON && xhr.responseJSON.message) message = xhr.responseJSON.message;
                $("#hx711-settings-message").text(message);
            });
    }

    $(function () {
        updateStatus();
        window.setInterval(updateStatus, 2000);
        $(document).on("click", "#hx711-tare", function () {
            runScaleCommand("tare");
        });
        $(document).on("click", "#hx711-calibrate", function () {
            var weight = parseFloat($("#hx711-known-weight").val());
            if (!Number.isFinite(weight) || weight <= 0) {
                $("#hx711-settings-message").text("Bitte das bekannte Gewicht in Gramm eingeben.");
                return;
            }
            runScaleCommand("calibrate", {weight_g: weight});
        });
    });
})();
