import React from 'react';
import {Composition} from 'remotion';
import {CustomerProvisioningWalkthrough} from './scenes/CustomerProvisioningWalkthrough';

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition
				id="customer-provisioning-walkthrough"
				component={CustomerProvisioningWalkthrough}
				durationInFrames={240} // 8s @ 30fps
				fps={30}
				width={1600}
				height={900}
			/>
		</>
	);
};
