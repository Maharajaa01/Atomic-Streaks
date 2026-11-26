import { defineStore } from "pinia"

interface Ask {
	title: string
	body?: string
	confirmLabel: string
	danger?: boolean
	resolve: (ok: boolean) => void
}

export const useConfirm = defineStore("confirm", {
	state: () => ({ current: null as Ask | null }),
	actions: {
		ask(opts: Omit<Ask, "resolve">): Promise<boolean> {
			this.current?.resolve(false)
			return new Promise((resolve) => {
				this.current = { ...opts, resolve }
			})
		},
		answer(ok: boolean) {
			this.current?.resolve(ok)
			this.current = null
		},
	},
})
