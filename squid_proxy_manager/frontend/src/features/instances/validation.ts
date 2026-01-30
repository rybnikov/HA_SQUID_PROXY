import { z } from 'zod';

export const certParamsSchema = z.object({
  common_name: z.string().optional(),
  validity_days: z.coerce.number().int().min(1).max(3650),
  key_size: z.coerce.number().int().min(2048)
});

export const createInstanceSchema = z
  .object({
    name: z.string().min(1, 'Instance name is required').regex(/^[a-zA-Z0-9._-]+$/, {
      message: 'Use letters, numbers, dots, hyphens, or underscores'
    }),
    port: z.coerce.number().int().min(1024).max(65535),
    https_enabled: z.boolean(),
    cert_params: certParamsSchema.optional()
  })
  .refine(
    (data) => (data.https_enabled ? data.cert_params?.common_name : true),
    { path: ['cert_params', 'common_name'], message: 'Certificate CN is required for HTTPS' }
  );

export const userSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(6, 'Password must be at least 6 characters')
});

export const testCredentialsSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required')
});

export const updateInstanceSchema = createInstanceSchema.omit({ name: true });

export type CreateInstanceFormValues = z.infer<typeof createInstanceSchema>;
export type CreateInstanceFormInput = z.input<typeof createInstanceSchema>;
export type UpdateInstanceFormValues = z.infer<typeof updateInstanceSchema>;
export type UpdateInstanceFormInput = z.input<typeof updateInstanceSchema>;
export type UserFormValues = z.infer<typeof userSchema>;
export type TestCredentialsValues = z.infer<typeof testCredentialsSchema>;
