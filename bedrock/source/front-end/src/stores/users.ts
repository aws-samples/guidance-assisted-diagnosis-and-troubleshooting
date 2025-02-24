import { IoTSiteWiseClient } from '@aws-sdk/client-iotsitewise';
import { IoTEventsClient } from '@aws-sdk/client-iot-events';
import { atom } from 'nanostores';
import type { User, AwsCredentials } from '../types';
import { isNotNil } from '../core/utils/lang2';
import { $client, resetClient } from './iotsitewise';
import { $eventsClient, resetEventClient } from './iotevents';


const EXPIRATION_CHECK_INTERVAL_IN_MS = 1000;
let authCheckInterval: NodeJS.Timeout;

export const $user = atom<User | null>(null);

export function resetUser() {
  $user.set(null);
}

// Check if the user credentials have expired and purge user if so
$user.listen((user) => {
  if (user?.awsCredentials) {
    authCheckInterval = setInterval(() => {
      if (!hasCredentials(user.awsCredentials)) {
        $user.set(null);
      }
    }, EXPIRATION_CHECK_INTERVAL_IN_MS);
  } else {
    clearInterval(authCheckInterval);
  }
});

// Initialize or dispose SitewiseClient and IoTEventsClient on user state change
$user.listen((user) => {
  if (user) {
    $client.set(
      new IoTSiteWiseClient({
        credentials: user.awsCredentials,
        region: user.awsCredentials.region,
      })
    );

    $eventsClient.set(
      new IoTEventsClient({
        credentials: user.awsCredentials,
        region: user.awsCredentials.region,
      })
    );

  } else {
    resetClient();
    resetEventClient();
  }
});

// Private methods
function hasCredentials(creds?: AwsCredentials | null): creds is Exclude<AwsCredentials, undefined> {
  return (
    isNotNil(creds) &&
    creds.expiration !== undefined &&  // Check that expiration exists
    creds.expiration.getTime() > Date.now()
  );
}