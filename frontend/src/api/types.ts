export type Theme = "System" | "Light" | "Dark"

export interface Profile {
	full_name: string
	avatar?: string | null
	timezone: string
	has_timezone: boolean
	week_starts_on?: "Monday" | "Sunday"
	theme: Theme
	goals?: string | null
	onboarding_completed?: 0 | 1
	xp: number
	level: number
	current_streak?: number
	longest_streak?: number
	total_completions?: number
}

export interface Boot {
	user: string
	full_name: string
	user_image?: string | null
	has_access: boolean
	allow_join: boolean
	profile?: Profile
	features?: { ai_coach: boolean; push: boolean }
}

export interface AuthOptions {
	allow_signup: boolean
	can_reset_password: boolean
}

export type HabitType = "Build" | "Break" | "One-time"
export type Frequency = "Daily" | "Specific Days" | "Every N Days"
export type HabitStatus = "Active" | "Paused" | "Archived" | "Completed"
export type TimeOfDay = "Anytime" | "Morning" | "Afternoon" | "Evening" | "Night"
export type DayPeriod = Exclude<TimeOfDay, "Anytime">
export type Weekday = "Monday" | "Tuesday" | "Wednesday" | "Thursday" | "Friday" | "Saturday" | "Sunday"

export interface Category {
	name: string
	label: string
	icon: string
	color: string
	is_standard: 0 | 1
}

export interface HabitInput {
	habit_name: string
	description?: string
	icon: string
	category?: string | null
	color: string
	habit_type: HabitType
	frequency: Frequency
	interval_days?: number
	weekdays?: Weekday[]
	start_date?: string
	end_date?: string | null
	time_of_day: TimeOfDay
	preferred_time?: string | null
	daily_target: number
	target_unit: string
	difficulty: "Easy" | "Medium" | "Hard"
	reminder_enabled: 0 | 1
	reminder_time?: string | null
	notes?: string
}

export interface Habit extends HabitInput {
	name: string
	status: HabitStatus
	sort_order: number
	current_streak: number
	longest_streak: number
	total_completions: number
	last_completed_on: string | null
	weekdays: Weekday[]
	category_info: { name: string; label: string; icon: string; color: string } | null
}

export interface Completion {
	name?: string
	value: number
	target: number
	status: "Completed" | "Partial"
	client_id?: string | null
}

export interface TodayHabit extends Habit {
	completion: Completion | null
}

export interface DayProgress {
	date: string
	weekday: string
	scheduled: number
	completed: number
	percent: number
	is_today: boolean
	is_future: boolean
}

export interface StreakSummary {
	current: number
	longest: number
	total_completions: number
}

export interface TodayView {
	date: string
	today: string
	habits: TodayHabit[]
	summary: { total: number; completed: number; remaining: number; percent: number; active_habits: number }
	streak: StreakSummary
	xp: number
	level: number
	week: DayProgress[]
}

export interface CheckInResult {
	date: string
	habit: string
	completion: Completion | null
	stats: { current_streak: number; longest_streak: number; total_completions: number; status: HabitStatus }
	streak: StreakSummary
	xp: LevelProgress
	celebrations: Celebrations
	/** offline sync only: the server kept a newer change made on another device */
	conflict?: boolean
}

export type CellState = "done" | "partial" | "missed" | "pending" | "bonus" | "off"
export type DayState = "done" | "partial" | "missed" | "pending" | "none" | "bonus" | "future"

export interface DaySummary {
	date: string
	scheduled: number
	completed: number
	partial: number
	missed: number
	pending: number
	bonus: number
	percent: number
	state: DayState
}

export interface CalendarData {
	start: string
	end: string
	today: string
	days: DaySummary[]
	habits: { name: string; habit_name: string; icon: string; color: string }[]
	cells?: Record<string, CellState[]>
}

export interface DayDetail {
	date: string
	today: string
	summary: DaySummary
	habits: {
		name: string
		habit_name: string
		icon: string
		color: string
		habit_type: HabitType
		daily_target: number
		target_unit: string
		category: { label: string; color: string } | null
		state: CellState
		value: number
		target: number
		can_edit: boolean
	}[]
}

export interface HabitHistory {
	start: string
	today: string
	cells: { date: string; state: CellState }[]
	week_rate: number | null
	month_rate: number | null
	comebacks: number
}

