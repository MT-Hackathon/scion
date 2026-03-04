// BLUEPRINT: theme.service
// STRUCTURAL: private signal + asReadonly() encapsulation, stored-preference ?? system-preference
//             fallback chain, overlay container synchronization for Material overlays,
//             try/catch isolation on every window API call
// ILLUSTRATIVE: STORAGE_KEY value, CSS class names ('dark-theme'/'light-theme'),
//               body as root target (swap documentElement if theme scoped to <html>)

import {DOCUMENT} from '@angular/common';
import {inject, Injectable, signal} from '@angular/core';
import {OverlayContainer} from '@angular/cdk/overlay';

@Injectable({providedIn: 'root'})
export class ThemeService {
  private static readonly STORAGE_KEY = 'app:theme:isDark'; // ILLUSTRATIVE: rename per project

  private readonly document = inject(DOCUMENT);
  private readonly overlay = inject(OverlayContainer, {optional: true});

  // STRUCTURAL: private write signal + public readonly — only this service mutates theme state
  private readonly _isDarkMode = signal<boolean>(false);
  readonly isDarkMode = this._isDarkMode.asReadonly();

  constructor() {
    // STRUCTURAL: stored preference wins; system preference is the fallback; false is the safe default
    const stored = this.readStoredPreference();
    const prefersDark = stored ?? this.getSystemPrefersDark();
    this.apply(prefersDark);
  }

  toggle(): void {
    const isDark = !this._isDarkMode();
    this.apply(isDark);
    this.storePreference(isDark);
  }

  private apply(isDark: boolean): void {
    this._isDarkMode.set(isDark);
    const root = this.document.body;
    if (!root) return;

    // ILLUSTRATIVE: class names — swap to match your global stylesheet selectors
    root.classList.toggle('dark-theme', isDark);
    root.classList.toggle('light-theme', !isDark);

    // STRUCTURAL: overlay container must mirror root classes so Material dialogs/menus follow the theme
    const overlayEl = this.overlay?.getContainerElement();
    if (overlayEl) {
      overlayEl.classList.toggle('dark-theme', isDark);
      overlayEl.classList.toggle('light-theme', !isDark);
    }
  }

  private getSystemPrefersDark(): boolean {
    // STRUCTURAL: try/catch required — matchMedia throws in SSR and some headless environments
    try {
      return !!window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    } catch {
      return false;
    }
  }

  private readStoredPreference(): boolean | null {
    try {
      const raw = window.localStorage.getItem(ThemeService.STORAGE_KEY);
      if (raw === null) return null;
      return raw === 'true';
    } catch {
      return null;
    }
  }

  private storePreference(isDark: boolean): void {
    try {
      window.localStorage.setItem(ThemeService.STORAGE_KEY, String(isDark));
    } catch {
      // ignore storage failures — preference not persisted, theme still applied
    }
  }
}
