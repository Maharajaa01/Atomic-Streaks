import { defineStore } from "pinia"

export interface Toast {
	id: number
	message: string
	tone: "success" | "error" | "info"
	action?: { label: string; run: () => void }
}

let seq = 0

export const useToast = defineStore("toast", {
	state: () => ({ items: [] as Toast[] }),
	actions: {
		show(message: string, tone: Toast["tone"] = "info", action?: Toast["action"], ms = 4000) {
			const id = ++seq
			this.items = [...this.items.slice(-2), { id, message, tone, action }]
			setTimeout(() => this.dismiss(id), ms)
			return id
		},
		success(message: string, action?: Toast["action"]) {
			return this.show(message, "success", action)
		},
		error(message: string, action?: Toast["action"]) {
			return this.show(message, "error", action, 6000)
		},
		dismiss(id: number) {
			this.items = this.items.filter((t) => t.id !== id)
		},
	},
})
