<template>
	<n-scrollbar class="notifications-list">
		<div
			class="item flex"
			v-for="item of listSanitized"
			:key="item.id"
			@click="item.action ? item.action() : () => {}"
			:class="[{ pointer: !!item.action }, item.type]"
		>
			<div class="icon-box">
				<Icon :name="AlertIcon" :size="21" v-if="item.category === 'alert'"></Icon>
			</div>
			<div class="content grow">
				<div class="title">{{ item.title }}</div>
				<div class="description">{{ item.description }}</div>
				<div class="footer flex justify-between items-center">
					<div class="date">{{ formatDatetime(item.date) }}</div>
					<div class="action-text" v-if="!!item.action">{{ item.actionTitle || "Details" }}</div>
				</div>
			</div>
			<div class="read-badge" v-if="!item.read" @click.stop="setRead(item.id)"></div>
		</div>
		<slot name="last"></slot>
	</n-scrollbar>
</template>

<script lang="ts" setup>
import { NScrollbar } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { useNotifications } from "@/composables/useNotifications"
import { computed } from "vue"
import _take from "lodash/take"

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

function setRead(id: string | number) {
	useNotifications().setRead(id)
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

			.n-icon {
				display: flex;
				justify-content: center;
				align-items: center;
				border-radius: 50%;
				width: 42px;
				height: 42px;
				margin-top: 2px;
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

		.read-badge {
			position: absolute;
			top: 14px;
			right: 14px;
			width: 10px;
			height: 10px;
			border-radius: 50%;
			background-color: var(--primary-color);
			cursor: pointer;
		}

		&.success {
			.n-icon {
				background-color: var(--primary-005-color);
				color: var(--success-color);
			}
			.action-text {
				color: var(--success-color);
			}
		}
		&.info {
			.n-icon {
				background-color: var(--secondary1-opacity-010-color);
				color: var(--info-color);
			}
			.action-text {
				color: var(--info-color);
			}
		}
		&.warning {
			.n-icon {
				background-color: var(--secondary3-opacity-010-color);
				color: var(--warning-color);
			}
			.action-text {
				color: var(--warning-color);
			}
		}
		&.error {
			.n-icon {
				background-color: var(--secondary4-opacity-010-color);
				color: var(--error-color);
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
		}
	}
}
</style>
