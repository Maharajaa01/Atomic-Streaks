/**
 * Render the PWA icons from public/icons/logo.svg.  Run: npm run icons
 * Maskable icons keep the gradient full-bleed and shrink the mark into the central safe zone.
 */
import { readFileSync } from "node:fs"
import { dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"

import sharp from "sharp"

const ICONS = resolve(dirname(fileURLToPath(import.meta.url)), "../public/icons")
const svg = readFileSync(resolve(ICONS, "logo.svg"))
// full-bleed variant: same artwork without rounded corners (the OS applies its own mask)
const square = Buffer.from(svg.toString().replace('rx="15"', 'rx="0"'))
// maskable: full-bleed gradient, artwork shrunk into the central safe zone
const maskable = Buffer.from(
	svg
		.toString()
		.replace('rx="15" fill="url(#t)"/>', 'rx="0" fill="url(#t)"/><g transform="translate(32 32) scale(.78) translate(-32 -32)">')
		.replace("</svg>", "</g></svg>"),
)

async function png(source, size, file, { pad = 0, background } = {}) {
	const inner = Math.round(size * (1 - pad * 2))
	let img = sharp(source, { density: 1024 }).resize(inner, inner)
	if (pad) {
		const buf = await img.png().toBuffer()
		img = sharp({ create: { width: size, height: size, channels: 4, background } }).composite([{ input: buf, gravity: "center" }])
	}
	await img.png().toFile(resolve(ICONS, file))
	console.log("icons:", file)
}

await png(svg, 32, "favicon-32.png")
await png(svg, 192, "icon-192.png")
await png(svg, 512, "icon-512.png")
await png(square, 180, "apple-touch-icon.png")
await png(maskable, 512, "maskable-512.png")
