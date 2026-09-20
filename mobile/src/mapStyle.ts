/** How the map gets out of the way.
 *
 * The default map is a competitor, not a backdrop: it draws the Statue of
 * Liberty, a photo of Barclays Center and every restaurant in midtown, all of
 * which are more colourful than a grey padlock. This app has exactly one
 * subject and it is the pins.
 *
 * iOS gets Apple's own answer - `mapType="mutedStandard"` plus
 * `showsPointsOfInterest={false}`. Android has no muted type, so it gets the
 * equivalent as a style array; `customMapStyle` is Google-provider only, which
 * is also why iOS cannot use it.
 */

/** Deliberately short. Every rule here removes something. */
export const MUTED_ANDROID_STYLE = [
  // Someone else's landmarks are not this app's content.
  { featureType: 'poi', stylers: [{ visibility: 'off' }] },
  { featureType: 'transit', stylers: [{ visibility: 'off' }] },
  // Parks stay, drained of colour: they are landmarks you navigate by.
  { featureType: 'poi.park', elementType: 'geometry', stylers: [{ color: '#eef0ee' }] },
  { featureType: 'landscape', elementType: 'geometry', stylers: [{ color: '#f6f6f5' }] },
  { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#e3e8ec' }] },
  { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#ffffff' }] },
  { featureType: 'road', elementType: 'labels.icon', stylers: [{ visibility: 'off' }] },
  { featureType: 'road.highway', elementType: 'geometry', stylers: [{ color: '#eceded' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#9b9ba1' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#ffffff' }] },
];
