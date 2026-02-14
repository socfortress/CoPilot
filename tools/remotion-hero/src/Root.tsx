import React from 'react';
import {Composition} from 'remotion';
import {HubSpoke} from './scenes/HubSpoke';

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition
				id="copilot-hub"
				component={HubSpoke}
				durationInFrames={180} // 6s @ 30fps
				fps={30}
				width={1600}
				height={600}
			/>
		</>
	);
};
