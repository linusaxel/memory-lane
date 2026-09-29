// expo-task-manager adds the `fetch` background mode to every app that links
// it. Only geofencing uses the task manager here, which needs `location` alone,
// and App Review rejects a declared mode the app never uses (guideline 2.5.4).
const { withInfoPlist } = require('expo/config-plugins');

module.exports = (config) =>
  withInfoPlist(config, (config) => {
    const modes = config.modResults.UIBackgroundModes ?? [];
    config.modResults.UIBackgroundModes = modes.filter((mode) => mode !== 'fetch');
    return config;
  });
