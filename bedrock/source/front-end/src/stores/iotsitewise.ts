

import { atom } from 'nanostores';
import { IoTSiteWiseClient } from '@aws-sdk/client-iotsitewise';

export const $client = atom<IoTSiteWiseClient | null>(null);

export function resetClient() {
    $client.set(null);
  }
