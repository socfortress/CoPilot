<template>
	<div class="customer-info @container flex flex-col gap-5">
		<div v-if="editing">
			<CustomerForm :customer lock-code @submitted="submitted">
				<template #additionalActions>
					<n-button @click="editing = false">Close</n-button>
				</template>
			</CustomerForm>
		</div>
		<template v-else>
			<!-- Who the customer is, at a glance; the one everyday action beside it. -->
			<header
				class="border-default flex flex-wrap items-center gap-x-5 gap-y-3 border-b pb-5"
				data-testid="customer-info-header"
			>
				<!-- The same avatar as the customers list: its logo, else one drawn from its initials. -->
				<n-avatar
					:src="customer.logo_file || fallbackAvatar"
					:fallback-src="fallbackAvatar"
					round
					:size="56"
					class="shrink-0"
					:img-props="{ alt: '' }"
					data-testid="customer-info-avatar"
				/>
				<div class="flex min-w-0 grow flex-col gap-2">
					<h2 class="font-display text-default m-0 text-xl leading-tight font-semibold break-words">
						<bdi>{{ customer.customer_name || customer.customer_code }}</bdi>
					</h2>
					<div class="flex flex-wrap items-center gap-2">
						<span
							class="border-default text-secondary rounded-md border px-1.5 py-0.5 font-mono text-xs"
							title="Customer code"
							data-testid="customer-info-code"
						>
							<bdi>{{ customer.customer_code }}</bdi>
						</span>
						<span
							v-if="customer.customer_type"
							class="bg-secondary text-secondary rounded-md px-1.5 py-0.5 font-mono text-[10px] tracking-[0.12em] uppercase"
							data-testid="customer-info-type"
						>
							{{ customer.customer_type }}
						</span>
						<span
							class="flex items-center gap-1.5 text-xs"
							:class="customer.is_provisioned ? 'text-success' : 'text-tertiary'"
							data-testid="customer-info-provisioned"
						>
							<span
								class="size-1.5 rounded-full"
								:class="customer.is_provisioned ? 'bg-success' : 'bg-current'"
							></span>
							{{ customer.is_provisioned ? "Provisioned" : "Not provisioned" }}
						</span>
					</div>
				</div>
				<n-button :disabled="loadingDelete" data-testid="customer-info-edit" @click="editing = true">
					<template #icon>
						<Icon :name="EditIcon" :size="15" />
					</template>
					Edit
				</n-button>
			</header>

			<div class="grid gap-5 @2xl:grid-cols-2">
				<section
					v-for="section of sections"
					:key="section.title"
					class="flex flex-col gap-3"
					:class="{ '@2xl:col-span-2': section.wide }"
					:data-testid="`customer-info-${section.key}`"
				>
					<h3
						class="text-tertiary m-0 flex items-center gap-2 font-mono text-[10px] font-normal tracking-[0.14em] uppercase"
					>
						<Icon :name="section.icon" :size="13" />
						{{ section.title }}
						<span class="border-default grow border-t"></span>
					</h3>
					<dl class="m-0 grid gap-x-6 gap-y-3" :class="{ '@2xl:grid-cols-2': section.wide }">
						<div v-for="row of section.rows" :key="row.label" class="flex min-w-0 flex-col gap-0.5">
							<dt class="text-secondary text-xs">{{ row.label }}</dt>
							<dd
								class="m-0 text-sm break-words whitespace-pre-line"
								:class="[
									row.value ? 'text-default' : 'text-tertiary',
									{ 'font-mono': row.mono && row.value }
								]"
							>
								<bdi>{{ row.value || "Not set" }}</bdi>
							</dd>
						</div>
					</dl>
				</section>
			</div>

			<!-- Deleting is rare and final: apart from the everyday actions, and says what it costs. -->
			<section
				class="border-error/30 bg-error/5 mt-1 flex flex-wrap items-center justify-between gap-x-6 gap-y-3 rounded-lg border px-4 py-3"
				data-testid="customer-info-danger"
			>
				<div class="flex min-w-0 flex-col gap-0.5">
					<span class="text-default text-sm font-medium">Delete customer</span>
					<span class="text-secondary text-xs">
						Removes
						<bdi class="text-default">{{ customer.customer_name || customer.customer_code }}</bdi>
						<span>{{ " from CoPilot. This cannot be undone." }}</span>
					</span>
				</div>
				<n-button
					type="error"
					ghost
					:loading="loadingDelete"
					data-testid="customer-info-delete"
					@click="handleDelete"
				>
					<template #icon>
						<Icon :name="DeleteIcon" :size="15" />
					</template>
					Delete customer
				</n-button>
			</section>
		</template>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import { NAvatar, NButton, useDialog, useMessage } from "naive-ui"
import { computed, h, ref, toRefs, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage, getAvatar, getNameInitials } from "@/utils"
import CustomerForm from "./CustomerForm.vue"

const props = defineProps<{
	customer: Customer
}>()

const emit = defineEmits<{
	(e: "update:loading", value: boolean): void
	(e: "delete"): void
	(e: "submitted", value: Customer): void
}>()

const { customer } = toRefs(props)

const EditIcon = "uil:edit-alt"
const DeleteIcon = "ph:trash"

const loadingDelete = ref(false)
const editing = ref(false)
const dialog = useDialog()
const message = useMessage()

const fallbackAvatar = computed(() => {
	const initials = getNameInitials(customer.value.customer_name)
	return getAvatar({ seed: initials, text: initials })
})

interface InfoRow {
	label: string
	value: string
	mono?: boolean
}

/** The customer's fields, grouped by what they are for, every field shown once. */
const sections = computed(() => {
	const c = customer.value
	const contact = [c.contact_first_name, c.contact_last_name].filter(Boolean).join(" ")
	const cityLine = [c.postal_code, c.city].filter(Boolean).join(" ")
	const regionLine = [c.state, c.country].filter(Boolean).join(", ")
	const address = [c.address_line1, c.address_line2, cityLine, regionLine].filter(Boolean).join("\n")
	return [
		{
			key: "contact",
			title: "Contact",
			icon: "carbon:user-profile",
			rows: [
				{ label: "Contact person", value: contact },
				{ label: "Phone", value: c.phone, mono: true }
			] as InfoRow[]
		},
		{
			key: "organization",
			title: "Organization",
			icon: "carbon:enterprise",
			rows: [
				{ label: "Parent customer", value: c.parent_customer_code ?? "", mono: true },
				{ label: "Logo file", value: c.logo_file, mono: true }
			] as InfoRow[]
		},
		{
			key: "address",
			title: "Address",
			icon: "carbon:location",
			wide: true,
			rows: [{ label: "Postal address", value: address }] as InfoRow[]
		}
	]
})

function submitted(newData: Customer) {
	emit("submitted", newData)
	editing.value = false
}

function deleteCustomer() {
	loadingDelete.value = true

	Api.customers
		.deleteCustomer(customer.value.customer_code)
		.then(res => {
			if (res.data.success) {
				emit("delete")
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loadingDelete.value = false
		})
}

function handleDelete() {
	dialog.warning({
		title: "Delete customer?",
		// Built from nodes, never HTML: the code is data.
		content: () =>
			h("div", [
				"This removes ",
				h("strong", customer.value.customer_name || customer.value.customer_code),
				" (",
				h("code", customer.value.customer_code),
				") from CoPilot. This cannot be undone."
			]),
		positiveText: "Delete customer",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteCustomer()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

watch(loadingDelete, val => {
	emit("update:loading", val)
})
</script>
