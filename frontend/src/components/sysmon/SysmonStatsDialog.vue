<template>
	<n-modal
		:show
		preset="card"
		:style="{ maxWidth: 'min(1100px, 95vw)' }"
		:bordered="false"
		title="Noise statistics shared with SOCFortress"
		segmented
		@update:show="emit('update:show', $event)"
	>
		<div v-if="status" class="flex flex-col gap-3 text-sm" data-testid="stats-dialog">
			<div class="text-secondary flex flex-wrap gap-x-4 gap-y-1 text-xs">
				<span>Week: {{ status.target_week }}</span>
				<span>Only alerts at rule level {{ status.max_rule_level }} or lower</span>
				<span>Patterns on at least {{ status.min_endpoints }} endpoints</span>
				<span class="font-mono">{{ status.service_url }}</span>
			</div>
			<n-data-table
				:columns
				:data="status.customers"
				:row-key="(row: StatsCustomer) => row.customer_code"
				size="small"
				:scroll-x="900"
				:max-height="480"
			/>
		</div>
		<SysmonStatsPreview v-model:show="showPreview" :customer-code="previewCode" />
	</n-modal>
</template>

<script setup lang="ts">
import type { DataTableColumns } from "naive-ui"
import type { StatsCustomer, StatsStatus } from "@/types/sysmon-config"
import { NButton, NDataTable, NInput, NModal, NPopover, NSwitch, NTooltip, useDialog, useMessage } from "naive-ui"
import { h, ref } from "vue"
import Api from "@/api"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import { toggleSharing, weekStateText } from "./statsSharing"
import SysmonStatsPreview from "./SysmonStatsPreview.vue"

const props = defineProps<{ show: boolean; status: StatsStatus | null }>()
const emit = defineEmits<{
	(e: "update:show", value: boolean): void
	(e: "customer", value: StatsCustomer): void
}>()

const dialog = useDialog()
const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const showPreview = ref(false)
const previewCode = ref<string | null>(null)
const saving = ref<string | null>(null)

const fmt = (iso: string) => formatDate(iso, dFormats.datetime) as string

function openPreview(code: string) {
	previewCode.value = code
	showPreview.value = true
}

function setSharing(customer: StatsCustomer, value: boolean) {
	saving.value = customer.customer_code
	toggleSharing(dialog, message, customer, value).then(updated => {
		saving.value = null
		if (updated) emit("customer", updated)
	})
}

// The redaction hints: the installer's InstallDirName when it is not the customer code, and the customer's own domains
const hints = ref<Record<string, { installDir: string; domains: string }>>({})

function hintsFor(customer: StatsCustomer) {
	if (!hints.value[customer.customer_code]) {
		hints.value[customer.customer_code] = {
			installDir: customer.install_dir_name ?? "",
			domains: customer.own_domains.join(", ")
		}
	}
	return hints.value[customer.customer_code]
}

function saveHints(customer: StatsCustomer) {
	const draft = hintsFor(customer)
	const domains = draft.domains
		.split(/[\s,]+/)
		.map(d => d.trim())
		.filter(Boolean)
	saving.value = customer.customer_code
	Api.sysmonConfig
		.setStatsSharing(customer.customer_code, {
			sharing: customer.sharing,
			install_dir_name: draft.installDir.trim() || null,
			own_domains: domains
		})
		.then(res => {
			if (res.data.success) {
				message.success(`Redaction hints saved for ${customer.customer_code}`)
				emit("customer", res.data.customer)
			} else {
				message.error(res.data.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => message.error(getApiErrorMessage(err) || "An error occurred. Please try again later."))
		.finally(() => {
			saving.value = null
		})
}

const columns: DataTableColumns<StatsCustomer> = [
	{
		title: "Customer",
		key: "customer_code",
		render: row => h("span", { class: "font-mono" }, `#${row.customer_code}${row.customer_name ? ` - ${row.customer_name}` : ""}`)
	},
	{
		title: "Pseudonym",
		key: "pseudonym",
		render: row => h("span", { class: "font-mono text-xs break-all" }, row.pseudonym ?? "-")
	},
	{
		title: "Sharing",
		key: "sharing",
		width: 90,
		render: row =>
			h(NSwitch, {
				value: row.sharing,
				loading: saving.value === row.customer_code,
				"data-testid": `stats-dialog-switch-${row.customer_code}`,
				"onUpdate:value": (value: boolean) => setSharing(row, value)
			})
	},
	{
		title: "This week",
		key: "target_week_state",
		render: row =>
			h(
				NTooltip,
				{ disabled: !row.target_week_state?.message },
				{
					trigger: () => h("span", weekStateText(props.status?.target_week ?? null, row.target_week_state, fmt)),
					default: () => row.target_week_state?.message ?? ""
				}
			)
	},
	{
		title: "Last sent",
		key: "last_sent_state",
		render: row => h("span", row.last_sent_state ? weekStateText(row.last_sent_week, row.last_sent_state, fmt) : "-")
	},
	{
		title: "",
		key: "actions",
		width: 180,
		render: row =>
			h("div", { class: "flex gap-2" }, [
				h(NButton, { size: "tiny", secondary: true, onClick: () => openPreview(row.customer_code) }, () => "Preview"),
				h(
					NPopover,
					{ trigger: "click", placement: "left" },
					{
						trigger: () => h(NButton, { size: "tiny", secondary: true }, () => "Advanced"),
						default: () => {
							const draft = hintsFor(row)
							return h("div", { class: "flex w-72 flex-col gap-2 text-xs" }, [
								h("div", "Install folder name (the installer's InstallDirName), when it is not the customer code"),
								h(NInput, {
									size: "small",
									value: draft.installDir,
									placeholder: row.customer_code,
									"onUpdate:value": (v: string) => (draft.installDir = v)
								}),
								h("div", "The customer's own DNS domains: names under them are never sent"),
								h(NInput, {
									size: "small",
									value: draft.domains,
									placeholder: "example.com, corp.example.com",
									"onUpdate:value": (v: string) => (draft.domains = v)
								}),
								h(
									NButton,
									{ size: "small", type: "primary", loading: saving.value === row.customer_code, onClick: () => saveHints(row) },
									() => "Save"
								)
							])
						}
					}
				)
			])
	}
]
</script>
