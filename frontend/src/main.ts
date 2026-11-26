import "@fontsource-variable/bricolage-grotesque"
import "@fontsource-variable/plus-jakarta-sans"
import "./styles/main.css"

import { createPinia } from "pinia"
import { createApp } from "vue"

import App from "./App.vue"
import { registerServiceWorker } from "./lib/pwa"
import { applyTheme } from "./lib/theme"
import { router } from "./router"

applyTheme()
const app = createApp(App).use(createPinia()).use(router)
router.isReady().then(() => app.mount("#app"))

registerServiceWorker()
