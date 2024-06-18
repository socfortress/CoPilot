<template>
	<n-tabs type="line" animated :tabs-padding="24" v-if="alert">
		<n-tab-pane name="Context" tab="Context" display-directive="show:lazy">
			<SocAlertItemContext :alert="alert" class="p-7 pt-4" />
		</n-tab-pane>
		<n-tab-pane name="Note" tab="Note" display-directive="show:lazy">
			<div class="p-7 pt-4">
				{{ alert.alert_note ?? "No notes for this alert" }}
			</div>
		</n-tab-pane>
		<n-tab-pane name="Customer" tab="Customer" display-directive="show:lazy">
			<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4">
				<KVCard v-for="(value, key) of alert.customer" :key="key">
					<template #key>{{ key }}</template>
					<template #value>
						<template v-if="key === 'customer_code' && value && value !== 'Customer Not Found'">
							<code
								class="cursor-pointer text-primary-color"
								@click="gotoCustomer({ code: value.toString() })"
							>
								#{{ value }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
						</template>
						<template v-else>
							{{ value || "-" }}
						</template>
					</template>
				</KVCard>
			</div>
		</n-tab-pane>
		<n-tab-pane name="Owner" tab="Owner" display-directive="show:lazy">
			<div class="grid gap-2 px-7 pt-4">
				<Badge type="active" style="max-width: 145px" class="cursor-pointer" @click="gotoSocUsers(ownerId)">
					<template #iconRight>
						<Icon :name="LinkIcon" :size="14"></Icon>
					</template>
					<template #label>Go to users page</template>
				</Badge>
			</div>
			<div class="grid gap-2 grid-auto-flow-200 p-7 pt-4">
				<KVCard>
					<template #key>user_login</template>
					<template #value>
						<SocAssignUser
							:alert="alert"
							:users="users"
							v-slot="{ loading }"
							@updated="emit('updated', $event)"
						>
							<div class="flex items-center gap-2 cursor-pointer text-primary-color">
								<n-spin :size="16" :show="loading">
									<Icon :name="EditIcon" :size="16"></Icon>
								</n-spin>
								<span>{{ ownerName || "Assign a user" }}</span>
							</div>
						</SocAssignUser>
					</template>
				</KVCard>
				<KVCard v-if="alert.owner">
					<template #key>user_name</template>
					<template #value>
						<span>#{{ alert.owner.id }}</span>
						{{ alert.owner.user_name }}
					</template>
				</KVCard>
				<KVCard v-if="alert.owner">
					<template #key>user_email</template>
					<template #value>
						{{ alert.owner.user_email }}
					</template>
				</KVCard>
			</div>
		</n-tab-pane>
		<n-tab-pane name="History" tab="History" display-directive="show:lazy">
			<div class="p-7 pt-4">
				<SocAlertItemTimeline :alert="alert" />
			</div>
		</n-tab-pane>
		<n-tab-pane name="Details" tab="Details" display-directive="show:lazy">
			<div class="p-7 pt-4">
				<SimpleJsonViewer class="vuesjv-override" :model-value="socAlertDetail" :initialExpandedDepth="1" />
			</div>
		</n-tab-pane>
		<n-tab-pane name="Assets" tab="Assets" display-directive="show:lazy">
			<SocAlertAssetsList v-if="alert" :alert-id="alert.alert_id" />
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import type { SocAlert } from "@/types/soc/alert.d"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { computed } from "vue"
import { SimpleJsonViewer } from "vue-sjv"
import KVCard from "@/components/common/KVCard.vue"
import SocAlertItemTimeline from "./SocAlertItemTimeline.vue"
import SocAssignUser from "./SocAssignUser.vue"
import SocAlertItemContext from "./SocAlertItemContext.vue"
import SocAlertAssetsList from "../SocAlertAssets/SocAlertAssetsList.vue"
import "@/assets/scss/vuesjv-override.scss"
import { NTabs, NTabPane, NSpin } from "naive-ui"
import { useGoto } from "@/composables/useGoto"
import type { SocUser } from "@/types/soc/user"

const emit = defineEmits<{
	(e: "updated", value: SocAlert): void
}>()

const { alert } = defineProps<{
	alert: SocAlert
	users?: SocUser[]
}>()

const LinkIcon = "carbon:launch"
const EditIcon = "uil:edit-alt"

const { gotoCustomer, gotoSocUsers } = useGoto()

const ownerName = computed(() => alert?.owner?.user_login)
const ownerId = computed(() => alert?.owner?.id)

const socAlertDetail = computed<Partial<SocAlert>>(() => {
	const clone: Partial<SocAlert> = JSON.parse(JSON.stringify(alert))

	delete clone.alert_context
	delete clone.alert_source_content
	delete clone.customer
	delete clone.modification_history
	delete clone.alert_note
	delete clone.alert_source_link

	return clone
})
</script>
