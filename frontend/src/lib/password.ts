/**
 * A rough, friendly strength hint for the sign-up form (0-4). The server's password policy
 * (Frappe's zxcvbn check plus a minimum length) is what actually decides.
 */
export function passwordScore(pw: string): number {
	if (!pw || pw.length < 8) return 0
	let score = 1
	if (pw.length >= 12) score++
	const kinds = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((r) => r.test(pw)).length
	if (kinds >= 3) score++
	if (pw.length >= 14 && kinds >= 3) score++
	if (/^(.)\1+$/.test(pw) || /^(?:password|12345678|qwerty)/i.test(pw)) score = 1
	return Math.min(score, 4)
}

export const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
