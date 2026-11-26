/**
 * Turn the Vite build into the Frappe website page + root-scoped service worker.
 *
 * Run after `vite build`:
 *   - www/atomic_streak_app.html : built index.html with this session's CSRF token and sign-in
 *                                  state injected (Frappe renders it as Jinja)
 *   - www/atomic_streak_sw.js    : sw-template.js stamped with a fresh CACHE_VERSION and the
 *                                  list of built assets to precache
 *   - manifest.json and icon links get ?v=<content hash>, because nginx serves /assets with a
 *     one-year max-age and these files keep fixed names.
 */
import { createHash } from "node:crypto"
import { mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs"
import { dirname, join, relative, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const HERE = dirname(fileURLToPath(import.meta.url))
const FRONTEND = resolve(HERE, "..")
const APP = resolve(FRONTEND, "../atomic_streak")
const OUT = resolve(APP, "public/frontend")
const BASE = "/assets/atomic_streak/frontend/"

function write(target, contents) {
	mkdirSync(dirname(target), { recursive: true })
	writeFileSync(target, contents)
	console.log(`make-page: wrote ${relative(resolve(APP, ".."), target)}`)
}

// ----------------------------------------------------------- cache busting
const hashOf = (path) => createHash("sha1").update(readFileSync(join(OUT, path))).digest("hex").slice(0, 10)
const bust = (url) => {
	const clean = url.split("?")[0]
	return clean.startsWith(BASE) ? `${clean}?v=${hashOf(clean.slice(BASE.length))}` : url
}

const manifestFile = join(OUT, "manifest.json")
const manifest = JSON.parse(readFileSync(manifestFile, "utf-8"))
for (const icon of manifest.icons ?? []) icon.src = bust(icon.src)
writeFileSync(manifestFile, JSON.stringify(manifest, null, 2) + "\n")

// ---------------------------------------------------------------- app shell
const html = readFileSync(join(OUT, "index.html"), "utf-8").replace(
	new RegExp(`href="(${BASE}(?:manifest\\.json|icons/[^"?]+))"`, "g"),
	(_, url) => `href="${bust(url)}"`,
)
if (!html.includes("</head>")) {
	console.error("make-page: built index.html has no </head>")
	process.exit(1)
}
const page = html.replace(
	"</head>",
	'    <script>window.csrf_token = "{{ csrf_token }}"; window.atomic_guest = {{ is_guest or 0 }};</script>\n  </head>',
)
write(resolve(APP, "www/atomic_streak_app.html"), page)

// ---------------------------------------------------------- service worker
function walk(dir) {
	return readdirSync(dir).flatMap((name) => {
		const p = join(dir, name)
		return statSync(p).isDirectory() ? walk(p) : [p]
	})
}
const precache = walk(OUT)
	.map((p) => relative(OUT, p).split("\\").join("/"))
	.filter((p) => p !== "index.html" && !p.startsWith(".vite/"))
	// fonts: only the Latin subsets are worth downloading up front; others load on demand
	.filter((p) => !/\.(woff2?|ttf)$/.test(p) || /-latin-wght-normal/.test(p))
	.map((p) => BASE + p)
	.sort()

const sw = readFileSync(resolve(FRONTEND, "sw-template.js"), "utf-8")
	.replace("__CACHE_VERSION__", String(Date.now()))
	.replace("__PRECACHE__", JSON.stringify(precache, null, "\t"))
write(resolve(APP, "www/atomic_streak_sw.js"), sw)
console.log(`make-page: ${precache.length} files precached`)
