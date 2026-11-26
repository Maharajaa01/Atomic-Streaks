import { BarChart3, Bot, CalendarDays, House, Layers, ListChecks, ListTodo, Trophy, UserRound } from "lucide-vue-next"
import type { Component } from "vue"

export interface NavItem {
	name: string
	label: string
	icon: Component
	color: string
}

/** Bottom tab bar on phones, top of the sidebar on desktop. */
export const PRIMARY: NavItem[] = [
	{ name: "home", label: "Home", icon: House, color: "#7657F6" },
	{ name: "habits", label: "My Habits", icon: ListChecks, color: "#26C281" },
	{ name: "calendar", label: "Calendar", icon: CalendarDays, color: "#4D8DFF" },
	{ name: "insights", label: "Insights", icon: BarChart3, color: "#FF9F43" },
	{ name: "plan", label: "Day Plan", icon: ListTodo, color: "#F56FA1" },
]

/** Reached from Home on phones; listed under the main items on desktop. */
export const SECONDARY: NavItem[] = [
	{ name: "routines", label: "Routines", icon: Layers, color: "#1FB5A8" },
	{ name: "challenges", label: "Challenges", icon: Trophy, color: "#FF9F43" },
	{ name: "coach", label: "AI Coach", icon: Bot, color: "#7657F6" },
	{ name: "profile", label: "Profile", icon: UserRound, color: "#F56FA1" },
]
