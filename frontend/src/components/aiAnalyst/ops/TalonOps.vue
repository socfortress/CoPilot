<template>
	<div v-if="!allowed" class="text-secondary py-10 text-center text-sm" data-testid="talon-ops-not-for-role">
		Talon's ops findings aren't available for your role.
	</div>
	<div v-else class="flex flex-col gap-4" data-testid="talon-ops">
		<div class="flex flex-wrap items-start justify-between gap-3">
			<p class="text-secondary max-w-3xl text-sm">
				Talon's ops jobs check the stack on a schedule: endpoints that stopped checking in, log sources that
				went silent. Their findings are for the SOC only.
			</p>
			<a
				:href="OPS_DOCS"
				target="_blank"
				rel="noopener noreferrer"
				class="text-primary inline-flex items-center gap-1 text-xs no-underline hover:underline"
			>
				About Talon's ops jobs
				<Icon name="carbon:launch" :size="11" />
			</a>
		</div>

		<OpsProblem v-if="blocked" :state="jobsProblem!" :retry="false" />
		<template v-else>
			<n-alert
				v-if="jobsProblem"
				type="error"
				:bordered="false"
				:title="jobsProblem.title"
				data-testid="talon-ops-jobs-error"
			>
				<bdi>{{ jobsProblem.text }}</bdi>
			</n-alert>
			<n-alert
				v-else-if="jobsLoaded && !anyEnabled"
				type="info"
				:bordered="false"
				:title="OPS_OFF_TITLE"
				data-testid="talon-ops-off"
			>
				{{ OPS_OFF_TEXT }}
				<a :href="OPS_DOCS" target="_blank" rel="noopener noreferrer" class="text-primary">
					How to turn them on
				</a>
			</n-alert>
			<OpsJobs v-if="jobs.length || jobsLoading" :jobs :loading="jobsLoading" :is-admin @refresh="loadJobs()" />
			<OpsFindings ref="findingsList" :jobs :is-admin @open="open" />
		</template>

		<OpsFindingDetail
			:finding-id="openId"
			:customer-code="openCustomer"
			:titles
			@close="openId = null"
			@changed="finding => findingsList?.replace(finding)"
		/>
	</div>
</template>

<script setup lang="ts">
// The AI Analyst page's Ops tab (only with the "Talon v2" setting on): talon-analyst's ops jobs and
// their findings. Admins, analysts and responders, like the Memory tab; run now and platform
// findings are an admin's (the backend checks both by the database role). Every request goes
// through CoPilot, which sends talon-analyst the signed-in user's identity and checks each finding's
// customer.
//
// States: v2 turned off meanwhile or a Talon without the ops API (the whole tab is the notice), no
// job enabled in Talon ("Ops jobs are off in Talon", with the TALON_OPS_JOBS hint; earlier findings
// still show), a failure loading the jobs (a notice above the findings), and the findings' own.
import type { TalonOpsFailure } from "@/api/endpoints/talonOps"
import type { TalonOpsFinding, TalonOpsJob } from "@/types/talonOps"
import { NAlert } from "naive-ui"
import { getActivePinia } from "pinia"
import { computed, onBeforeUnmount, ref } from "vue"
import Api from "@/api"
import { opsFailure } from "@/api/endpoints/talonOps"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import { OPS_DOCS, OPS_OFF_TEXT, OPS_OFF_TITLE, problemState } from "./ops"
import OpsFindingDetail from "./OpsFindingDetail.vue"
import OpsFindings from "./OpsFindings.vue"
import OpsJobs from "./OpsJobs.vue"
import OpsProblem from "./OpsProblem.vue"

/** A finding to open at once (the notification's link: `/ai-analyst?tab=ops&finding=<id>`). */
const { initialFinding = null } = defineProps<{ initialFinding?: number | null }>()

// The routes answer admins and analysts (a responder is one too).
const allowed = computed(() =>
	getActivePinia() ? useAuthStore().isRoleGranted([AuthUserRole.Admin, AuthUserRole.Analyst]) : false
)
const isAdmin = computed(() => (getActivePinia() ? useAuthStore().isAdmin : false))

const jobs = ref<TalonOpsJob[]>([])
const anyEnabled = ref(false)
const jobsLoaded = ref(false)
const jobsLoading = ref(false)
const jobsFailure = ref<TalonOpsFailure | null>(null)
const findingsList = ref<InstanceType<typeof OpsFindings> | null>(null)
const openId = ref<number | null>(initialFinding)
const openCustomer = ref<string | null>(null)
let controller: AbortController | null = null

const jobsProblem = computed(() => problemState(jobsFailure.value))
// v2 off or an old Talon: nothing else can answer either, so only the notice shows.
const blocked = computed(() => jobsProblem.value !== null && jobsProblem.value.kind !== "error")
const titles = computed(() => Object.fromEntries(jobs.value.map(j => [j.name, j.title])))

async function loadJobs() {
	controller?.abort()
	const own = new AbortController()
	controller = own
	jobsLoading.value = true
	jobsFailure.value = null
	try {
		const { data } = await Api.talonOps.listJobs(own.signal)
		if (controller !== own) return
		jobs.value = data.items
		anyEnabled.value = data.any_enabled
		jobsLoaded.value = true
	} catch (err) {
		if (controller !== own || own.signal.aborted) return
		jobsFailure.value = opsFailure(err)
	} finally {
		if (controller === own) jobsLoading.value = false
	}
}

function open(finding: TalonOpsFinding) {
	openCustomer.value = finding.customer_code
	openId.value = finding.id
}

if (allowed.value) loadJobs()
onBeforeUnmount(() => controller?.abort())
</script>
