<template>
	<n-card size="small" class="uba-about">
		<template #header>
			<div class="flex items-center gap-2">
				<Icon name="carbon:information" :size="16" />
				<span class="text-sm font-semibold">About User Behavior Analytics</span>
				<span v-if="!open" class="text-secondary hidden text-xs sm:inline">
					What UBA is, how risk adds up to an alert, and what each rule means
				</span>
			</div>
		</template>
		<template #header-extra>
			<n-button text size="small" @click="open = !open">{{ open ? "Hide" : "Show" }}</n-button>
		</template>

		<div v-if="open" class="flex flex-col gap-5 text-sm">
			<UbaError v-if="error" :error />
			<n-spin v-else :show="loading" class="min-h-24">
				<div v-if="about" class="flex flex-col gap-5">
					<section class="flex flex-col gap-2">
						<span :class="SECTION_LABEL">What it is</span>
						<p>
							UBA learns how each person and computer
							<i>normally</i>
							behaves (where they sign in from, what they do with email and files, which programs run)
							and points out what is new or unusual. It reads the same Wazuh and Microsoft 365 data
							CoPilot already collects; nothing is installed on users' machines.
						</p>
						<p>
							Each unusual thing it finds is a
							<b>finding</b>
							with a number of risk points. Points add up per person or computer, and when they reach
							<b>{{ about.policy.alert_threshold }}</b>
							UBA raises an
							<b>alert</b>
							that also appears in Incidents → Alerts. One finding rarely means trouble; several
							together usually do.
						</p>
					</section>

					<section class="flex flex-col gap-2">
						<span :class="SECTION_LABEL">How risk adds up</span>
						<ul class="flex list-disc flex-col gap-1 pl-5">
							<li>
								Each finding adds its rule's points (between {{ minScore }} and {{ maxScore }}).
								An alert opens at
								<b>{{ about.policy.alert_threshold }}</b>
								points, or at once for a single finding worth {{ about.policy.single_signal_threshold }} or more.
							</li>
							<li>
								Points fade: they
								<b>halve every {{ halfLife }}</b>
								and are dropped after {{ about.policy.horizon_days }} days, so old findings stop counting.
							</li>
							<li>
								The same rule firing again for the same person within {{ about.policy.repeat_window_hours }}
								hours counts {{ Math.round(about.policy.repeat_decay * 100) }}% as much each time, so one noisy
								rule cannot raise an alert alone.
							</li>
							<li>
								Findings about
								<b>administrators</b>
								count {{ about.policy.privileged_multiplier }}×: their accounts can do more damage.
							</li>
							<li>
								Wazuh's own alerts add context, at most {{ about.policy.max_native_per_window }} points per
								person or computer per day. They cannot raise a UBA alert on their own; UBA's findings
								must.
							</li>
							<li>
								Many rules first
								<b>learn</b>
								what is normal (usually 7 to 14 days) and stay quiet until then. A new customer sees few
								findings at first.
							</li>
						</ul>
					</section>

					<section class="flex flex-col gap-2">
						<span :class="SECTION_LABEL">What you can do</span>
						<ul class="flex list-disc flex-col gap-1 pl-5">
							<li>
								<b>Give a verdict</b>
								on an alert (here or in Incidents → Alerts). A false positive can suppress the rules
								behind it for that person for 30 days.
							</li>
							<li>
								<b>Suppress</b>
								a rule for one person or computer when it is expected there: findings are kept but add
								no points.
							</li>
							<li>
								<b>Show events</b>
								under any finding to see the original records it came from.
							</li>
							<li>
								<b>Backtest</b>
								rules (Rules tab) to see what they would have found over recent days, without alerting.
							</li>
						</ul>
					</section>

					<section class="flex flex-col gap-2">
						<span :class="SECTION_LABEL">The {{ about.rule_count }} rules</span>
						<p class="text-secondary text-xs">
							Grouped by what they watch, strongest first. "Adds to" says whose risk the points go to.
						</p>
						<n-collapse :default-expanded-names="[]" arrow-placement="right">
							<n-collapse-item v-for="c of about.categories" :key="c.id" :name="c.id">
								<template #header>
									<div class="flex flex-col">
										<span class="font-semibold">{{ c.label }} ({{ c.rules.length }})</span>
										<span class="text-secondary text-xs">{{ c.summary }}</span>
									</div>
								</template>
								<ul class="divide-border border-default flex flex-col divide-y rounded-lg border">
									<li v-for="r of c.rules" :key="r.id" class="flex flex-col gap-1 px-3 py-2">
										<div class="flex flex-wrap items-center gap-2">
											<n-tag size="small" round :bordered="false">{{ r.score }} pts</n-tag>
											<b>{{ r.name }}</b>
											<n-tag v-if="!r.enabled" size="tiny" :bordered="false">off</n-tag>
										</div>
										<p>{{ r.description }}</p>
										<p class="text-secondary text-xs">{{ r.how }}</p>
										<p class="text-tertiary text-xs">
											Adds to {{ r.about }}
											<template v-if="r.mitre.length">· MITRE {{ r.mitre.join(", ") }}</template>
											·
											<span class="font-mono">{{ r.id }}</span>
										</p>
									</li>
								</ul>
							</n-collapse-item>
						</n-collapse>
					</section>

					<section class="flex flex-col gap-2">
						<span :class="SECTION_LABEL">Words used on this page</span>
						<dl class="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-[max-content_1fr]">
							<template v-for="g of GLOSSARY" :key="g.term">
								<dt class="font-semibold">{{ g.term }}</dt>
								<dd class="text-secondary">{{ g.meaning }}</dd>
							</template>
						</dl>
					</section>
				</div>
			</n-spin>
		</div>
	</n-card>
