<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Icons</div>
		</div>
		<div class="main">
			<strong>Pinx</strong>
			uses the
			<a href="https://www.xicons.org/#/" target="_blank" alt="docs" rel="nofollow noopener noreferrer">xicons</a>
			library which gives the possibility to integrate, with the use of the NIcon component, many icon sets. Here
			are some examples:

			<div class="groups grid gap-5 mt-8">
				<n-card class="group" title="Carbon">
					<div class="list">
						<div v-for="icon of Carbon" :key="icon.name" class="icon-box">
							<n-icon :size="20">
								<component :is="icon.name" />
							</n-icon>
						</div>
					</div>
					<template #footer>
						<div class="flex justify-end">
							<n-button
								tag="a"
								href="https://www.xicons.org/#/"
								target="_blank"
								type="primary"
								alt="docs"
							>
								See more
							</n-button>
						</div>
					</template>
				</n-card>

				<n-card class="group" title="Tabler">
					<div class="list">
						<div v-for="icon of Tabler" :key="icon.name" class="icon-box">
							<n-icon :size="20">
								<component :is="icon.name" />
							</n-icon>
						</div>
					</div>
					<template #footer>
						<div class="flex justify-end">
							<n-button
								tag="a"
								href="https://www.xicons.org/#/"
								target="_blank"
								type="primary"
								alt="docs"
							>
								See more
							</n-button>
						</div>
					</template>
				</n-card>

				<n-card class="group" title="Font Awesome">
					<div class="list">
						<div v-for="icon of Fa" :key="icon.name" class="icon-box">
							<n-icon :size="20">
								<component :is="icon.name" />
							</n-icon>
						</div>
					</div>
					<template #footer>
						<div class="flex justify-end">
							<n-button
								tag="a"
								href="https://www.xicons.org/#/"
								target="_blank"
								type="primary"
								alt="docs"
							>
								See more
							</n-button>
						</div>
					</template>
				</n-card>

				<n-card class="group" title="Fluent">
					<div class="list">
						<div v-for="icon of Fluent" :key="icon.name" class="icon-box">
							<n-icon :size="20">
								<component :is="icon.name" />
							</n-icon>
						</div>
					</div>
					<template #footer>
						<div class="flex justify-end">
							<n-button
								tag="a"
								href="https://www.xicons.org/#/"
								target="_blank"
								type="primary"
								alt="docs"
							>
								See more
							</n-button>
						</div>
					</template>
				</n-card>

				<n-card class="group" title="Ionicons 5">
					<div class="list">
						<div v-for="icon of Ionicons5" :key="icon.name" class="icon-box">
							<n-icon :size="20">
								<component :is="icon.name" />
							</n-icon>
						</div>
					</div>
					<template #footer>
						<div class="flex justify-end">
							<n-button
								tag="a"
								href="https://www.xicons.org/#/"
								target="_blank"
								type="primary"
								alt="docs"
							>
								See more
							</n-button>
						</div>
					</template>
				</n-card>

				<n-card class="group" title="Material">
					<div class="list">
						<div v-for="icon of Material" :key="icon.name" class="icon-box">
							<n-icon :size="20">
								<component :is="icon.name" />
							</n-icon>
						</div>
					</div>
					<template #footer>
						<div class="flex justify-end">
							<n-button
								tag="a"
								href="https://www.xicons.org/#/"
								target="_blank"
								type="primary"
								alt="docs"
							>
								See more
							</n-button>
						</div>
					</template>
				</n-card>
			</div>
		</div>
	</div>
</template>

