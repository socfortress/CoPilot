<template>
	<section class="uba-about border-default overflow-hidden rounded-lg border" data-testid="uba-about">
		<header class="bg-secondary flex flex-wrap items-center gap-3 px-4 py-2.5">
			<span class="info-tile grid size-7 shrink-0 place-items-center rounded-md" aria-hidden="true">
				<Icon name="carbon:information" :size="15" />
			</span>
			<div class="flex min-w-0 flex-1 items-baseline gap-2">
				<span class="text-sm font-semibold">About User Behavior Analytics</span>
				<span class="text-tertiary hidden text-xs sm:inline">
					What UBA is, how risk adds up to an alert, and what each rule means
				</span>
			</div>
			<n-button size="small" quaternary :aria-expanded="open" data-testid="uba-about-toggle" @click="open = true">
				Show
				<template #icon><Icon name="carbon:side-panel-open" :size="14" /></template>
			</n-button>
		</header>

		<n-drawer v-model:show="open" :width="720" class="max-w-[95vw]" data-testid="uba-about-drawer">
			<n-drawer-content closable :native-scrollbar="false" body-content-class="uba-about-body">
				<template #header>
					<div class="flex items-center gap-3 py-1">
						<span class="info-tile grid size-9 shrink-0 place-items-center rounded-lg" aria-hidden="true">
							<Icon name="carbon:information" :size="18" />
						</span>
						<div class="flex min-w-0 flex-col gap-0.5">
							<span class="text-tertiary font-mono text-[10px] tracking-widest uppercase">
								SOCFortress UBA
							</span>
							<span class="text-lg leading-tight font-semibold">About User Behavior Analytics</span>
						</div>
					</div>
				</template>
				<div class="text-sm">
					<UbaError v-if="error" :error />
					<n-spin v-else :show="loading" class="min-h-24">
						<div v-if="about" class="flex flex-col gap-7">
							<UbaSection title="What it is">
								<p class="text-default m-0 leading-relaxed">
									UBA learns how each person and computer
									<i>normally</i>
									behaves (where they sign in from, what they do with email and files, which programs
									run) and points out what is new or unusual. It reads the same Wazuh and Microsoft
									365 data CoPilot already collects; nothing is installed on users' machines.
								</p>
								<p class="text-default m-0 leading-relaxed">
									Each unusual thing it finds is a
									<b>finding</b>
									with a number of risk points. Points add up per person or computer, and when they
									reach
									<b>{{ about.policy.alert_threshold }}</b>
									UBA raises an
									<b>alert</b>
									that also appears in Incidents → Alerts. One finding rarely means trouble; several
									together usually do.
								</p>
							</UbaSection>

							<UbaSection title="How risk adds up">
								<ul class="marked m-0 flex list-none flex-col gap-1.5 p-0">
									<li>
										Each finding adds its rule's points (between {{ minScore }} and {{ maxScore }}).
										An alert opens at
										<b>{{ about.policy.alert_threshold }}</b>
										points, or at once for a single finding worth
										{{ about.policy.single_signal_threshold }} or more.
									</li>
									<li>
										Points fade: they
										<b>halve every {{ halfLife }}</b>
										and are dropped after {{ about.policy.horizon_days }} days, so old findings stop
										counting.
									</li>
									<li>
										The same rule firing again for the same person within
										{{ about.policy.repeat_window_hours }} hours counts
										{{ Math.round(about.policy.repeat_decay * 100) }}% as much each time, so one
										noisy rule cannot raise an alert alone.
									</li>
									<li>
										Findings about
										<b>administrators</b>
										count {{ about.policy.privileged_multiplier }}×: their accounts can do more
										damage.
									</li>
									<li>
										Wazuh's own alerts add context, at most
										{{ about.policy.max_native_per_window }} points per person or computer per day.
										They cannot raise a UBA alert on their own; UBA's findings must.
									</li>
									<li>
										Many rules first
										<b>learn</b>
										what is normal (usually 7 to 14 days) and stay quiet until then. A new customer
										sees few findings at first.
									</li>
								</ul>
							</UbaSection>

							<UbaSection title="What you can do">
								<ul class="marked m-0 flex list-none flex-col gap-1.5 p-0">
									<li>
										<b>Give a verdict</b>
										on an alert (here or in Incidents → Alerts). A false positive can suppress the
										rules behind it for that person for 30 days.
									</li>
									<li>
										<b>Suppress</b>
										a rule for one person or computer when it is expected there: findings are kept
										but add no points.
									</li>
									<li>
										<b>Show events</b>
										under any finding to see the original records it came from.
									</li>
									<li>
										<b>Backtest</b>
										rules (Rules tab) to see what they would have found over recent days, without
										alerting.
									</li>
								</ul>
							</UbaSection>

							<UbaSection title="Words used on this page">
								<dl class="glossary m-0 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1.5">
									<template v-for="g of GLOSSARY" :key="g.term">
										<dt>{{ g.term }}</dt>
										<dd class="text-secondary m-0">{{ g.meaning }}</dd>
									</template>
								</dl>
							</UbaSection>

							<UbaSection
								:title="`The ${about.rule_count} rules`"
								caption="grouped by what they watch, strongest first"
							>
								<p class="text-secondary m-0 text-xs">"Adds to" says whose risk the points go to.</p>
								<n-collapse :default-expanded-names="[]" arrow-placement="right" class="rules w-full">
									<n-collapse-item
										v-for="c of about.categories"
										:key="c.id"
										:name="c.id"
										class="w-full"
									>
										<template #header>
											<div class="flex w-full flex-col">
												<span class="font-semibold">{{ c.label }} ({{ c.rules.length }})</span>
												<span class="text-secondary text-xs">{{ c.summary }}</span>
											</div>
										</template>
										<ul
											class="rule-list border-default m-0 flex list-none flex-col overflow-hidden rounded-lg border p-0"
										>
											<li
												v-for="r of c.rules"
												:key="r.id"
												class="rule-item flex flex-col gap-0.5 px-3 py-2"
											>
												<div class="flex flex-wrap items-center gap-x-2 gap-y-0.5">
													<span class="score font-mono text-[11px] tabular-nums">
														{{ r.score }} pts
													</span>
													<span class="text-[13px] font-semibold">{{ r.name }}</span>
													<n-tag v-if="!r.enabled" size="tiny" :bordered="false">off</n-tag>
												</div>
												<p class="text-secondary m-0 text-xs leading-snug">
													{{ r.description }}
												</p>
												<p class="text-tertiary m-0 text-[11px] leading-snug">
													{{ r.how }} · Adds to {{ r.about }}
													<template v-if="r.mitre.length">
														· MITRE {{ r.mitre.join(", ") }}
													</template>
													·
													<span class="font-mono">{{ r.id }}</span>
												</p>
											</li>
										</ul>
									</n-collapse-item>
								</n-collapse>
							</UbaSection>

							<UbaSection v-if="isAdmin" title="Deploying UBA (admins)">
								<n-collapse :default-expanded-names="[]" arrow-placement="right">
									<n-collapse-item name="deploy">
										<template #header>
											<span class="text-secondary text-xs">
												How to install SOCFortress UBA, create CoPilot's API key for all
												customers, and connect it
											</span>
										</template>
										<UbaDeployGuide />
									</n-collapse-item>
								</n-collapse>
							</UbaSection>
						</div>
					</n-spin>
				</div>
			</n-drawer-content>
		</n-drawer>
	</section>
