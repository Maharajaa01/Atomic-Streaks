/**
 * Sequential ramp for "how much of the day got done": one hue (grape), light -> dark on light
 * surfaces and dark -> light on dark surfaces. "Nothing scheduled" is a neutral, not a step.
 */
export const HEAT_LIGHT = ["#EFEBFF", "#CFC3FF", "#9479F9", "#6140E8", "#41289E"]
export const HEAT_DARK = ["#2A2350", "#41289E", "#6140E8", "#9479F9", "#CFC3FF"]
export const HEAT_NONE = { light: "#EEF0F6", dark: "#1C2537" }

export function heatColor(percent: number | null, dark: boolean): string {
	if (percent === null) return dark ? HEAT_NONE.dark : HEAT_NONE.light
	const ramp = dark ? HEAT_DARK : HEAT_LIGHT
	const i = percent >= 100 ? 4 : percent >= 67 ? 3 : percent >= 34 ? 2 : percent > 0 ? 1 : 0
	return ramp[i]!
}
