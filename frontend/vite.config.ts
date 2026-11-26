import { fileURLToPath, URL } from "node:url"

import vue from "@vitejs/plugin-vue"
import { defineConfig } from "vite"

const APP = "atomic_streak"
// dns_multitenant bench: the dev proxy must send the site name as Host
const SITE = process.env.ATOMIC_SITE || "admin.dreamtechsolution.com"

export default defineConfig({
	plugins: [vue()],
	base: `/assets/${APP}/frontend/`,
	resolve: {
		alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
	},
	build: {
		outDir: `../${APP}/public/frontend`,
		emptyOutDir: true,
		target: "es2019",
		sourcemap: false,
		rollupOptions: {
			output: {
				entryFileNames: "assets/[name].[hash].js",
				chunkFileNames: "assets/[name].[hash].js",
				assetFileNames: "assets/[name].[hash].[ext]",
			},
		},
	},
	server: {
		port: 8083,
		proxy: {
			"^/(api|assets|files|private)": {
				target: process.env.ATOMIC_BACKEND || "http://127.0.0.1:8000",
				changeOrigin: false,
				headers: { Host: SITE },
			},
		},
	},
	test: {
		environment: "jsdom",
	},
})
