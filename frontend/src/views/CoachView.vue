<script setup lang="ts">
import { Bot, Check, History, MessageSquarePlus, Plus, SendHorizontal, Trash2 } from "lucide-vue-next"
import { computed, nextTick, onMounted, ref } from "vue"

import { deleteConversation, getCoachStatus, getConversation, getConversations, sendCoachMessage } from "@/api/growth"
import type { CoachMessage, CoachStatus, CoachSuggestion, HabitInput } from "@/api/types"
import HabitIcon from "@/components/habits/HabitIcon.vue"
import AppButton from "@/components/ui/AppButton.vue"
import BottomSheet from "@/components/ui/BottomSheet.vue"
import PageHeader from "@/components/ui/PageHeader.vue"
import { formatDay } from "@/lib/dates"
import { online } from "@/lib/pwa"
import { useConfirm } from "@/stores/confirm"
import { useHabits } from "@/stores/habits"
import { useSession } from "@/stores/session"
import { useToast } from "@/stores/toast"

const session = useSession()
const habits = useHabits()
const toast = useToast()
const confirm = useConfirm()

const status = ref<CoachStatus | null>(null)
const conversation = ref<string | undefined>()
const messages = ref<CoachMessage[]>([])
const draft = ref("")
const sending = ref(false)
const scroller = ref<HTMLElement | null>(null)
const input = ref<HTMLTextAreaElement | null>(null)

const history = ref<{ name: string; title: string; last_message_at: string | null }[]>([])
const showHistory = ref(false)
const added = ref(new Set<string>())
const adding = ref(new Set<string>())

const STARTERS = [
	"Suggest habits for better sleep",
	"How am I doing this week?",
	"I keep missing a habit. Help me make it easier",
	"Give me some motivation",
]

onMounted(async () => {
	try {
		;[status.value, history.value] = await Promise.all([getCoachStatus(), getConversations()])
	} catch {
		/* the chat still works; the status pill just stays hidden */
	}
})

async function scrollDown() {
	await nextTick()
	scroller.value?.scrollIntoView({ block: "end", behavior: "smooth" })
}

async function send(text = draft.value) {
	const message = text.trim()
	if (!message || sending.value) return
	if (!online.value) return toast.error("You're offline. The coach needs a connection.")
	sending.value = true
	draft.value = ""
	messages.value.push({ role: "user", content: message, created_at: new Date().toISOString(), provider: "" })
	void scrollDown()
	try {
		const res = await sendCoachMessage(message, conversation.value)
		// new chat, or the old one was full and the server continued in a new one
		if (!history.value.some((h) => h.name === res.conversation)) {
			history.value.unshift({ name: res.conversation, title: message.slice(0, 60), last_message_at: null })
		}
		conversation.value = res.conversation
		messages.value.push({
			role: "assistant",
			content: res.reply,
			created_at: new Date().toISOString(),
			provider: res.provider,
			suggestions: res.suggestions,
			note: res.note,
		})
	} catch (e) {
		messages.value.pop()
		draft.value = message
		toast.error((e as Error).message)
	} finally {
		sending.value = false
		void scrollDown()
		input.value?.focus()
	}
}

function onKey(e: KeyboardEvent) {
	if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
		e.preventDefault()
		void send()
	}
}

async function open(name: string) {
	showHistory.value = false
	try {
		const conv = await getConversation(name)
		conversation.value = conv.name
		messages.value = conv.messages
		void scrollDown()
	} catch (e) {
		toast.error((e as Error).message)
	}
}

function startNew() {
	showHistory.value = false
	conversation.value = undefined
	messages.value = []
	input.value?.focus()
}

async function remove(name: string) {
	const ok = await confirm.ask({ title: "Delete this chat?", confirmLabel: "Delete", danger: true })
	if (!ok) return
	try {
		await deleteConversation(name)
		history.value = history.value.filter((h) => h.name !== name)
		if (conversation.value === name) startNew()
	} catch (e) {
		toast.error((e as Error).message)
	}
}

