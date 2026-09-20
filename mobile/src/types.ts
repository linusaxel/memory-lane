/** Types more than one screen needs.
 *
 * `Permission` lived in App.tsx and could not be imported, so Settings restated
 * the union in a comment and typed the prop `string` - which compiles a typo
 * into the "off" branch.
 */

/** 'blocked' is the one that cannot be fixed by asking again - only Settings. */
export type Permission = 'unknown' | 'granted' | 'denied' | 'blocked';

/** Separate states, because "nothing here" and "we could not ask" must not look
 *  alike. That identical rendering was the bug this replaced. */
export type Status = 'loading' | 'ready' | 'failed';
