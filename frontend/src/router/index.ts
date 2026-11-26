import { createRouter, createWebHistory } from "vue-router"

declare module "vue-router" {
	interface RouteMeta {
		title?: string
		/** sign-in pages: no app shell, no boot data */
		public?: boolean
		/** reachable whether or not someone is signed in (e.g. a reset link) */
		anyone?: boolean
		/** which main tab lights up (detail pages belong to their list's tab) */
		section?: string
		/** full-screen forms: no bottom tab bar */
		hideTabs?: boolean
	}
}


export const router = createRouter({
	history: createWebHistory("/atomic-streak/"),
	scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
	routes: [
		{ path: "/login", name: "login", component: () => import("@/views/auth/LoginView.vue"), meta: { title: "Sign in", public: true } },
		{ path: "/signup", name: "signup", component: () => import("@/views/auth/SignupView.vue"), meta: { title: "Create account", public: true } },
		{ path: "/forgot-password", name: "forgot-password", component: () => import("@/views/auth/ForgotPasswordView.vue"), meta: { title: "Forgot password", public: true } },
		{
			path: "/reset-password",
			name: "reset-password",
			component: () => import("@/views/auth/ResetPasswordView.vue"),
			meta: { title: "Choose a new password", public: true, anyone: true },
		},

		{ path: "/", name: "home", component: () => import("@/views/DashboardView.vue"), meta: { title: "Home" } },
		{ path: "/habits", name: "habits", component: () => import("@/views/HabitsView.vue"), meta: { title: "My Habits" } },
		{
			path: "/habits/new",
			name: "habit-new",
			component: () => import("@/views/HabitFormView.vue"),
			meta: { title: "New habit", section: "habits", hideTabs: true },
		},
		{
			path: "/habits/:name",
			name: "habit",
			component: () => import("@/views/HabitDetailView.vue"),
			props: true,
			meta: { title: "Habit", section: "habits" },
		},
		{
			path: "/habits/:name/edit",
			name: "habit-edit",
			component: () => import("@/views/HabitFormView.vue"),
			props: true,
			meta: { title: "Edit habit", section: "habits", hideTabs: true },
		},
		{ path: "/calendar", name: "calendar", component: () => import("@/views/CalendarView.vue"), meta: { title: "Calendar" } },
		{ path: "/insights", name: "insights", component: () => import("@/views/InsightsView.vue"), meta: { title: "Insights" } },
		{ path: "/challenges", name: "challenges", component: () => import("@/views/ChallengesView.vue"), meta: { title: "Challenges" } },
		{ path: "/coach", name: "coach", component: () => import("@/views/CoachView.vue"), meta: { title: "AI Coach" } },
		{ path: "/plan", name: "plan", component: () => import("@/views/PlannerView.vue"), meta: { title: "Day Plan" } },
		{ path: "/routines", name: "routines", component: () => import("@/views/RoutinesView.vue"), meta: { title: "Routines" } },
		{ path: "/profile", name: "profile", component: () => import("@/views/ProfileView.vue"), meta: { title: "Profile" } },
		{ path: "/:pathMatch(.*)*", name: "not-found", component: () => import("@/views/NotFoundView.vue"), meta: { title: "Not found" } },
	],
})

const isGuest = () => window.atomic_guest === 1

router.beforeEach((to) => {
	if (to.meta.anyone) return true
	if (isGuest() && !to.meta.public) {
		return { name: "login", query: to.fullPath !== "/" ? { redirect: to.fullPath } : {} }
	}
	if (!isGuest() && to.meta.public) return { name: "home" }
	return true
})

router.afterEach((to) => {
	document.title = to.meta.title ? `${to.meta.title} · Atomic Streak` : "Atomic Streak"
})
