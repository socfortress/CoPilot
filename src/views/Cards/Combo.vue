<template>
	<div class="page flex flex-col gap-5">
		<div class="card-row flex md:flex-row flex-col gap-5">
			<div class="card-wrap md:basis-1/2 basis-full">
				<CardCombo1 title="Sales" class="h-full">
					<template #icon>
						<CardComboIcon :iconName="SalesIcon" boxed></CardComboIcon>
					</template>
				</CardCombo1>
			</div>
			<div class="card-wrap md:basis-1/2 basis-full">
				<CardCombo1 title="Subscribers" type="bar" class="h-full" :chartColor="style['--secondary1-color']">
					<template #icon>
						<CardComboIcon
							:iconName="SubscribersIcon"
							boxed
							:color="style['--secondary1-color']"
						></CardComboIcon>
					</template>
				</CardCombo1>
			</div>
		</div>
		<div class="card-row flex lg:flex-row flex-col gap-5">
			<div class="card-wrap lg:basis-1/2 basis-full flex xs:flex-row flex-col gap-5">
				<div class="flex lg:basis-1/2 basis-full">
					<CardCombo2
						title="Reports"
						centered
						class="h-full !text-white"
						:style="`background-color: ${style['--secondary2-color']}`"
					>
						<template #icon>
							<CardComboIcon :iconName="ReportsIcon" boxed :boxSize="50" :color="'white'"></CardComboIcon>
						</template>
					</CardCombo2>
				</div>
				<div class="flex lg:basis-1/2 basis-full">
					<div class="flex flex-col gap-5 w-full">
						<CardCombo2 title="Issues" horizontal>
							<template #icon>
								<CardComboIcon
									:iconName="ErrorIcon"
									boxed
									:boxSize="50"
									:color="style['--secondary4-color']"
								></CardComboIcon>
							</template>
						</CardCombo2>
						<CardCombo2 title="Completed" horizontal>
							<template #icon>
								<CardComboIcon :iconName="CompletedIcon" boxed :boxSize="50"></CardComboIcon>
							</template>
						</CardCombo2>
					</div>
				</div>
			</div>
			<div class="card-wrap lg:basis-1/2 basis-full flex xs:flex-row flex-col gap-5">
				<div class="flex lg:basis-1/2 basis-full">
					<div class="flex flex-col gap-5 w-full">
						<CardCombo2 title="Pending" horizontal>
							<template #icon>
								<CardComboIcon
									:iconName="PendingIcon"
									:boxSize="50"
									:color="style['--secondary3-color']"
								></CardComboIcon>
							</template>
						</CardCombo2>
						<CardCombo2 title="Shipped" horizontal>
							<template #icon>
								<CardComboIcon
									:iconName="ShippedIcon"
									:boxSize="50"
									:color="style['--secondary1-color']"
								></CardComboIcon>
							</template>
						</CardCombo2>
					</div>
				</div>
				<div class="flex lg:basis-1/2 basis-full">
					<CardCombo2 title="Earned" centered class="h-full" currency="USD">
						<template #icon>
							<CardComboIcon :iconName="RevenueIcon" :boxSize="50"></CardComboIcon>
						</template>
					</CardCombo2>
				</div>
			</div>
		</div>
		<div class="card-row flex lg:flex-row flex-col gap-5">
			<div class="card-wrap lg:basis-1/2 basis-full flex flex-col gap-5">
				<CardCombo3 class="grow"></CardCombo3>

				<CardCombo8 />

				<div class="flex flex-col gap-5 md:flex-row lg:flex-col xl:flex-row">
					<CardCombo6 cardWrap titleLeft="Computer" titleRight="Tablet" valueLeft="75.6k" valueRight="143.7k">
						<template #iconLeft>
							<CardComboIcon :iconName="ComputerIcon" boxed :boxSize="30"></CardComboIcon>
						</template>
						<template #iconRight>
							<CardComboIcon :iconName="TabletIcon" boxed :boxSize="30"></CardComboIcon>
						</template>
					</CardCombo6>

					<CardCombo6 cardWrap showDividerLines hideVersusIcon></CardCombo6>
				</div>
			</div>
			<div class="card-wrap lg:basis-1/2 basis-full flex flex-col gap-5">
				<div class="flex flex-col gap-5 sm:flex-row">
					<CardCombo7 cardWrap>
						<template #icon>
							<CardComboIcon :iconName="SalesIcon" boxed></CardComboIcon>
						</template>
					</CardCombo7>

					<CardCombo4
						title="Activities"
						cardWrap
						vertical
						valString="32.9K"
						percentage
						:percentageProps="{
							value: 2.45,
							direction: 'up'
						}"
					>
						<template #icon>
							<CardComboIcon
								:iconName="ActivityIcon"
								:color="style['--secondary2-color']"
							></CardComboIcon>
						</template>
					</CardCombo4>
				</div>

				<CardCombo5></CardCombo5>

				<div class="flex flex-col gap-5 sm:flex-row">
					<CardCombo4
						title="Uploaded"
						valString="137.5 GB"
						cardWrap
						percentage
						:percentageProps="{
							value: 1.96,
							direction: 'down'
						}"
					>
						<template #icon>
							<CardComboIcon :iconName="UploadsIcon" boxed></CardComboIcon>
						</template>
					</CardCombo4>

					<CardCombo4
						title="Users"
						cardWrap
						valString="248.3K"
						percentage
						:percentageProps="{
							value: 2.45,
							direction: 'up'
						}"
					></CardCombo4>
				</div>

				<div class="flex flex-col gap-5 md:flex-row lg:flex-col xl:flex-row">
					<CardCombo7 cardWrap hideHeader></CardCombo7>

					<CardCombo7 cardWrap showPercentage hideInfo></CardCombo7>
				</div>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
const RevenueIcon = "carbon:money"
const SubscribersIcon = "carbon:user-multiple"
const SalesIcon = "carbon:shopping-cart"
const ReportsIcon = "carbon:report"
const ErrorIcon = "carbon:debug"
const ActivityIcon = "carbon:activity"
const UploadsIcon = "carbon:cloud-upload"
const CompletedIcon = "carbon:checkmark-outline"
const PendingIcon = "carbon:hourglass"
const ShippedIcon = "carbon:send"
const TabletIcon = "carbon:tablet"
const ComputerIcon = "carbon:screen"
import { computed } from "vue"
import { useThemeStore } from "@/stores/theme"

const style = computed<{ [key: string]: any }>(() => useThemeStore().style)
</script>
