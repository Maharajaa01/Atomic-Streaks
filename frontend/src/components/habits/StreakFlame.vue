<script setup lang="ts">
/**
 * An animated fire. Three flame layers flicker at different speeds, embers drift up and a
 * glow breathes underneath. `heat` (0–1) grows the fire with the streak; an unlit flame
 * (streak 0) is a still, grey ember waiting for its first check-in.
 */
import { computed, useId } from "vue"

const props = withDefaults(defineProps<{ heat?: number; lit?: boolean; size?: number }>(), { heat: 0.5, lit: true, size: 180 })

const id = useId()
const scale = computed(() => (props.lit ? 0.78 + 0.32 * Math.min(Math.max(props.heat, 0), 1) : 0.62))

// fixed ember positions so the fire looks the same every time
const EMBERS = [
	{ x: 42, delay: "0s", dur: "1.9s", drift: "-10px", r: 2.6 },
	{ x: 58, delay: ".6s", dur: "2.3s", drift: "8px", r: 2 },
	{ x: 74, delay: "1.1s", dur: "1.7s", drift: "12px", r: 2.4 },
	{ x: 50, delay: "1.5s", dur: "2.1s", drift: "-6px", r: 1.8 },
	{ x: 68, delay: ".3s", dur: "2.5s", drift: "-12px", r: 1.6 },
]
</script>

<template>
	<div class="flame relative" :class="{ 'is-lit': lit }" :style="{ width: `${size}px`, height: `${size * 1.25}px` }" aria-hidden="true">
		<div class="glow absolute inset-x-[8%] bottom-[2%] h-[46%] rounded-full" />
		<svg viewBox="0 0 120 160" class="relative h-full w-full overflow-visible" :style="{ transform: `scale(${scale})`, transformOrigin: '50% 95%' }">
			<defs>
				<linearGradient :id="`${id}-outer`" x1="0" y1="1" x2="0" y2="0">
					<stop offset="0" :stop-color="lit ? '#FF4D1A' : '#9AA1B5'" />
					<stop offset="1" :stop-color="lit ? '#FF9F43' : '#C8CDDB'" />
				</linearGradient>
				<linearGradient :id="`${id}-mid`" x1="0" y1="1" x2="0" y2="0">
					<stop offset="0" :stop-color="lit ? '#FF9F1A' : '#B4BACB'" />
					<stop offset="1" :stop-color="lit ? '#FFD166' : '#E1E4EE'" />
				</linearGradient>
				<linearGradient :id="`${id}-core`" x1="0" y1="1" x2="0" y2="0">
					<stop offset="0" :stop-color="lit ? '#FFF7DE' : '#EEF0F6'" />
					<stop offset="1" :stop-color="lit ? '#FFE08A' : '#F7F8FC'" />
				</linearGradient>
			</defs>

			<g class="layer outer">
				<path
					:fill="`url(#${id}-outer)`"
					d="M60 6C70 36 104 56 104 100C104 134 84 154 60 154C36 154 16 134 16 100C16 76 30 62 38 46C42 62 48 70 54 72C50 50 52 26 60 6Z"
				/>
			</g>
			<g class="layer mid">
				<path
					:fill="`url(#${id}-mid)`"
					d="M60 48C68 70 88 84 88 110C88 134 76 148 60 148C44 148 32 134 32 112C32 96 42 88 46 78C50 90 54 96 58 96C56 82 56 64 60 48Z"
				/>
			</g>
			<g class="layer core">
				<path :fill="`url(#${id}-core)`" d="M60 92C66 104 76 112 76 126C76 138 69 146 60 146C51 146 44 138 44 127C44 116 54 108 60 92Z" />
			</g>

			<template v-if="lit">
				<circle
					v-for="(e, i) in EMBERS"
					:key="i"
					class="ember"
					:cx="e.x"
					cy="60"
					:r="e.r"
					fill="#FFB347"
					:style="{ animationDelay: e.delay, animationDuration: e.dur, '--drift': e.drift }"
				/>
			</template>
		</svg>
	</div>
</template>

<style scoped>
.layer {
	transform-box: fill-box;
	transform-origin: 50% 100%;
}
.glow {
	background: radial-gradient(closest-side, rgba(154, 161, 181, 0.35), transparent);
}
.is-lit .glow {
	background: radial-gradient(closest-side, rgba(255, 140, 40, 0.55), rgba(255, 80, 20, 0.15) 60%, transparent);
	animation: glow 1.6s ease-in-out infinite;
}
.is-lit .outer {
	animation: flicker-a 1.3s ease-in-out infinite;
}
.is-lit .mid {
	animation: flicker-b 0.95s ease-in-out infinite;
}
.is-lit .core {
	animation: flicker-c 0.7s ease-in-out infinite;
}
.flame.is-lit {
	animation: ignite 0.7s cubic-bezier(0.2, 0.9, 0.3, 1.3) both;
}
.ember {
	opacity: 0;
	transform-box: fill-box;
	animation: ember 2s ease-out infinite;
}

@keyframes ignite {
	0% {
		opacity: 0;
		transform: scale(0.3) translateY(30px);
	}
	100% {
		opacity: 1;
		transform: none;
	}
}
@keyframes flicker-a {
	0%,
	100% {
		transform: scale(1, 1) skewX(0deg);
	}
	25% {
		transform: scale(0.97, 1.04) skewX(1.5deg);
	}
	50% {
		transform: scale(1.02, 0.97) skewX(-1deg);
	}
	75% {
		transform: scale(0.98, 1.03) skewX(-2deg);
	}
}
@keyframes flicker-b {
	0%,
	100% {
		transform: scale(1, 1) skewX(0deg);
	}
	33% {
		transform: scale(0.95, 1.07) skewX(-2.5deg);
	}
	66% {
		transform: scale(1.04, 0.95) skewX(2deg);
	}
}
@keyframes flicker-c {
	0%,
	100% {
		transform: scale(1, 1);
	}
	50% {
		transform: scale(0.92, 1.1);
	}
}
@keyframes glow {
	0%,
	100% {
		opacity: 0.75;
		transform: scale(1);
	}
	50% {
		opacity: 1;
		transform: scale(1.08);
	}
}
@keyframes ember {
	0% {
		opacity: 0;
		transform: translate(0, 0) scale(1);
	}
	15% {
		opacity: 1;
	}
	100% {
		opacity: 0;
		transform: translate(var(--drift), -70px) scale(0.3);
	}
}
</style>
