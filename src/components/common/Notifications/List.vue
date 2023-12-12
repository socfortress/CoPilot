<template>
	<n-scrollbar class="notifications-list">
		<div
			class="item flex"
			v-for="item of listSanitized"
			:key="item.id"
			@click="item.action ? preformAction(item.id, item.action) : () => {}"
			:class="[{ pointer: !!item.action }, item.type]"
		>
			<div class="icon-box">
				<Icon :name="AlertIcon" :size="21" v-if="item.category === 'alert'"></Icon>
				<n-tooltip trigger="hover" style="padding: 0" placement="right" v-if="!item.read">
					<template #trigger>
						<div class="read-badge" @click.stop="setRead(item.id)"></div>
					</template>
					Set as read
				</n-tooltip>
			</div>
			<div class="content grow">
				<div class="title">{{ item.title }}</div>
				<div class="description">{{ item.description }}</div>
				<div class="footer flex justify-between items-center">
					<div class="date">{{ formatDatetime(item.date) }}</div>
					<div class="action-text" v-if="!!item.action">{{ item.actionTitle || "Details" }}</div>
				</div>
			</div>
			<div class="delete-btn" @click.stop="deleteOne(item.id)">
				<Icon :name="DeleteIcon" :size="18"></Icon>
			</div>
		</div>
		<slot name="last"></slot>
	</n-scrollbar>
</template>

<script lang="ts" setup>
import { NScrollbar, NTooltip } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { useNotifications } from "@/composables/useNotifications"
import { computed } from "vue"
import _take from "lodash/take"

const DeleteIcon = "carbon:close"
const AlertIcon = "mdi:alert-outline"

const props = defineProps<{
	maxItems?: number
}>()

const list = useNotifications().list

const listSanitized = computed(() => {
	if (props.maxItems) {
		return _take(list.value, props.maxItems)
	}
	return list.value
})

function preformAction(id: string | number, action: () => void) {
	action()
	setRead(id)
}

function setRead(id: string | number) {
	useNotifications().setRead(id)
}

function deleteOne(id: string | number) {
	useNotifications().deleteOne(id)
}

function formatDatetime(date: Date | string) {
	return useNotifications().formatDatetime(date)
}
</script>

<style lang="scss" scoped>
.notifications-list {
	.item {
		position: relative;
		padding: 14px 0;

		.icon-box {
			width: 70px;
			min-width: 70px;
			display: flex;
			justify-content: center;
			position: relative;

			.n-icon {
				display: flex;
				justify-content: center;
				align-items: center;
				border-radius: 50%;
				width: 42px;
				height: 42px;
				margin-top: 2px;
			}

			.read-badge {
				position: absolute;
				top: 5px;
				left: 14px;
				width: 10px;
				height: 10px;
				border-radius: 50%;
				background-color: var(--primary-color);
				cursor: pointer;
			}
		}

		.content {
			max-width: 250px;
			padding-right: 20px;
			font-size: 14px;

			.title {
				font-weight: bold;
			}

			.footer {
				margin-top: 6px;

				.date {
					font-size: 12px;
					opacity: 0.5;
				}
				.action-text {
					font-size: 12px;
				}
			}
		}

		.delete-btn {
			position: absolute;
			top: 8px;
			right: 8px;
			cursor: pointer;
			opacity: 0;
		}

		&.success {
			.icon-box {
				.n-icon {
					background-color: var(--primary-005-color);
					color: var(--success-color);
				}
			}
			.action-text {
				color: var(--success-color);
			}
		}
		&.info {
			.icon-box {
				.n-icon {
					background-color: var(--secondary1-opacity-010-color);
					color: var(--info-color);
				}
			}
			.action-text {
				color: var(--info-color);
			}
		}
		&.warning {
			.icon-box {
				.n-icon {
					background-color: var(--secondary3-opacity-010-color);
					color: var(--warning-color);
				}
			}
			.action-text {
				color: var(--warning-color);
			}
		}
		&.error {
			.icon-box {
				.n-icon {
					background-color: var(--secondary4-opacity-010-color);
					color: var(--error-color);
				}
			}
			.action-text {
				color: var(--error-color);
			}
		}

		&.pointer {
			cursor: pointer;
		}

		&:not(:last-child) {
			border-bottom: var(--border-small-050);
		}

		&:hover {
			background-color: var(--hover-005-color);

			.delete-btn {
				opacity: 0.5;

				&:hover {
					opacity: 1;
				}
			}
		}
	}
}
</style>