<script lang="ts">
import { NIcon, NCard, NButton } from "naive-ui"
import Carbon from "./icons-set/carbon"
import Fa from "./icons-set/fa"
import Fluent from "./icons-set/fluent"
import Ionicons5 from "./icons-set/ionicons5"
import Material from "./icons-set/material"
import Tabler from "./icons-set/tabler"
import {
	StringInteger,
	DocumentWordProcessorReference,
	CategoryNewEach,
	WarningAlt,
	Stethoscope,
	KeepDry,
	NoImage,
	GroupObjects,
	Information,
	Warning,
	AccessibilityAlt,
	VirtualColumnKey,
	OpenPanelFilledRight,
	DataBase,
	AlignVerticalTop,
	ConnectionSignal,
	ConnectionSend,
	PhoneIncomingFilled,
	TemperatureFahrenheitAlt,
	PhoneVoice,
	Network1,
	WintryMix,
	PlayFilled,
	MicrophoneOffFilled,
	FilterRemove,
	Moonset,
	AlignBoxMiddleRight,
	TaskTools,
	FaceWinkFilled,
	AlignBoxMiddleCenter
} from "@vicons/carbon"
import {
	SortAlphaDown,
	Chrome,
	Envira,
	Shopware,
	Snapchat,
	CommentAlt,
	RedditAlien,
	Comment,
	Mailchimp,
	Bone,
	Quran,
	Download,
	Draft2Digital,
	Blackberry,
	Digg,
	Film,
	IdBadgeRegular,
	FileMedicalAlt,
	SortAlphaUpAlt,
	CodeBranch,
	MehRegular,
	DiceThree,
	Beer,
	Js,
	CottonBureau,
	CreativeCommonsShare,
	Vest,
	DiceFive,
	StoreAltSlash,
	Unlink
} from "@vicons/fa"
import {
	ChevronUp24Filled,
	SquareMultiple20Regular,
	PresenceUnknown10Regular,
	Gift20Regular,
	CheckmarkUnderlineCircle20Filled,
	ArrowFit16Regular,
	Fingerprint24Filled,
	TextClearFormatting16Regular,
	ReadingListAdd16Regular,
	DrinkCoffee20Filled,
	FolderLink20Filled,
	History24Filled,
	DataBarHorizontal20Regular,
	News28Regular,
	BookLetter24Filled,
	SportHockey24Regular,
	Oval32Regular,
	ArrowUpLeft16Filled,
	Home48Filled,
	LineDashes20Regular,
	MailArrowDoubleBack16Regular,
	TabInPrivate16Filled,
	ChatHelp20Filled,
	EditOff20Filled,
	PanelRightContract16Regular,
	WeatherMoonOff24Regular,
	Dentist12Regular,
	Handshake16Filled,
	DeleteArrowBack16Regular,
	TableMoveLeft16Regular
} from "@vicons/fluent"
import {
	LogoWindows,
	EarthSharp,
	CaretForwardCircleSharp,
	GitBranchSharp,
	LogoEuro,
	EllipsisHorizontalSharp,
	PlayForward,
	FootstepsSharp,
	BagAddSharp,
	SendOutline,
	BackspaceSharp,
	BagCheck,
	BatteryDead,
	LogoAppleAppstore,
	RefreshCircleSharp,
	ShirtSharp,
	InvertModeOutline,
	PulseOutline,
	PawOutline,
	SwapHorizontal,
	PinOutline,
	CheckmarkDoneCircle,
	CloudOfflineSharp,
	CodeDownloadSharp,
	Barcode,
	CheckmarkDoneSharp,
	CaretUpSharp,
	LaptopOutline,
	LocationOutline,
	PlaySkipBackCircleOutline
} from "@vicons/ionicons5"
import {
	PinOffTwotone,
	CategoryFilled,
	MoneyRound,
	FiberSmartRecordRound,
	HourglassBottomTwotone,
	AddToDriveRound,
	LocalCarWashFilled,
	KeyboardArrowRightRound,
	MonitorHeartFilled,
	KeyboardOptionKeySharp,
	ChurchSharp,
	Md123Round,
	FilterTiltShiftTwotone,
	KeyboardArrowDownRound,
	VpnKeyRound,
	ShieldFilled,
	ExploreOffRound,
	SupportAgentRound,
	NotStartedTwotone,
	LocalOfferSharp,
	AudioFileFilled,
	ArrowForwardIosSharp,
	DoorBackFilled,
	AirlineSeatReclineNormalOutlined,
	CurrencyBitcoinTwotone,
	VideogameAssetOutlined,
	TocOutlined,
	Md7KOutlined,
	SensorsFilled,
	WifiProtectedSetupOutlined
} from "@vicons/material"
import {
	ArrowBigUpLine,
	FileDiff,
	Smoking,
	ArrowsDoubleSwNe,
	Atom,
	Messages,
	Space,
	Separator,
	Home,
	Stars,
	Trash,
	SquareForbid2,
	BellMinus,
	SoccerField,
	Ruler2,
	BrandOpera,
	PlaneArrival,
	FileMusic,
	Barbell,
	PictureInPicture,
	Anchor,
	Calendar,
	BoxMultiple3,
	CurrencyDollarAustralian,
	HandLittleFinger,
	LetterY,
	TrashX,
	HandOff,
	Pizza,
	AntennaBars5
} from "@vicons/tabler"
import { defineComponent } from "vue"