async function addHabit(s: CoachSuggestion) {
	if (added.value.has(s.habit_name)) return
	adding.value.add(s.habit_name)
	try {
		const data: Partial<HabitInput> = { habit_name: s.habit_name, icon: s.icon, color: s.color, category: s.category }
		if (s.time_of_day) data.time_of_day = s.time_of_day
		if (s.habit_type) data.habit_type = s.habit_type
		if (s.daily_target) Object.assign(data, { daily_target: s.daily_target, target_unit: s.target_unit })
		await habits.create(data)
		added.value.add(s.habit_name)
		toast.success(`Added "${s.habit_name}" to your habits.`)
	} catch (e) {
		toast.error((e as Error).message)
	} finally {
		adding.value.delete(s.habit_name)
	}
}

const subtitle = computed(() =>
	status.value ? (status.value.ai ? "Powered by Claude, using your own progress" : "Tips from your own progress") : undefined,
)
</script>

<template>
	<div>
		<PageHeader title="AI Coach" :subtitle="subtitle">
			<template #actions>
				<AppButton variant="ghost" aria-label="Past chats" @click="showHistory = true"><History class="h-5 w-5" /></AppButton>
				<AppButton v-if="messages.length" variant="secondary" @click="startNew"><MessageSquarePlus class="h-5 w-5" /> New</AppButton>
			</template>
		</PageHeader>

		<!-- welcome -->
		<section v-if="!messages.length" class="rounded-4xl bg-white p-6 shadow-soft dark:bg-night-900">
			<span class="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-grape-500 to-grape-700 text-white shadow-lift">
				<Bot class="h-7 w-7" />
			</span>
			<h2 class="mt-4 text-[22px] font-extrabold leading-tight">Hi {{ session.firstName || "there" }}, what would you like to work on?</h2>
			<p class="mt-2 text-[15px] text-ink-500 dark:text-ink-400">
				I can suggest small habits for a goal, help when one keeps slipping, or sum up your week. I only see your own habits and check-ins.
			</p>
			<div class="mt-5 flex flex-wrap gap-2">
				<button
					v-for="s in STARTERS"
					:key="s"
					type="button"
					class="rounded-2xl bg-grape-50 px-4 py-2.5 text-left text-[14px] font-semibold text-grape-700 transition hover:bg-grape-100 dark:bg-grape-500/15 dark:text-grape-200 dark:hover:bg-grape-500/25"
					:disabled="sending"
					@click="send(s)"
				>
					{{ s }}
				</button>
			</div>
		</section>

		<!-- conversation -->
		<ol v-else class="space-y-4" aria-live="polite">
			<li v-for="(m, i) in messages" :key="i" class="flex" :class="m.role === 'user' ? 'justify-end' : 'justify-start'">
				<div class="max-w-[88%] sm:max-w-[75%]">
					<div
						class="whitespace-pre-line rounded-3xl px-4 py-3 text-[15px] leading-relaxed"
						:class="
							m.role === 'user'
								? 'rounded-br-lg bg-grape-500 text-white'
								: 'rounded-bl-lg bg-white shadow-soft dark:bg-night-900'
						"
					>
						{{ m.content }}
					</div>
					<p v-if="m.note" class="mt-1.5 px-2 text-[12px] text-ink-500 dark:text-ink-400">{{ m.note }}</p>
					<ul v-if="m.suggestions?.length" class="mt-2 space-y-2">
						<li v-for="s in m.suggestions" :key="s.habit_name" class="flex items-center gap-3 rounded-3xl bg-white p-3 shadow-soft dark:bg-night-900">
							<HabitIcon :icon="s.icon" :color="s.color" size="sm" />
							<span class="min-w-0 flex-1">
								<span class="block text-[15px] font-bold">{{ s.habit_name }}</span>
								<span class="block text-[13px] text-ink-500 dark:text-ink-400">{{ s.why }}</span>
							</span>
							<button
								type="button"
								class="flex h-10 shrink-0 items-center gap-1 rounded-xl px-3 text-[13px] font-bold transition"
								:class="added.has(s.habit_name) ? 'bg-mint-50 text-mint-700 dark:bg-mint-500/15 dark:text-mint-400' : 'bg-grape-500 text-white hover:bg-grape-600'"
								:disabled="added.has(s.habit_name) || adding.has(s.habit_name)"
								:aria-label="added.has(s.habit_name) ? `${s.habit_name} added` : `Add ${s.habit_name}`"
								@click="addHabit(s)"
							>
								<Check v-if="added.has(s.habit_name)" class="h-4 w-4" />
								<Plus v-else class="h-4 w-4" :stroke-width="2.6" />
								{{ added.has(s.habit_name) ? "Added" : "Add" }}
							</button>
						</li>
					</ul>
				</div>
			</li>
			<li v-if="sending" class="flex justify-start">
				<span class="flex gap-1.5 rounded-3xl rounded-bl-lg bg-white px-5 py-4 shadow-soft dark:bg-night-900" aria-label="The coach is typing">
					<span v-for="d in 3" :key="d" class="h-2 w-2 animate-bounce rounded-full bg-grape-400" :style="{ animationDelay: `${d * 120}ms` }" />
				</span>
			</li>
		</ol>
		<div ref="scroller" class="h-28 lg:h-24" aria-hidden="true" />

		<!-- composer: above the tab bar on phones -->
		<form
			class="fixed inset-x-0 z-30 px-4 lg:!bottom-6 lg:left-64 lg:px-10"
			style="bottom: calc(env(safe-area-inset-bottom) + 4.75rem)"
			@submit.prevent="send()"
		>
			<div class="mx-auto flex max-w-3xl items-end gap-2 rounded-3xl bg-white p-2 shadow-sheet ring-2 ring-transparent transition focus-within:ring-grape-300 dark:bg-night-900 dark:focus-within:ring-grape-500/50 lg:max-w-4xl">
				<label for="coach-input" class="sr-only">Message the coach</label>
				<textarea
					id="coach-input"
					ref="input"
					v-model="draft"
					rows="1"
					maxlength="1500"
					placeholder="Ask about your habits…"
					class="max-h-32 min-h-[2.75rem] flex-1 resize-none bg-transparent px-3 py-2.5 text-[15px] !outline-none focus-visible:!ring-0 focus-visible:!ring-offset-0 placeholder:text-ink-400"
					@keydown="onKey"
				/>
				<button
					type="submit"
					class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-grape-500 text-white transition hover:bg-grape-600 disabled:opacity-40"
					:disabled="!draft.trim() || sending"
					aria-label="Send"
				>
					<SendHorizontal class="h-5 w-5" />
				</button>
			</div>
		</form>

		<!-- past chats -->
		<BottomSheet :open="showHistory" title="Past chats" @close="showHistory = false">
			<AppButton variant="secondary" block @click="startNew"><MessageSquarePlus class="h-5 w-5" /> New chat</AppButton>
			<p v-if="!history.length" class="mt-4 text-center text-[14px] text-ink-500 dark:text-ink-400">No chats yet.</p>
			<ul class="mt-3 space-y-1">
				<li v-for="h in history" :key="h.name" class="flex items-center gap-1">
					<button
						type="button"
						class="min-w-0 flex-1 rounded-2xl px-3 py-2.5 text-left hover:bg-ink-100 dark:hover:bg-night-800"
						:class="h.name === conversation ? 'bg-grape-50 dark:bg-grape-500/15' : ''"
						@click="open(h.name)"
					>
						<span class="block truncate text-[15px] font-semibold">{{ h.title }}</span>
						<span v-if="h.last_message_at" class="block text-[12px] text-ink-500 dark:text-ink-400">
							{{ formatDay(h.last_message_at.slice(0, 10), { day: "numeric", month: "short" }) }}
						</span>
					</button>
					<button type="button" class="rounded-xl p-2.5 text-ink-400 hover:bg-ink-100 hover:text-blush-600 dark:hover:bg-night-800" :aria-label="`Delete ${h.title}`" @click="remove(h.name)">
						<Trash2 class="h-4 w-4" />
					</button>
				</li>
			</ul>
		</BottomSheet>
	</div>
</template>
