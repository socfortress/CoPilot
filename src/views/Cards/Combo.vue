<template>
	<div class="page flex flex-col gap-5">
		<div class="card-row flex md:flex-row flex-col gap-5">
			<div class="card-wrap md:basis-1/2 basis-full">
				<CardCombo1 title="Sales" class="h-full">
					<template #icon>
						<CardComboIcon boxed>
							<SalesIcon />
						</CardComboIcon>
					</template>
				</CardCombo1>
			</div>
			<div class="card-wrap md:basis-1/2 basis-full">
				<CardCombo1 title="Subscribers" type="bar" class="h-full" :chartColor="style['--secondary1-color']">
					<template #icon>
						<CardComboIcon boxed :color="style['--secondary1-color']">
							<SubscribersIcon />
						</CardComboIcon>
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
							<CardComboIcon boxed :boxSize="50" :color="'white'">
								<ReportsIcon />
							</CardComboIcon>
						</template>
					</CardCombo2>
				</div>
				<div class="flex lg:basis-1/2 basis-full">
					<div class="flex flex-col gap-5 w-full">
						<CardCombo2 title="Issues" horizontal>
							<template #icon>
								<CardComboIcon boxed :boxSize="50" :color="style['--secondary4-color']">
									<ErrorIcon />
								</CardComboIcon>
							</template>
						</CardCombo2>
						<CardCombo2 title="Completed" horizontal>
							<template #icon>
								<CardComboIcon boxed :boxSize="50">
									<CompletedIcon />
								</CardComboIcon>
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
								<CardComboIcon :boxSize="50" :color="style['--secondary3-color']">
									<PendingIcon />
								</CardComboIcon>
							</template>
						</CardCombo2>
						<CardCombo2 title="Shipped" horizontal>
							<template #icon>
								<CardComboIcon :boxSize="50" :color="style['--secondary1-color']">
									<ShippedIcon />
								</CardComboIcon>
							</template>
						</CardCombo2>
					</div>
				</div>
				<div class="flex lg:basis-1/2 basis-full">
					<CardCombo2 title="Earned" centered class="h-full" currency="USD">
						<template #icon>
							<CardComboIcon :boxSize="50">
								<RevenueIcon />
							</CardComboIcon>
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
							<CardComboIcon boxed :boxSize="30">
								<ComputerIcon />
							</CardComboIcon>
						</template>
						<template #iconRight>
							<CardComboIcon boxed :boxSize="30">
								<TabletIcon />
							</CardComboIcon>
						</template>
					</CardCombo6>

					<CardCombo6 cardWrap showDividerLines hideVersusIcon></CardCombo6>
				</div>
			</div>
			<div class="card-wrap lg:basis-1/2 basis-full flex flex-col gap-5">
				<div class="flex flex-col gap-5 sm:flex-row">
					<CardCombo7 cardWrap>
						<template #icon>
							<CardComboIcon boxed>
								<SalesIcon />
							</CardComboIcon>
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
							<CardComboIcon :color="style['--secondary2-color']">
								<ActivityIcon />
							</CardComboIcon>
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
							<CardComboIcon boxed>
								<UploadsIcon />
							</CardComboIcon>
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
import RevenueIcon from "@vicons/carbon/Money"
import SubscribersIcon from "@vicons/carbon/UserMultiple"
import SalesIcon from "@vicons/carbon/ShoppingCart"
import ReportsIcon from "@vicons/carbon/Report"
import ErrorIcon from "@vicons/carbon/Debug"
import ActivityIcon from "@vicons/carbon/Activity"
import UploadsIcon from "@vicons/carbon/CloudUpload"
import CompletedIcon from "@vicons/carbon/CheckmarkOutline"
import PendingIcon from "@vicons/carbon/Hourglass"
import ShippedIcon from "@vicons/carbon/Send"
import TabletIcon from "@vicons/carbon/Tablet"
import ComputerIcon from "@vicons/carbon/Screen"
import { computed } from "vue"
import { useThemeStore } from "@/stores/theme"

const style: { [key: string]: any } = computed(() => useThemeStore().style)
</script>
