import { Appearance } from 'react-native';
import * as WebBrowser from 'expo-web-browser';

/** A link opens in a sheet over the app, never out of it: Done brings the
 *  walker back to the map (UI.md, "A link that can fail"). Rejects when
 *  nothing can show it, so a caller can say so. */
export function openLink(url: string): Promise<unknown> {
  return WebBrowser.openBrowserAsync(url, {
    presentationStyle: WebBrowser.WebBrowserPresentationStyle.PAGE_SHEET,
    // controlsColor takes a plain string, so pick gold's half by hand.
    controlsColor: Appearance.getColorScheme() === 'dark' ? '#F2703F' : '#A8350F',
    dismissButtonStyle: 'close',
  });
}
