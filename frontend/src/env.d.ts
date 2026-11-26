/// <reference types="vite/client" />

declare module "*.vue" {
	import type { DefineComponent } from "vue"
	const component: DefineComponent<object, object, unknown>
	export default component
}

interface Window {
	csrf_token?: string
	/** 1 when the page was rendered for a signed-out visitor (set by www/atomic_streak_app.html). */
	atomic_guest?: number
}