export interface HabitPerformance {
	name: string
	habit_name: string
	icon: string
	color: string
	status: HabitStatus
	completed: number
	scheduled: number
	rate: number | null
	missed: number
	current_streak: number
	longest_streak: number
}

export interface Insights {
	days: 7 | 30 | 90
	start: string
	today: string
	rate: number | null
	previous_rate: number | null
	completed: number
	scheduled: number
	week_rate: number | null
	month_rate: number | null
	comebacks: number
	streak: StreakSummary
	trend: { date: string; rate: number | null; completed: number; scheduled: number }[]
	weekdays: { weekday: string; rate: number | null; scheduled: number }[]
	habits: HabitPerformance[]
	best: HabitPerformance[]
	struggling: HabitPerformance[]
	longest_streaks: HabitPerformance[]
	categories: { category: string | null; label: string; color: string; completed: number; scheduled: number; rate: number | null }[]
	heatmap: { date: string; completed: number; scheduled: number; percent: number | null }[]
}

// ------------------------------------------------------------------ growth (Phase 6)
export interface LevelProgress {
	xp: number
	level: number
	level_start: number
	next_level_at: number
	progress: number
}

export interface Achievement {
	name: string
	title: string
	description: string
	icon: string
	color: string
	criteria: string
	threshold: number
	xp_reward: number
	earned: boolean
	achieved_on: string | null
}

export interface ProgressSummary extends LevelProgress {
	achievements: Achievement[]
}

export interface Celebrations {
	achievements: { name: string; code: string; xp: number; title: string; description: string; icon: string; color: string }[]
	challenges: { name: string; xp: number; title: string; icon: string; color: string }[]
}

export type ChallengeType = "7-Day" | "21-Day" | "30-Day" | "Custom"
export type ParticipationStatus = "Active" | "Completed" | "Failed" | "Abandoned"

export interface Challenge {
	name: string
	title: string
	description: string | null
	suggested_habit: string | null
	challenge_type: ChallengeType
	duration_days: number
	xp_reward: number
	icon: string
	color: string
	is_standard: 0 | 1
	joined: boolean
	is_mine: boolean
}

export interface Participation {
	name: string
	challenge: string
	habit: string
	status: ParticipationStatus
	start_date: string
	end_date: string
	days_completed: number
	completed_on: string | null
	xp_awarded: number
	day: number
	challenge_info: Pick<Challenge, "name" | "title" | "icon" | "color" | "duration_days" | "xp_reward" | "challenge_type">
	habit_info: { name: string; habit_name: string; icon: string; color: string } | null
	progress: { target: number | null; needed: number | null; done: number; remaining: number }
}

export interface ChallengesOverview {
	today: string
	mine: Participation[]
	discover: Challenge[]
}

export interface RoutineStep {
	habit: string
	habit_name: string
	icon: string
	color: string
	status: HabitStatus
	habit_type: HabitType
	daily_target: number
	target_unit: string
	current_streak: number
	note: string | null
	done: boolean
}

export interface Routine {
	name: string
	routine_name: string
	cue: string | null
	icon: string | null
	color: string | null
	time_of_day: TimeOfDay | null
	is_active: 0 | 1
	sort_order: number
	steps: RoutineStep[]
	done_today: number
}

export interface CoachSuggestion {
	habit_name: string
	icon: string
	color: string
	category: string
	why: string
	time_of_day?: TimeOfDay
	daily_target?: number
	target_unit?: string
	habit_type?: HabitType
}

export interface CoachMessage {
	role: "user" | "assistant"
	content: string
	created_at: string
	provider: string
	suggestions?: CoachSuggestion[]
	note?: string | null
}

export interface CoachStatus {
	ai: boolean
	model: string | null
	daily_limit: number
}

export interface CoachReply {
	conversation: string
	reply: string
	provider: string
	suggestions: CoachSuggestion[]
	note: string | null
}

// ------------------------------------------------------------------ day planner
export type TaskPriority = "Normal" | "High" | "Low"

export interface PlanTask {
	name: string
	plan_date: string
	title: string
	notes: string
	start_time: string | null
	priority: TaskPriority
	is_done: 0 | 1
	done_at: string | null
}

export interface PlanDay {
	date: string
	today: string
	tasks: PlanTask[]
	/** unfinished tasks from earlier days (only when `date` is today) */
	carryover: PlanTask[]
	/** future days that already have tasks */
	upcoming: { date: string; total: number; done: number }[]
}
