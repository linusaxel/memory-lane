/** Types more than one screen needs.
 *
 * `Permission` lived in App.tsx and could not be imported, so Settings restated
 * the union in a comment and typed the prop `string` - which compiles a typo
 * into the "off" branch.
 */

/** 'blocked' is the one that cannot be fixed by asking again - only Settings. */
export type Permission = 'unknown' | 'granted' | 'denied' | 'blocked';
