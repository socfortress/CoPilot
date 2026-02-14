import React, {useMemo} from 'react';
import {
	AbsoluteFill,
	interpolate,
	random,
	spring,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';
import {
	Database,
	Gauge,
	GitBranch,
	LayoutDashboard,
	Logs,
	Server,
	ShieldCheck,
} from 'lucide-react';

type NodeSpec = {
	id: string;
	label: string;
	Icon: React.FC<{size?: number; color?: string}>;
	angleDeg: number;
};

const BG = '#0b0912';
const PRIMARY = '#f85d3b';
const ACCENT = '#884fff';

const NodeCard: React.FC<{
	cx: number;
	cy: number;
	label: string;
	Icon: NodeSpec['Icon'];
	accent: string;
	appear: number;
}> = ({cx, cy, label, Icon, accent, appear}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const s = spring({frame, fps, config: {damping: 14, mass: 0.8, stiffness: 120}});
	const scale = interpolate(s, [0, 1], [0.92, 1]) * appear;
	const opacity = interpolate(s, [0, 1], [0, 1]) * appear;

	return (
		<div
			style={{
				position: 'absolute',
				left: cx,
				top: cy,
				transform: `translate(-50%, -50%) scale(${scale})`,
				opacity,
				width: 180,
				padding: '14px 14px 12px',
				borderRadius: 16,
				background: 'rgba(255,255,255,0.03)',
				border: '1px solid rgba(255,255,255,0.08)',
				backdropFilter: 'blur(8px)',
				boxShadow: `0 0 24px rgba(136,79,255,0.08)`,
				textAlign: 'center',
				fontFamily:
					'IBM Plex Sans, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial',
			}}
		>
			<div
				style={{
					display: 'inline-flex',
					alignItems: 'center',
					justifyContent: 'center',
					width: 58,
					height: 58,
					borderRadius: 18,
					background: 'rgba(255,255,255,0.02)',
					border: `1px solid rgba(255,255,255,0.10)`,
					boxShadow: `0 0 18px ${accent}33`,
				}}
			>
				<Icon size={30} color={accent} />
			</div>
			<div style={{marginTop: 10, fontSize: 16, fontWeight: 600, color: 'rgba(255,255,255,0.92)'}}>
				{label}
			</div>
		</div>
	);
};

const Stream: React.FC<{
	x1: number;
	y1: number;
	x2: number;
	y2: number;
	color: string;
	seed: number;
}> = ({x1, y1, x2, y2, color, seed}) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();

	// Dotted stream
	const dash = 10;
	const gap = 8;
	const speed = 2.0 + random(seed) * 1.4;
	const offset = (frame * speed) % (dash + gap);

	// Occasional packet pulse (repeatable)
	const t = (frame + Math.floor(random(seed + 1) * 60)) % durationInFrames;
	const pulseEvery = 45 + Math.floor(random(seed + 2) * 35);
	const pulsePhase = t % pulseEvery;
	const pulseT = pulsePhase / pulseEvery;
	const packetVisible = pulsePhase < 18;

	// Quadratic curve control point (bend outward)
	const mx = (x1 + x2) / 2;
	const my = (y1 + y2) / 2;
	const bend = 80;
	const cx = mx + (my - 300) * 0.15;
	const cy = my - bend;

	const path = `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;

	// Packet position along curve (approx via linear interpolation on t; fine for small effect)
	const px = x1 + (x2 - x1) * pulseT;
	const py = y1 + (y2 - y1) * pulseT;

	return (
		<svg
			style={{
				position: 'absolute',
				left: 0,
				top: 0,
				width: '100%',
				height: '100%',
				overflow: 'visible',
			}}
		>
			<path
				d={path}
				fill="none"
				stroke={color}
				strokeWidth={2.2}
				strokeDasharray={`${dash} ${gap}`}
				strokeDashoffset={-offset}
				opacity={0.45}
				style={{
					filter: `drop-shadow(0 0 10px ${color}55) drop-shadow(0 0 18px ${color}33)`,
				}}
			/>
			{packetVisible ? (
				<circle
					cx={px}
					cy={py}
					r={4.2}
					fill={color}
					opacity={0.9}
					style={{filter: `drop-shadow(0 0 14px ${color})`}}
				/>
			) : null}
		</svg>
	);
};

export const HubSpoke: React.FC = () => {
	const frame = useCurrentFrame();
	const {fps, durationInFrames, width, height} = useVideoConfig();

	const center = {x: width / 2, y: height / 2};
	const radius = 210;

	const nodes: NodeSpec[] = useMemo(
		() => [
			{ id: 'wazuh-manager', label: 'Wazuh Manager', Icon: Server, angleDeg: -90 },
			{ id: 'wazuh-indexer', label: 'Wazuh Indexer', Icon: Database, angleDeg: -30 },
			{ id: 'graylog', label: 'Graylog', Icon: Logs, angleDeg: 30 },
			{ id: 'grafana', label: 'Grafana', Icon: Gauge, angleDeg: 90 },
			{ id: 'shuffle', label: 'Shuffle', Icon: GitBranch, angleDeg: 150 },
			{ id: 'velociraptor', label: 'Velociraptor', Icon: LayoutDashboard, angleDeg: 210 },
		],
		[]
	);

	const appear = spring({frame, fps, config: {damping: 16, stiffness: 120, mass: 0.9}});

	const hubPulse = 0.5 + 0.5 * Math.sin((frame / durationInFrames) * Math.PI * 2);
	const hubGlow = interpolate(hubPulse, [0, 1], [0.25, 0.6]);

	return (
		<AbsoluteFill
			style={{
				backgroundColor: BG,
				overflow: 'hidden',
			}}
		>
			{/* Background: subtle grid + gradient */}
			<AbsoluteFill
				style={{
					background:
						`radial-gradient(900px 380px at 50% 30%, rgba(136,79,255,0.18), transparent 60%),` +
						`radial-gradient(700px 420px at 70% 70%, rgba(248,93,59,0.12), transparent 55%),` +
						`linear-gradient(180deg, rgba(255,255,255,0.02), transparent 40%)`,
				}}
			/>
			<AbsoluteFill
				style={{
					backgroundImage:
						'linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)',
					backgroundSize: '56px 56px',
					opacity: 0.10,
					transform: `translateY(${interpolate(
						(frame % durationInFrames) / durationInFrames,
						[0, 1],
						[0, -56]
					)}px)`,
				}}
			/>

			{/* Streams */}
			{nodes.map((n, idx) => {
				const a = (n.angleDeg * Math.PI) / 180;
				const x = center.x + Math.cos(a) * radius;
				const y = center.y + Math.sin(a) * radius;
				const color = idx % 2 === 0 ? PRIMARY : ACCENT;
				return (
					<Stream
						key={n.id}
						x1={x}
						y1={y}
						x2={center.x}
						y2={center.y}
						color={color}
						seed={idx + 10}
					/>
				);
			})}

			{/* Hub */}
			<div
				style={{
					position: 'absolute',
					left: center.x,
					top: center.y,
					transform: `translate(-50%, -50%) scale(${0.98 + appear * 0.02})`,
					width: 320,
					padding: '22px 18px 18px',
					borderRadius: 22,
					background: 'rgba(255,255,255,0.04)',
					border: '1px solid rgba(255,255,255,0.10)',
					textAlign: 'center',
					boxShadow: `0 0 35px rgba(248,93,59,${hubGlow}), 0 0 55px rgba(136,79,255,0.18)`,
					backdropFilter: 'blur(10px)',
					fontFamily:
						'IBM Plex Sans, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial',
				}}
			>
				<div
					style={{
						display: 'inline-flex',
						alignItems: 'center',
						justifyContent: 'center',
						width: 76,
						height: 76,
						borderRadius: 22,
						background: 'rgba(255,255,255,0.02)',
						border: '1px solid rgba(255,255,255,0.12)',
						boxShadow: `0 0 22px ${PRIMARY}55`,
					}}
				>
					<ShieldCheck size={38} color={PRIMARY} />
				</div>
				<div
					style={{
						marginTop: 12,
						fontSize: 22,
						fontWeight: 700,
						color: 'rgba(255,255,255,0.94)',
						letterSpacing: 0.2,
					}}
				>
					SOCFortress CoPilot
				</div>
				<div
					style={{
						marginTop: 6,
						fontSize: 15,
						color: 'rgba(255,255,255,0.70)',
					}}
				>
					Connect • Enrich • Automate
				</div>
			</div>

			{/* Outer nodes */}
			{nodes.map((n, idx) => {
				const a = (n.angleDeg * Math.PI) / 180;
				const x = center.x + Math.cos(a) * radius;
				const y = center.y + Math.sin(a) * radius;
				const accent = idx % 2 === 0 ? PRIMARY : ACCENT;
				return (
					<NodeCard
						key={n.id}
						cx={x}
						cy={y}
						label={n.label}
						Icon={n.Icon}
						accent={accent}
						appear={appear}
					/>
				);
			})}

			{/* Subtle vignette */}
			<AbsoluteFill
				style={{
					background:
						'radial-gradient(circle at 50% 50%, transparent 40%, rgba(0,0,0,0.55) 85%)',
					opacity: 0.55,
				}}
			/>
		</AbsoluteFill>
	);
};
