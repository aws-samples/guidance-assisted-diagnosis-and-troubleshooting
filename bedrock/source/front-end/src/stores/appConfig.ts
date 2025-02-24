import { atom } from 'nanostores';
import type { AppConfig } from '../types';

export const $appConfig = atom<AppConfig | null>(null);


