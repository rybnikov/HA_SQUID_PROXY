import 'react';
import type * as React from 'react';

declare module 'react' {
  namespace JSX {
    interface IntrinsicElements {
      'ha-switch': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        checked?: boolean;
        disabled?: boolean;
      };
      'ha-button': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        raised?: boolean;
        outlined?: boolean;
        disabled?: boolean;
        appearance?: 'accent' | 'outlined' | 'plain';
      };
      'ha-textfield': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        label?: string;
        type?: 'text' | 'number' | 'password' | 'email' | 'url';
        value?: string | number;
        name?: string;
        disabled?: boolean;
        required?: boolean;
        min?: string | number;
        max?: string | number;
        placeholder?: string;
        suffix?: string;
      };
      'ha-card': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        header?: string;
        outlined?: boolean;
      };
      'ha-integration-card': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        domain?: string;
      };
      'ha-form': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        disabled?: boolean;
        hass?: unknown;
      };
      'ha-dialog': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        open?: boolean;
        heading?: string;
        hideActions?: boolean;
      };
      'ha-wa-dialog': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        open?: boolean;
        'header-title'?: string;
        width?: string;
      };
      'ha-tab-group': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        placement?: 'top' | 'bottom' | 'start' | 'end';
      };
      'ha-tab-group-tab': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        active?: boolean;
        panel?: string;
      };
      'ha-tab': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        active?: boolean;
        name?: string;
        narrow?: boolean;
      };
      'ha-chip-set': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        type?: string;
      };
      'ha-chip': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        disabled?: boolean;
      };
      'ha-icon': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        icon?: string;
      };
      'ha-icon-button': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        disabled?: boolean;
      };
      'hui-tile-card': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        tabIndex?: number;
      };
      'ha-select': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        label?: string;
        value?: string;
        disabled?: boolean;
      };
      'mwc-list-item': React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        value?: string;
        selected?: boolean;
      };
    }
  }
}

export {};
