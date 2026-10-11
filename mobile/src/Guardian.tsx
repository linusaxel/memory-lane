/** The fir guardian: the mascot, only at the app's edges (docs/10, "The fir
 *  guardian, at the edges"). Decorative, so it says nothing to VoiceOver. */

import { Image, useColorScheme, type ImageStyle, type StyleProp } from 'react-native';

const ART = {
  front: [
    require('../assets/guardian/front-light.png'),
    require('../assets/guardian/front-dark.png'),
  ],
  curious: [
    require('../assets/guardian/curious-light.png'),
    require('../assets/guardian/curious-dark.png'),
  ],
  sleepy: [
    require('../assets/guardian/sleepy-light.png'),
    require('../assets/guardian/sleepy-dark.png'),
  ],
};

type Props = { pose: keyof typeof ART; size: number; place?: StyleProp<ImageStyle> };

export default function Guardian({ pose, size, place }: Props) {
  const dark = useColorScheme() === 'dark' ? 1 : 0;
  return (
    <Image
      source={ART[pose][dark]}
      style={[{ width: size, height: size }, place]}
      resizeMode="contain"
      accessible={false}
    />
  );
}