</template>

<script setup lang="ts">
// For people new to UBA: what it is, how risk adds up (UBA's own numbers, GET /v1/about) and every rule
// in plain words. Open on the first visit; the choice is remembered. Loaded when opened.
import type { ApiError } from "@/types/common"
import type { UbaAbout } from "@/types/uba"
import { useLocalStorage } from "@vueuse/core"
import { NButton, NCard, NCollapse, NCollapseItem, NSpin, NTag } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { SECTION_LABEL } from "@/components/common/section-label"
import UbaError from "./UbaError.vue"

const { customerCode } = defineProps<{ customerCode: string }>()

const GLOSSARY = [
	{ term: "Entity", meaning: "A person (user account), a computer, or an IP address UBA keeps a risk score for." },
	{ term: "Finding", meaning: "One unusual thing a rule noticed, worth some risk points (also called a signal)." },
	{ term: "Risk", meaning: "An entity's points from recent findings, fading over time." },
	{ term: "Alert", meaning: "Raised when an entity's risk crosses the threshold; it lists the findings behind it." },
	{ term: "Native alert", meaning: "An alert from Wazuh itself, counted as context with capped points." },
	{ term: "Suppression", meaning: "A rule muted for one entity for a while: its findings are kept but add no points." },
	{ term: "Learning period", meaning: "The days a rule watches to learn what is normal before it can fire." }
]

const open = useLocalStorage("uba-about-open", true)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const about = ref<UbaAbout | null>(null)

const scores = computed(() => about.value?.categories.flatMap(c => c.rules.map(r => r.score)) ?? [])
const minScore = computed(() => Math.min(...scores.value))
const maxScore = computed(() => Math.max(...scores.value))
const halfLife = computed(() => {
	const hours = about.value?.policy.half_life_hours ?? 0
	return hours % 24 === 0 ? `${hours / 24} days` : `${hours} hours`
})

function load() {
	if (about.value || loading.value) return
	loading.value = true
	error.value = null
	Api.uba
		.getAbout(customerCode)
		.then(res => {
			about.value = res.data
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
}

watch(open, value => value && load(), { immediate: true })
</script>
