/**
 * Atomic Streak design tokens.
 *
 * Palette from the product brief. Each brand hue has a light tint (50/100) for surfaces and
 * a deeper shade (600/700) for text on light backgrounds, so coloured text keeps WCAG AA
 * contrast. "ink" is a cool slate grey for text; "night" is the dark-mode surface family
 * built around the brief's #111827.
 */
/** @type {import('tailwindcss').Config} */
export default {
	darkMode: "class",
	content: ["./index.html", "./src/**/*.{vue,ts}"],
	theme: {
		extend: {
			colors: {
				grape: {
					50: "#F3F0FF", 100: "#E6E0FF", 200: "#CFC3FF", 300: "#B19EFC", 400: "#9479F9",
					500: "#7657F6", 600: "#6140E8", 700: "#5131C7", 800: "#41289E", 900: "#2F1D73",
				},
				sky: { 50: "#EEF4FF", 100: "#DCE8FF", 400: "#73A6FF", 500: "#4D8DFF", 600: "#2F6FE6", 700: "#2357BA" },
				mint: { 50: "#E8F9F1", 100: "#C9F1DE", 400: "#4FD39A", 500: "#26C281", 600: "#1A9E68", 700: "#147A51" },
				tangerine: { 50: "#FFF4E8", 100: "#FFE4C7", 400: "#FFB46E", 500: "#FF9F43", 600: "#E57F1C", 700: "#B85F0B" },
				blush: { 50: "#FEEFF5", 100: "#FDD8E6", 400: "#F88DB5", 500: "#F56FA1", 600: "#DE4C83", 700: "#B33366" },
				sun: { 50: "#FFF9E6", 100: "#FFEFBF", 400: "#FFDB85", 500: "#FFD166", 600: "#E5B23A", 700: "#A87D12" },
				ink: {
					50: "#F7F8FC", 100: "#EEF0F6", 200: "#E1E4EE", 300: "#C8CDDB", 400: "#9AA1B5",
					500: "#6B7389", 600: "#4E566B", 700: "#363D50", 800: "#232938", 900: "#141826",
				},
				night: { 950: "#0B1020", 900: "#111827", 850: "#161E2E", 800: "#1C2537", 700: "#273249", 600: "#36425C" },
			},
			fontFamily: {
				display: ['"Bricolage Grotesque Variable"', '"Plus Jakarta Sans Variable"', "system-ui", "sans-serif"],
				sans: ['"Plus Jakarta Sans Variable"', "-apple-system", "system-ui", '"Segoe UI"', "Roboto", "sans-serif"],
			},
			fontSize: {
				"2xs": ["0.6875rem", { lineHeight: "1rem" }],
			},
			borderRadius: { "4xl": "2rem" },
			boxShadow: {
				soft: "0 1px 2px rgba(20,24,38,.04), 0 4px 16px -4px rgba(20,24,38,.08)",
				lift: "0 18px 40px -12px rgba(81,49,199,.35)",
				sheet: "0 -12px 40px -16px rgba(20,24,38,.25)",
			},
			keyframes: {
				"fade-up": { from: { opacity: "0", transform: "translateY(8px)" }, to: { opacity: "1", transform: "none" } },
				"cell-in": {
					"0%": { opacity: "0", transform: "scale(.4)" },
					"70%": { opacity: "1", transform: "scale(1.12)" },
					"100%": { opacity: "1", transform: "scale(1)" },
				},
				float: { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-6px)" } },
				shake: { "0%,100%": { transform: "none" }, "25%": { transform: "translateX(-6px)" }, "75%": { transform: "translateX(6px)" } },
				pop: { "0%": { transform: "scale(1)" }, "40%": { transform: "scale(1.22)" }, "100%": { transform: "scale(1)" } },
				burst: { "0%": { opacity: "1", transform: "translate(0,0) scale(1)" }, "100%": { opacity: "0", transform: "translate(var(--bx),var(--by)) scale(.4)" } },
			},
			animation: {
				"fade-up": "fade-up .35s ease-out both",
				"cell-in": "cell-in .45s cubic-bezier(.2,.9,.3,1.3) both",
				float: "float 5s ease-in-out infinite",
				shake: "shake .3s ease-in-out",
				pop: "pop .35s cubic-bezier(.2,.9,.3,1.4)",
				burst: "burst .6s ease-out forwards",
			},
		},
	},
	plugins: [],
}
