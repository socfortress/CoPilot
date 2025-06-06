<template>
	<CardEntity class="index-card" :loading :class="[`health-${index.health}`]">
		<div class="wrapper">
			<div class="group">
				<div class="box">
					<div class="value">
						{{ index.index }}
					</div>
					<div class="label">name</div>
				</div>
				<div class="box">
					<div class="value align-center flex gap-2 uppercase">
						<IndexIcon :health="index.health" color />
						{{ index.health }}
					</div>
					<div class="label">health</div>
				</div>
			</div>
			<div class="group">
				<div class="box">
					<div class="value">
						{{ index.store_size }}
					</div>
					<div class="label">store_size</div>
				</div>
				<div class="box">
					<div class="value">
						{{ index.docs_count }}
					</div>
					<div class="label">docs_count</div>
				</div>
				<div class="box">
					<div class="value">
						{{ index.replica_count }}
					</div>
					<div class="label">replica_count</div>
				</div>
			</div>
			<div v-if="showActions" class="actions group">
				<div class="box">
					<!--
						<el-tooltip content="Rotate" placement="top" :show-arrow="false">
							<el-button type="primary" :icon="RefreshIcon" circle />
						</el-tooltip>
					-->
					<n-tooltip content="Delete">
						Delete
						<template #trigger>
							<n-button quaternary circle type="error" @click.stop="handleDelete">
								<template #icon>
									<Icon :name="DeleteIcon"></Icon>
								</template>
							</n-button>
						</template>
					</n-tooltip>
				</div>
			</div>
		</div>
	</CardEntity>
</template>

<script setup lang="ts">
import type { IndexStats } from "@/types/indices.d"
import { NButton, NTooltip, useDialog, useMessage } from "naive-ui"
import { h, ref, toRefs } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import IndexIcon from "@/components/indices/IndexIcon.vue"

const props = defineProps<{
	index: IndexStats
	showActions?: boolean
}>()

const emit = defineEmits<{
	(e: "delete"): void
}>()

const DeleteIcon = "ph:trash"

const { index, showActions } = toRefs(props)

const dialog = useDialog()
const message = useMessage()
const loading = ref(false)

function handleDelete() {
	dialog.warning({
		title: "Confirm",
		content: () =>
			h("div", {
				innerHTML: `Are you sure you want to delete the index:<br/><strong>${index.value.index}</strong> ?`
			}),
		positiveText: "Yes I'm sure",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleteIndex()
		},
		onNegativeClick: () => {
			message.info("Delete canceled")
		}
	})
}

function deleteIndex() {
	loading.value = true

	Api.graylog
		.deleteIndex(index.value.index)
		.then(res => {
			if (res.data.success) {
				message.success("Index was successfully deleted.")

				emit("delete")
			} else {
				message.error(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			if (err.response?.status === 401) {
				message.error(
					err.response?.data?.message ||
						"Wazuh-Indexer returned Unauthorized. Please check your connector credentials."
				)
			} else if (err.response?.status === 404) {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			} else {
				message.error(err.response?.data?.message || "An error occurred. Please try again later.")
			}
		})
		.finally(() => {
			loading.value = false
		})
}
</script>

<style lang="scss" scoped>
.index-card {
	.wrapper {
		display: flex;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: calc(var(--spacing) * 6);

		.group {
			display: flex;
			justify-content: space-between;
			gap: calc(var(--spacing) * 6);
			flex-grow: 1;
			flex-wrap: wrap;

			.box {
				flex-grow: 1;

				.value {
					font-weight: bold;
					margin-bottom: 2px;
				}
				.label {
					white-space: nowrap;
					font-size: var(--text-xs);
					font-family: var(--font-family-mono);
					opacity: 0.8;
				}
			}
			&.actions {
				flex-grow: 0;
			}
		}
	}

	&.health-green {
		border-color: var(--success-color);
	}

	&.health-yellow {
		border-color: var(--warning-color);
	}

	&.health-red {
		border-color: var(--error-color);
	}
}
</style>
