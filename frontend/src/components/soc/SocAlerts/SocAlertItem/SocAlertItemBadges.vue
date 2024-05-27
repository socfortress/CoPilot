<template>
	<div class="flex flex-wrap items-center gap-3 mt-3">
		<n-tooltip placement="top-start" trigger="hover">
			<template #trigger>
				<Badge type="splitted" hint-cursor>
					<template #iconLeft>
						<Icon :name="StatusIcon" :size="14"></Icon>
					</template>
					<template #label>Status</template>
					<template #value>{{ alert.status?.status_name || "-" }}</template>
				</Badge>
			</template>
			{{ alert.status.status_description }}
		</n-tooltip>
		<Badge type="splitted" :color="alert.severity?.severity_id === 5 ? 'danger' : undefined">
			<template #iconLeft>
				<Icon :name="SeverityIcon" :size="13"></Icon>
			</template>
			<template #label>Severity</template>
			<template #value>{{ alert.severity?.severity_name || "-" }}</template>
		</Badge>
		<Badge type="splitted" class="hide-on-small">
			<template #iconLeft>
				<Icon :name="SourceIcon" :size="13"></Icon>
			</template>
			<template #label>Source</template>
			<template #value>{{ alert.alert_source || "-" }}</template>
		</Badge>
		<Badge type="splitted" class="hide-on-small">
			<template #iconLeft>
				<Icon :name="CustomerIcon" :size="13"></Icon>
			</template>
			<template #label>Customer</template>
			<template #value>
				<template v-if="alert.customer?.customer_code && alert.customer.customer_code !== 'Customer Not Found'">
					<code
						class="cursor-pointer text-primary-color"
						@click="gotoCustomer({ code: alert.customer.customer_code })"
					>
						{{ alert.customer?.customer_name || alert.customer.customer_code || "-" }}
						<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
					</code>
				</template>
				<template v-else>
					{{ alert.customer?.customer_name || "-" }}
				</template>
			</template>
		</Badge>

		<SocAssignUser :alert="alert" :users="users" v-slot="{ loading }" @updated="emit('updated', $event)">
			<Badge type="active" class="cursor-pointer">
				<template #iconLeft>
					<n-spin :size="16" :show="loading">
						<Icon :name="OwnerIcon" :size="16"></Icon>
					</n-spin>
				</template>
				<template #label>Owner</template>
				<template #value>{{ ownerName || "n/d" }}</template>
			</Badge>
		</SocAssignUser>

		<Badge
			v-if="alert.alert_source_link"
			type="active"
			:href="alert.alert_source_link"
			target="_blank"
			alt="Source link"
			rel="nofollow noopener noreferrer"
		>
			<template #iconRight>
				<Icon :name="LinkIcon" :size="14"></Icon>
			</template>
			<template #label>Source link</template>
		</Badge>
	</div>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert.d"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { computed, toRefs } from "vue"
import SocAssignUser from "./SocAssignUser.vue"
import { NSpin, NTooltip } from "naive-ui"
import type { SocUser } from "@/types/soc/user.d"
import { useGoto } from "@/composables/useGoto"

const emit = defineEmits<{
	(e: "updated", value: SocAlert): void
}>()

const props = defineProps<{
	alert: SocAlert
	users?: SocUser[]
}>()
const { alert, users } = toRefs(props)

const LinkIcon = "carbon:launch"
const StatusIcon = "fluent:status-20-regular"
const SeverityIcon = "bi:shield-exclamation"
const SourceIcon = "lucide:arrow-down-right-from-circle"
const CustomerIcon = "carbon:user"
const OwnerIcon = "carbon:user-military"

const { gotoCustomer } = useGoto()

const ownerName = computed(() => alert.value?.owner?.user_login)
</script>
