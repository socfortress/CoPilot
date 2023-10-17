<template>
	<n-table>
		<thead>
			<tr>
				<th>Product</th>
				<th>Price</th>
				<th v-if="showDate">Date</th>
				<th>Stock</th>
				<th class="!text-right">Orders</th>
				<th class="!text-right" v-if="showActions">Actions</th>
			</tr>
		</thead>
		<tbody>
			<tr v-for="item of list" :key="item.id">
				<td>
					<div class="product flex items-center">
						<div class="product-image flex items-center mr-3">
							<n-image lazy :src="item.photo" :width="50" :height="50" />
						</div>
						<div class="product-info">
							<div class="product-name">
								{{ item.name }}
							</div>
							<div class="product-category">
								{{ item.category }}
							</div>
						</div>
					</div>
				</td>
				<td>
					<div class="price">
						{{ item.price }}
					</div>
				</td>
				<td v-if="showDate">
					<div class="date">
						{{ item.date }}
					</div>
				</td>
				<td>
					<div class="stock">
						<n-tag :type="item.stock.type">
							{{ item.stock.name }}
						</n-tag>
					</div>
				</td>
				<td>
					<div class="orders flex items-center justify-end">
						<div class="orders-value mr-3">
							{{ item.orders }}
						</div>
						<div class="orders-percentage flex items-center">
							<n-progress
								type="circle"
								:percentage="item.percentage"
								:show-indicator="false"
								:stroke-width="18"
								style="width: 22px"
							/>
						</div>
					</div>
				</td>
				<td v-if="showActions">
					<div class="actions flex items-center justify-end gap-2">
						<n-button secondary>
							<template #icon>
								<Icon :name="DeleteIcon"></Icon>
							</template>
						</n-button>
						<n-button secondary>
							<template #icon>
								<Icon :name="DownloadIcon"></Icon>
							</template>
						</n-button>
						<n-popselect
							:options="[
								{ label: 'Share', value: 'Share' },
								{ label: 'View', value: 'View' }
							]"
						>
							<n-button secondary>
								<template #icon>
									<Icon :name="MenuIcon"></Icon>
								</template>
							</n-button>
						</n-popselect>
					</div>
				</td>
			</tr>
		</tbody>
	</n-table>
</template>

<script lang="ts" setup>
import { NTable, NImage, NProgress, NTag, NButton, NPopselect } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

const DeleteIcon = "carbon:delete"
const MenuIcon = "carbon:overflow-menu-vertical"
const DownloadIcon = "carbon:cloud-download"

import dayjs from "@/utils/dayjs"
import { faker } from "@faker-js/faker"
import { ref, toRefs } from "vue"
import _orderBy from "lodash/orderBy"

const props = withDefaults(
	defineProps<{
		rows?: number
		showActions?: boolean
		showDate?: boolean
	}>(),
	{ rows: 5, showActions: false, showDate: false }
)
const { rows, showActions, showDate } = toRefs(props)

const stock = [
	{
		name: "In stock",
		type: "success"
	},
	{
		name: "Out stock",
		type: "error"
	},
	{
		name: "Only 30",
		type: "warning"
	}
] as { name: string; type: "success" | "error" | "warning" }[]

const data = new Array(rows.value).fill(null).map(() => ({
	id: faker.string.nanoid(),
	name: faker.commerce.productName(),
	category: faker.commerce.product(),
	photo: faker.image.urlPicsumPhotos({ width: 240, height: 240 }),
	price: faker.commerce.price({ symbol: "$" }),
	stock: faker.helpers.arrayElement(stock),
	orders: faker.number.int({ min: 13, max: 1836 }),
	percentage: faker.number.int({ min: 0, max: 100 }),
	date: dayjs(faker.date.between({ from: dayjs().subtract(2, "w").toDate(), to: dayjs().toDate() })).format(
		"DD MMM YYYY"
	)
}))

const list = ref(_orderBy(data, ["date"], ["desc"]))
</script>

<style scoped lang="scss">
.product {
	.product-image {
		.n-image {
			:deep(img) {
				border-radius: var(--border-radius-small);
			}
		}
	}

	.product-info {
		.product-name {
			font-weight: 500;
			font-size: 16px;
			line-height: 1.2;
		}
		.product-category {
			opacity: 0.6;
		}
	}
}

.price {
	white-space: nowrap;
}

.orders {
	text-align: right;
	.orders-value {
		white-space: nowrap;
	}
}
</style>
