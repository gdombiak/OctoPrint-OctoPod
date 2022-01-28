/*
 * View model for OctoPrint-Printoid
 *
 * Author: Anthony Stéphan (original author: Gaston Dombiak)
 * License: Apache-2.0
 */
$(function() {
    function PrintoidViewModel(parameters) {
        var self = this;

        // assign the injected parameters, e.g.:
        self.settingsViewModel = parameters[0];

        self.testActive = ko.observable(false);
        self.testResult = ko.observable(false);
        self.testSuccessful = ko.observable(false);
        self.testMessage = ko.observable();

        self.testNotification  = function() {
            self.testActive(true);
            self.testResult(false);
            self.testSuccessful(false);
            self.testMessage("");

            var serverURL = $('#server_url').val();
            var cameraSnapshotURL = $('#camera_snapshot_url').val();
            var webcamFlipH = $('#printoid-webcamFlipH').prop("checked");
            var webcamFlipV = $('#printoid-webcamFlipV').prop("checked");
            var webcamRotate90 = $('#printoid-webcamRotate90').prop("checked");

            var payload = {
                command: "test",
                server_url: serverURL,
                camera_snapshot_url: cameraSnapshotURL,
                camera_flip_h: webcamFlipH,
                camera_flip_v: webcamFlipV,
                camera_rotate90: webcamRotate90
            };

            $.ajax({
                url: API_BASEURL + "plugin/printoid",
                type: "POST",
                dataType: "json",
                data: JSON.stringify(payload),
                contentType: "application/json; charset=UTF-8",
                success: function(response) {
                    self.testResult(true);
                    self.testSuccessful(response.code >= 200 && response.code < 300);

                    if (response.code == -1) {
                        self.testMessage("Please complete 'Notification Server URL'");
                    } else if (response.code == -2) {
                        self.testMessage("No Android devices registered yet. Open the Printoid application on your Android device and ensure the app is connected to your OctoPrint server, then retry.");
                    } else if (response.code == 404) {
                        self.testMessage("404 - Notification server URL not found, please contact the developer");
                    } else if (response.code == 500) {
                        self.testMessage("500 - Target server had an error, please contact the developer");
                    } else if (response.code == -500) {
                        self.testMessage("There was an error sending message. Please check the OctoPrint logs and contact the developer.");
                    } else {
                        self.testMessage(undefined);
                    }
                },
                complete: function() {
                    self.testActive(false);
                }
            });
        };

        self.removeDevice = function(token) {
            self.settings.plugins.printoid.tokens.remove(token);
        };

        self.onBeforeBinding = function() {
            self.settings = self.settingsViewModel.settings;
        };
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: PrintoidViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ "settingsViewModel" ],
        // Elements to bind to, e.g. #settings_plugin_printoid, #tab_plugin_printoid, ...
        elements: [ "#settings_plugin_printoid" ]
    });
});
