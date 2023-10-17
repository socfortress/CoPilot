<template>
	<n-scrollbar class="notifications-list">
		<div
			class="item flex"
			v-for="item of listSanitized"
			:key="item.id"
			@click="item.action ? item.action() : () => {}"
			:class="{ pointer: !!item.action }"
		>
			<div class="icon-box" :class="item.type">
				<Icon :name="MessageIcon" :size="21" v-if="item.type === 'message'"></Icon>
				<Icon :name="CalendarIcon" :size="21" v-else-if="item.type === 'reminder'"></Icon>
				<Icon :name="NewsIcon" :size="21" v-else-if="item.type === 'news'"></Icon>
				<Icon :name="AlertIcon" :size="21" v-else-if="item.type === 'alert'"></Icon>
			</div>
			<div class="content grow">
				<div class="title">{{ item.title }}</div>
				<div class="description">{{ item.description }}</div>
				<div class="date">{{ item.date }}</div>
			</div>
			<div class="read-badge" v-if="!item.read"></div>
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

const MessageIcon = "carbon:email"
const CalendarIcon = "carbon:calendar"
const NewsIcon = "fluent:news-24-regular"
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
				background-color: var(--primary-005-color);
				color: var(--primary-color);
				border-radius: 50%;
				width: 42px;
				height: 42px;
				margin-top: 2px;
			}

			&.message {
				.n-icon {
					background-color: var(--secondary1-opacity-010-color);
					color: var(--secondary1-color);
				}
			}
			&.reminder {
				.n-icon {
					background-color: var(--secondary2-opacity-010-color);
					color: var(--secondary2-color);
				}
			}
			&.news {
				.n-icon {
					background-color: var(--secondary3-opacity-010-color);
					color: var(--secondary3-color);
				}
			}
			&.alert {
				.n-icon {
					background-color: var(--secondary4-opacity-010-color);
					color: var(--secondary4-color);
				}
			}
		}
		.content {
			max-width: 250px;
			padding-right: 20px;
			font-size: 14px;

			.title {
				font-weight: bold;
			}
			.date {
				font-size: 12px;
				margin-top: 6px;
				opacity: 0.5;
			}
		}

		.read-badge {
			position: absolute;
			top: 0;
			left: 0;
			width: 0;
			height: 0;
			border-style: solid;
			border-width: 20px 20px 0 0;
			border-color: var(--primary-050-color) transparent transparent transparent;
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