</template>

<script setup lang="ts">
// For people new to UBA: what it is, how risk adds up (UBA's own numbers, GET /v1/about) and every rule
// in plain words. A slim bar on the page; "Show" opens it all in a drawer, one section under the
// other. Loaded the first time it is opened.
import type { ApiError } from "@/types/common"
import type { UbaAbout } from "@/types/uba"
import { NButton, NCollapse, NCollapseItem, NDrawer, NDrawerContent, NSpin, NTag } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import UbaDeployGuide from "./UbaDeployGuide.vue"
import UbaError from "./UbaError.vue"
import UbaSection from "./ui/UbaSection.vue"

const { customerCode } = defineProps<{ customerCode: string }>()

const GLOSSARY = [
	{ term: "Entity", meaning: "A person (user account), a computer, or an IP address UBA keeps a risk score for." },
	{ term: "Finding", meaning: "One unusual thing a rule noticed, worth some risk points (also called a signal)." },
	{ term: "Risk", meaning: "An entity's points from recent findings, fading over time." },
	{ term: "Alert", meaning: "Raised when an entity's risk crosses the threshold; it lists the findings behind it." },
	{ term: "Native alert", meaning: "An alert from Wazuh itself, counted as context with capped points." },
	{
		term: "Suppression",
		meaning: "A rule muted for one entity for a while: its findings are kept but add no points."
	},
	{ term: "Learning period", meaning: "The days a rule watches to learn what is normal before it can fire." }
]

// Opened from the bar, in a drawer: the page leads with the customer's data, the explainer is one click away.
const open = ref(false)
const isAdmin = computed(() => useAuthStore().isAdmin)
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

<style scoped>
.info-tile {
	color: var(--primary-color);
	background-color: rgb(var(--primary-color-rgb) / 0.1);
}

/* List items marked with a small primary square, aligned to the first line. */
/* The drawer's body: the sections well apart, one under the other. */
:global(.uba-about-body) {
	padding-top: 20px !important;
	padding-bottom: 32px !important;
}

.marked li {
	position: relative;
	padding-left: 14px;
	line-height: 1.55;
}

.marked li::before {
	content: "";
	position: absolute;
	left: 0;
	top: 0.6em;
	width: 5px;
	height: 5px;
	border-radius: 1px;
	background-color: var(--primary-color);
}

.glossary dt {
	font-weight: 600;
}

/* The rules: compact rows on the secondary (slightly darker) surface, hairlines between. */
.rule-item {
	background-color: var(--bg-secondary-color);
	border-bottom: 1px solid var(--border-color);
}

.rule-item:last-child {
	border-bottom: 0;
}

.score {
	padding: 0 5px;
	border-radius: 4px;
	background-color: rgb(var(--primary-color-rgb) / 0.12);
	color: var(--primary-color);
}
</style>
