<template>
	<div class="flex flex-col gap-4" data-testid="talon-automation-settings">
		<n-alert
			v-if="failure"
			type="error"
			:bordered="false"
			size="small"
			data-testid="talon-automation-settings-error"
		>
			{{ failure.detail }}
		</n-alert>

		<n-spin :show="loading">
			<n-card size="small">
				<div class="flex flex-wrap items-center justify-between gap-4">
					<div class="flex flex-col gap-1">
						<div class="font-semibold">AI Analyst automation</div>
						<div class="text-secondary text-sm" data-testid="talon-automation-settings-state">
							{{
								enabled
									? "Automatic investigations may run what each customer's automation policy allows."
									: "Off: no automated action starts for any customer, whatever their policies say."
							}}
						</div>
					</div>
					<n-switch
						:value="enabled"
						:disabled="loading || saving || settings === null"
						:loading="saving"
						data-testid="talon-automation-switch"
						@update:value="save"
					/>
				</div>
			</n-card>
		</n-spin>

		<p class="text-secondary text-xs">
			This is the global kill switch. Each customer's levels and modes are set on the customer's AI Automation
			tab, where every level is off until an admin sets it. Turning this off stops a running investigation's next
			automated start.
		</p>
	</div>
</template>

<script setup lang="ts">
// The AI Analyst page's Settings tab (admins only, with "Talon v2" on, D54): the global
// `automation_enabled` switch on the Talon connector's settings (talon-analyst D85, plan AP-2;
// CoPilot's `GET`/`PUT /api/talon/v2/settings/automation`).
import type { TalonAutomationSettings } from "@/api/endpoints/talonAutomation"
import type { TalonFailure } from "@/api/endpoints/talonUsage"
import { NAlert, NCard, NSpin, NSwitch, useMessage } from "naive-ui"
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import Api from "@/api"
import { talonFailure } from "@/api/endpoints/talonUsage"

const message = useMessage()

const loading = ref(false)
const saving = ref(false)
const failure = ref<TalonFailure | null>(null)
const settings = ref<TalonAutomationSettings | null>(null)
const enabled = computed(() => settings.value?.automation_enabled === true)

const controller = new AbortController()

async function load() {
	loading.value = true
	failure.value = null
	try {
		const res = await Api.talonAutomation.getSettings(controller.signal)
		settings.value = res.data
	} catch (err) {
		if (!controller.signal.aborted) failure.value = talonFailure(err)
	} finally {
		loading.value = false
	}
}

async function save(value: boolean) {
	saving.value = true
	failure.value = null
	try {
		const res = await Api.talonAutomation.putSettings(value)
		settings.value = res.data
		message.success(value ? "Automation turned on" : "Automation turned off")
	} catch (err) {
		failure.value = talonFailure(err)
	} finally {
		saving.value = false
	}
}

onMounted(load)
onBeforeUnmount(() => controller.abort())
</script>
