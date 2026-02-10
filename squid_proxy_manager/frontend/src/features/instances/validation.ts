import { z } from 'zod';

const proxyTypeEnum = z.enum(['squid', 'tls_tunnel']);

export const createInstanceSchema = z.object({
  name: z.string().min(1, 'Instance name is required').regex(/^[a-zA-Z0-9._-]+$/, {
    message: 'Use letters, numbers, dots, hyphens, or underscores'
  }),
  proxy_type: proxyTypeEnum.default('squid'),
  port: z.coerce.number().int().min(1024).max(65535),
  https_enabled: z.boolean().optional().default(false),
  dpi_prevention: z.boolean().optional().default(false),
  forward_address: z.string().optional(),
  cover_domain: z.string().optional(),
}).superRefine((data, ctx) => {
  if (data.proxy_type === 'tls_tunnel' && !data.forward_address) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'VPN server address is required for TLS Tunnel',
      path: ['forward_address'],
    });
  }
  if (data.forward_address && !/^[a-zA-Z0-9._-]+:\d{1,5}$/.test(data.forward_address)) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: 'Format: hostname:port (e.g., vpn.example.com:1194)',
      path: ['forward_address'],
    });
  }
});

export const userSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(6, 'Password must be at least 6 characters')
});

export const testCredentialsSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
  target_url: z
    .string()
    .optional()
    .refine((value) => value === undefined || value === '' || /^(https?:)\/\//.test(value), {
      message: 'Target URL must be a valid URL'
    })
});

export const updateInstanceSchema = z.object({
  port: z.coerce.number().int().min(1024).max(65535).optional(),
  https_enabled: z.boolean().optional(),
  dpi_prevention: z.boolean().optional(),
  forward_address: z.string().optional(),
  cover_domain: z.string().optional(),
});

export type CreateInstanceFormValues = z.infer<typeof createInstanceSchema>;
export type CreateInstanceFormInput = z.input<typeof createInstanceSchema>;
export type UpdateInstanceFormValues = z.infer<typeof updateInstanceSchema>;
export type UpdateInstanceFormInput = z.input<typeof updateInstanceSchema>;
export type UserFormValues = z.infer<typeof userSchema>;
export type TestCredentialsValues = z.infer<typeof testCredentialsSchema>;
