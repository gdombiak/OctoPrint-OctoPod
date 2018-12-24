/*
 * View model for OctoPrint-OctoPod
 *
 * Author: Gaston Dombiak
 * License: Apache-2.0
 */
$(function() {
    function OctopodViewModel(parameters) {
        var self = this;

        // assign the injected parameters, e.g.:
//         self.settings = parameters[0];

        // TODO: Implement your plugin's view model here.
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: OctopodViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ "settingsViewModel" ],
        // Elements to bind to, e.g. #settings_plugin_octopod, #tab_plugin_octopod, ...
        elements: [ /* ... */ ]
    });
});