export default defineComponent({
	name: "Xicons",
	data: () => ({
		Carbon,
		Fa,
		Fluent,
		Ionicons5,
		Material,
		Tabler
	}),
	components: {
		NIcon,
		NCard,
		NButton,
		StringInteger,
		DocumentWordProcessorReference,
		CategoryNewEach,
		WarningAlt,
		Stethoscope,
		KeepDry,
		NoImage,
		GroupObjects,
		Information,
		Warning,
		AccessibilityAlt,
		VirtualColumnKey,
		OpenPanelFilledRight,
		DataBase,
		AlignVerticalTop,
		ConnectionSignal,
		ConnectionSend,
		PhoneIncomingFilled,
		TemperatureFahrenheitAlt,
		PhoneVoice,
		Network1,
		WintryMix,
		PlayFilled,
		MicrophoneOffFilled,
		FilterRemove,
		Moonset,
		AlignBoxMiddleRight,
		TaskTools,
		FaceWinkFilled,
		AlignBoxMiddleCenter,
		SortAlphaDown,
		Chrome,
		Envira,
		Shopware,
		Snapchat,
		CommentAlt,
		RedditAlien,
		Comment,
		Mailchimp,
		Bone,
		Quran,
		Download,
		Draft2Digital,
		Blackberry,
		Digg,
		Film,
		IdBadgeRegular,
		FileMedicalAlt,
		SortAlphaUpAlt,
		CodeBranch,
		MehRegular,
		DiceThree,
		Beer,
		Js,
		CottonBureau,
		CreativeCommonsShare,
		Vest,
		DiceFive,
		StoreAltSlash,
		Unlink,
		ChevronUp24Filled,
		SquareMultiple20Regular,
		PresenceUnknown10Regular,
		Gift20Regular,
		CheckmarkUnderlineCircle20Filled,
		ArrowFit16Regular,
		Fingerprint24Filled,
		TextClearFormatting16Regular,
		ReadingListAdd16Regular,
		DrinkCoffee20Filled,
		FolderLink20Filled,
		History24Filled,
		DataBarHorizontal20Regular,
		News28Regular,
		BookLetter24Filled,
		SportHockey24Regular,
		Oval32Regular,
		ArrowUpLeft16Filled,
		Home48Filled,
		LineDashes20Regular,
		MailArrowDoubleBack16Regular,
		TabInPrivate16Filled,
		ChatHelp20Filled,
		EditOff20Filled,
		PanelRightContract16Regular,
		WeatherMoonOff24Regular,
		Dentist12Regular,
		Handshake16Filled,
		DeleteArrowBack16Regular,
		TableMoveLeft16Regular,
		LogoWindows,
		EarthSharp,
		CaretForwardCircleSharp,
		GitBranchSharp,
		LogoEuro,
		EllipsisHorizontalSharp,
		PlayForward,
		FootstepsSharp,
		BagAddSharp,
		SendOutline,
		BackspaceSharp,
		BagCheck,
		BatteryDead,
		LogoAppleAppstore,
		RefreshCircleSharp,
		ShirtSharp,
		InvertModeOutline,
		PulseOutline,
		PawOutline,
		SwapHorizontal,
		PinOutline,
		CheckmarkDoneCircle,
		CloudOfflineSharp,
		CodeDownloadSharp,
		Barcode,
		CheckmarkDoneSharp,
		CaretUpSharp,
		LaptopOutline,
		LocationOutline,
		PlaySkipBackCircleOutline,
		PinOffTwotone,
		CategoryFilled,
		MoneyRound,
		FiberSmartRecordRound,
		HourglassBottomTwotone,
		AddToDriveRound,
		LocalCarWashFilled,
		KeyboardArrowRightRound,
		MonitorHeartFilled,
		KeyboardOptionKeySharp,
		ChurchSharp,
		Md123Round,
		FilterTiltShiftTwotone,
		KeyboardArrowDownRound,
		VpnKeyRound,
		ShieldFilled,
		ExploreOffRound,
		SupportAgentRound,
		NotStartedTwotone,
		LocalOfferSharp,
		AudioFileFilled,
		ArrowForwardIosSharp,
		DoorBackFilled,
		AirlineSeatReclineNormalOutlined,
		CurrencyBitcoinTwotone,
		VideogameAssetOutlined,
		TocOutlined,
		Md7KOutlined,
		SensorsFilled,
		WifiProtectedSetupOutlined,
		ArrowBigUpLine,
		FileDiff,
		Smoking,
		ArrowsDoubleSwNe,
		Atom,
		Messages,
		Space,
		Separator,
		Home,
		Stars,
		Trash,
		SquareForbid2,
		BellMinus,
		SoccerField,
		Ruler2,
		BrandOpera,
		PlaneArrival,
		FileMusic,
		Barbell,
		PictureInPicture,
		Anchor,
		Calendar,
		BoxMultiple3,
		CurrencyDollarAustralian,
		HandLittleFinger,
		LetterY,
		TrashX,
		HandOff,
		Pizza,
		AntennaBars5
	}
})
</script>

<style lang="scss" scoped>
.page {
	.main {
		.groups {
			grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));

			@media (max-width: 450px) {
				grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
			}
			.group {
				.list {
					margin-top: 10px;
					display: grid;
					gap: 12px;
					align-items: start;
					grid-template-columns: repeat(auto-fit, minmax(45px, 1fr));

					.icon-box {
						background-color: rgba(var(--bg-body-rgb), 0.5);
						border-radius: 10px;
						aspect-ratio: 1;
						display: flex;
						align-items: center;
						justify-content: center;
					}
				}
			}
		}
	}
}
</style>
