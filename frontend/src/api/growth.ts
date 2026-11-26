/** Challenges, badges and XP, routines and the coach (Phase 6). */
import { call } from "./client"
import type {
	Celebrations,
	ChallengesOverview,
	CoachReply,
	CoachStatus,
	CoachSuggestion,
	ProgressSummary,
	Routine,
	TimeOfDay,
} from "./types"

// challenges, badges, XP
export const getChallenges = () => call<ChallengesOverview>("challenge.get_challenges")
export const joinChallenge = (challenge: string, opts: { habit?: string; habit_name?: string } = {}) =>
	call<{ name: string; habit: string }>("challenge.join_challenge", { challenge, ...opts }, { method: "POST" })
export const leaveChallenge = (name: string) => call<{ ok: boolean }>("challenge.leave_challenge", { name }, { method: "POST" })
export const createChallenge = (data: { title: string; duration_days: number; description?: string; icon?: string; color?: string }) =>
	call<{ name: string }>("challenge.create_challenge", data, { method: "POST" })
export const getProgress = () => call<ProgressSummary>("challenge.get_progress")
export const getCelebrations = () => call<Celebrations>("challenge.get_celebrations")
export const markCelebrated = (achievements: string[], challenges_done: string[]) =>
	call<{ ok: boolean }>("challenge.mark_celebrated", { achievements, challenges_done }, { method: "POST" })

// routines (habit stacking)
export interface RoutineInput {
	routine_name: string
	cue?: string
	icon?: string
	color?: string
	time_of_day?: TimeOfDay
	steps: { habit: string; note?: string }[]
}
export const getRoutines = () => call<Routine[]>("routine.get_routines")
export const saveRoutine = (data: Partial<RoutineInput>, name?: string) =>
	call<Routine>("routine.save_routine", { data, name }, { method: "POST" })
export const deleteRoutine = (name: string) => call<{ ok: boolean }>("routine.delete_routine", { name }, { method: "POST" })

// coach
export const getCoachStatus = () => call<CoachStatus>("coach.get_status")
export const sendCoachMessage = (message: string, conversation?: string) =>
	call<CoachReply>("coach.chat", { message, conversation }, { method: "POST" })
export const getConversations = () =>
	call<{ name: string; title: string; last_message_at: string | null }[]>("coach.get_conversations")
export const getConversation = (name: string) =>
	call<{ name: string; title: string; messages: { role: "user" | "assistant"; content: string; created_at: string; provider: string }[] }>(
		"coach.get_conversation",
		{ name },
	)
export const deleteConversation = (name: string) => call<{ ok: boolean }>("coach.delete_conversation", { name }, { method: "POST" })
export const getWeeklySummary = () => call<{ text: string }>("coach.get_weekly_summary")
export const suggestHabits = (goal?: string) => call<CoachSuggestion[]>("coach.suggest_habits", { goal })
