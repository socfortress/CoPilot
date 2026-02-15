import React from 'react';
import {
	AbsoluteFill,
	Img,
	interpolate,
	spring,
	staticFile,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';

const BG = '#0b0912';
const PRIMARY = '#f85d3b';
const ACCENT = '#884fff';

const Caption: React.FC<{title: string; body: string; color?: string}> = ({
	title,
	body,
	color = PRIMARY,
}) => {
	return (
		<div
			style={{
				position: 'absolute',
				left: 40,
				right: 40,
				bottom: 36,
				padding: '18px 18px 16px',
				borderRadius: 18,
				background: 'rgba(255,255,255,0.04)',
				border: '1px solid rgba(255,255,255,0.10)',
				backdropFilter: 'blur(10px)',
				fontFamily:
					'IBM Plex Sans, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial',
			}}
		>
			<div style={{fontSize: 20, fontWeight: 800, color: 'rgba(255,255,255,0.94)'}}>
				<span style={{color}}>{title}</span>
			</div>
			<div style={{marginTop: 6, fontSize: 15.5, lineHeight: 1.35, color: 'rgba(255,255,255,0.72)'}}>
				{body}
			</div>
		</div>
	);
};

const GlowBox: React.FC<{
	x: number;
	y: number;
	w: number;
	h: number;
	color: string;
	label?: string;
	progress: number;
}> = ({x, y, w, h, color, label, progress}) => {
	const opacity = interpolate(progress, [0, 1], [0, 1]);
	const scale = interpolate(progress, [0, 1], [0.98, 1]);
	return (
		<div
			style={{
				position: 'absolute',
				left: x,
				top: y,
				width: w,
				height: h,
				borderRadius: 18,
				border: `3px solid ${color}`,
				boxShadow: `0 0 18px ${color}88, 0 0 40px ${color}44`,
				opacity,
				transform: `scale(${scale})`,
			}}
		>
			{label ? (
				<div
					style={{
						position: 'absolute',
						left: 12,
						top: -34,
						padding: '6px 10px',
						borderRadius: 999,
						background: 'rgba(0,0,0,0.55)',
						border: `1px solid ${color}66`,
						color: 'rgba(255,255,255,0.92)',
						fontSize: 14,
						fontWeight: 700,
						backdropFilter: 'blur(6px)',
					}}
				>
					{label}
				</div>
			) : null}
		</div>
	);
};

const Slide: React.FC<{
	src: string;
	zoomFrom: number;
	zoomTo: number;
	offsetX?: number;
	offsetY?: number;
	from: number;
	to: number;
	children?: React.ReactNode;
}> = ({src, zoomFrom, zoomTo, offsetX = 0, offsetY = 0, from, to, children}) => {
	const frame = useCurrentFrame();
	const local = Math.min(Math.max(frame - from, 0), to - from);
	const dur = Math.max(1, to - from);
	const t = local / dur;
	const zoom = interpolate(t, [0, 1], [zoomFrom, zoomTo]);
	const fadeIn = interpolate(t, [0, 0.08], [0, 1]);
	const fadeOut = interpolate(t, [0.92, 1], [1, 0]);
	const opacity = Math.min(fadeIn, fadeOut);

	return (
		<AbsoluteFill style={{opacity}}>
			<AbsoluteFill
				style={{
					transform: `translate(${offsetX}px, ${offsetY}px) scale(${zoom})`,
					transformOrigin: '50% 50%',
				}}
			>
				<Img src={src} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
			</AbsoluteFill>
			{children}
		</AbsoluteFill>
	);
};

export const CustomerProvisioningWalkthrough: React.FC = () => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();

	// Frame ranges
	const s1 = {from: 0, to: 80};
	const s2 = {from: 80, to: 160};
	const s3 = {from: 160, to: 240};

	const p1 = spring({frame: frame - s1.from, fps, config: {damping: 18, stiffness: 120}});
	const p2 = spring({frame: frame - s2.from, fps, config: {damping: 18, stiffness: 120}});
	const p3 = spring({frame: frame - s3.from, fps, config: {damping: 18, stiffness: 120}});

	return (
		<AbsoluteFill style={{backgroundColor: BG}}>
			{/* Background glow */}
			<AbsoluteFill
				style={{
					background:
						`radial-gradient(900px 500px at 20% 30%, rgba(248,93,59,0.12), transparent 60%),` +
						`radial-gradient(900px 500px at 80% 70%, rgba(136,79,255,0.14), transparent 60%)`,
				}}
			/>

			{/* Slide 1: Customers list + Add Customer */}
			<Slide
				src={staticFile('ui/customers.png')}
				zoomFrom={1.0}
				zoomTo={1.08}
				offsetX={-40}
				offsetY={-10}
				from={s1.from}
				to={s1.to}
			>
				<GlowBox
					x={1180}
					y={120}
					w={350}
					h={90}
					color={PRIMARY}
					label="Add Customer"
					progress={p1}
				/>
				<Caption
					title="1) Create the Customer"
					body="Start in Customers and add a new customer. The customer code becomes the tenancy key used across provisioning and per-customer integrations."
					color={PRIMARY}
				/>
			</Slide>

			{/* Slide 2: Provision tab */}
			<Slide
				src={staticFile('ui/customer-tab-provision.png')}
				zoomFrom={1.0}
				zoomTo={1.06}
				offsetX={0}
				offsetY={-10}
				from={s2.from}
				to={s2.to}
			>
				<GlowBox
					x={170}
					y={155}
					w={190}
					h={70}
					color={ACCENT}
					label="Provision"
					progress={p2}
				/>
				<Caption
					title="2) Provision Tenancy (Wazuh + Graylog + Grafana)"
					body="Provisioning creates the customer’s dedicated index/stream routing, Wazuh agent groups, and Grafana org + default dashboards so data and visuals land correctly from day one."
					color={ACCENT}
				/>
			</Slide>

			{/* Slide 3: 3rd party integrations + network connectors */}
			<Slide
				src={staticFile('ui/customer-tab-3rd-party-integrations.png')}
				zoomFrom={1.0}
				zoomTo={1.04}
				offsetX={0}
				offsetY={-10}
				from={s3.from}
				to={s3.to}
			>
				<GlowBox
					x={290}
					y={155}
					w={300}
					h={70}
					color={PRIMARY}
					label="3rd Party Integrations"
					progress={p3}
				/>
				<GlowBox
					x={610}
					y={155}
					w={260}
					h={70}
					color={ACCENT}
					label="Network Connectors"
					progress={p3}
				/>

				{/* Show Network Connectors as a small inset preview */}
				<div
					style={{
						position: 'absolute',
						right: 44,
						top: 260,
						width: 520,
						borderRadius: 18,
						overflow: 'hidden',
						border: '1px solid rgba(255,255,255,0.10)',
						boxShadow: `0 0 28px ${ACCENT}33`,
						opacity: interpolate(p3, [0, 1], [0, 1]),
					}}
				>
					<Img
						src={staticFile('ui/customer-tab-network-connectors.png')}
						style={{width: '100%', height: '100%', objectFit: 'cover'}}
					/>
					<div
						style={{
							position: 'absolute',
							left: 14,
							top: 14,
							padding: '6px 10px',
							borderRadius: 999,
							background: 'rgba(0,0,0,0.55)',
							border: `1px solid ${ACCENT}66`,
							color: 'rgba(255,255,255,0.92)',
							fontSize: 14,
							fontWeight: 800,
							backdropFilter: 'blur(6px)',
						}}
					>
						Network Connectors
					</div>
				</div>

				<Caption
					title="3) Enable per-customer integrations"
					body="After provisioning, configure per-customer 3rd-party integrations (e.g., Office 365, Mimecast) and network connectors (firewalls/network devices). These are customer-scoped so data routes into the right tenant automatically."
					color={PRIMARY}
				/>
			</Slide>
		</AbsoluteFill>
	);
};
