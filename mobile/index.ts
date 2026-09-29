import { registerRootComponent } from 'expo';
import { createElement } from 'react';

import App from './App';
import { Crashed } from './src/Crashed.tsx';

// registerRootComponent calls AppRegistry.registerComponent('main', () => App);
// It also ensures that whether you load the app in Expo Go or in a native build,
// the environment is set up appropriately
registerRootComponent(() => createElement(Crashed, null, createElement(App)));
