<script setup lang="ts">
/**
 * Minimal ECharts host: lazy-loads lib/echarts, resizes with its box, re-renders when the
 * option (a function of the current theme) changes, and disposes on unmount.
 */
import type { EChartsType } from "echarts/core"
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue"

import { isDark } from "@/lib/theme"

const props = withDefaults(defineProps<{ option: (dark: boolean) => Record<string, unknown>; height?: number; label: string }>(), {
	height: 220,
})
const el = ref<HTMLElement | null>(null)
const chart = shallowRef<EChartsType | null>(null)
let observer: ResizeObserver | null = null

function render() {
	chart.value?.setOption(props.option(isDark.value), { notMerge: true })
}

onMounted(async () => {
	const { default: echarts } = await import("@/lib/echarts")
	if (!el.value) return
	chart.value = echarts.init(el.value, undefined, { renderer: "canvas" })
	render()
	observer = new ResizeObserver(() => chart.value?.resize())
	observer.observe(el.value)
})
watch(() => [props.option, isDark.value], render)
onBeforeUnmount(() => {
	observer?.disconnect()
	chart.value?.dispose()
})
</script>

<template>
	<div ref="el" role="img" :aria-label="label" :style="{ height: `${height}px` }" class="w-full" />
</template>
