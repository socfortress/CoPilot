<template>
	<n-card size="small" title="Customer access" segmented data-testid="profile-customers">
		<template #header-extra>
			<n-tag v-if="scope === 'assigned'" type="info" size="small" :bordered="false" data-testid="profile-customers-count">
				{{ customers.length }} {{ customers.length === 1 ? "customer" : "customers" }}
			</n-tag>
		</template>

		<n-spin :show="loading" class="min-h-16">
			<n-alert v-if="failed" type="error" :bordered="false">Your customers could not be loaded.</n-alert>

			<n-alert v-else-if="scope === 'deployment'" type="info" :bordered="false" data-testid="profile-customers-all">
				As an admin you see every customer.
				<a :href="routeCustomer().href()" class="text-primary ml-1" @click.prevent="routeCustomer().navigate()">
					Browse customers
				</a>
			</n-alert>

			<n-alert
				v-else-if="scope === 'unassigned'"
				type="warning"
				title="No customer assigned"
				:bordered="false"
				data-testid="profile-customers-none"
			>
				You see no customer's data until an admin assigns you at least one.
			</n-alert>

			<div v-else-if="scope === 'assigned'" class="flex flex-col gap-3">
				<p class="text-secondary text-sm">You see the data of these customers only. An admin manages your assignments.</p>
				<ul class="border-default divide-border m-0 list-none divide-y overflow-hidden rounded-lg border p-0">
					<li
						v-for="customer of customers"
						:key="customer.code"
						class="hover:bg-primary/5 flex items-center justify-between gap-4 px-4 py-3"
						:data-testid="`profile-customer-${customer.code}`"
					>
						<div class="flex min-w-0 items-center gap-3">
							<n-avatar
								round
								:size="32"
								:src="customer.logo || avatarOf(customer)"
								:fallback-src="avatarOf(customer)"
								class="shrink-0"
							/>
							<div class="flex min-w-0 flex-col">
								<span class="text-default truncate font-medium" :title="customer.name" data-testid="customer-name">
									{{ customer.name }}
								</span>
								<span class="text-tertiary font-mono text-xs">#{{ customer.code }}</span>
							</div>
							<n-tag v-if="customer.type" size="tiny" :bordered="false" class="shrink-0">{{ customer.type }}</n-tag>
						</div>
						<EntityDetailsButton
							size="tiny"
							:route="routeCustomer({ code: customer.code })"
							@view="openCustomer(customer.code)"
						/>
					</li>
				</ul>
			</div>
		</n-spin>

		<CustomerDetailsModal v-model:show="showDetails" :customer-code="selectedCode" :title="selectedName" />
	</n-card>
</template>

<script setup lang="ts">
import type { Customer } from "@/types/customers"
import { NAlert, NAvatar, NCard, NSpin, NTag } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import EntityDetailsButton from "@/components/common/EntityDetailsButton.vue"
import CustomerDetailsModal from "@/components/customers/CustomerDetailsModal.vue"
import { useNavigation } from "@/composables/useNavigation"
import { getAvatar, getNameInitials } from "@/utils"

/**
 * The signed-in user's customers, from /auth/me/customers: the one route that answers
 * for oneself whatever the role, and says why (assigned; deployment for an admin;
 * unassigned for an analyst or responder nobody has assigned a customer to yet).
 */

type Scope = "assigned" | "deployment" | "unassigned"

interface Row {
	code: string
	name: string
	type: string
	logo: string
}

const { routeCustomer } = useNavigation()
const loading = ref(false)
const failed = ref(false)
const scope = ref<Scope | null>(null)
const assigned = ref<string[]>([])
const details = ref<Record<string, Customer>>({})
const showDetails = ref(false)
const selectedCode = ref<string | null>(null)

const customers = computed<Row[]>(() =>
	assigned.value
		.map(code => ({
			code,
			name: details.value[code]?.customer_name || code,
			type: details.value[code]?.customer_type || "",
			logo: details.value[code]?.logo_file || ""
		}))
		.sort((a, b) => a.name.localeCompare(b.name))
)

const selectedName = computed(() => customers.value.find(c => c.code === selectedCode.value)?.name)

function avatarOf(customer: Row) {
	const initials = getNameInitials(customer.name)
	return getAvatar({ seed: customer.code, text: initials, size: 64 })
}

function openCustomer(code: string) {
	selectedCode.value = code
	showDetails.value = true
}

async function load() {
	loading.value = true
	failed.value = false
	try {
		const res = await Api.auth.getMyCustomerAccess()
		const codes = res.data.customer_codes || []
		const own = codes.filter(code => code !== "*")
		scope.value = res.data.scope ?? (codes.includes("*") ? "deployment" : own.length ? "assigned" : "unassigned")
		assigned.value = own

		// Names, types and logos are a nicety: the list is narrowed to the caller's
		// customers server-side, and the code stands in when it fails.
		if (own.length) {
			try {
				const list = await Api.customers.getCustomers({})
				details.value = Object.fromEntries((list.data.customers || []).map(c => [c.customer_code, c]))
			} catch {
				details.value = {}
			}
		}
	} catch {
		failed.value = true
		scope.value = null
		assigned.value = []
	} finally {
		loading.value = false
	}
}

onBeforeMount(load)
</script>
