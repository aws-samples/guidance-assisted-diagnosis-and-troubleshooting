

import { atom } from 'nanostores';
import { IoTEventsClient } from '@aws-sdk/client-iot-events';

export const $eventsClient = atom<IoTEventsClient | undefined>(undefined);

export function resetEventClient() {
    $eventsClient.set(undefined);
  }
