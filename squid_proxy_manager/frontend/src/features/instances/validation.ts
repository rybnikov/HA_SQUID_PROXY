import { z } from 'zod';

export const createInstanceSchema = z.object({
  name: z.string().min(1, 'Instance name is required').regex(/^[a-zA-Z0-9._-]+$/, {
    message: 'Use letters, numbers, dots, hyphens, or underscores'
  }),
  port: z.coerce.number().int().min(1024).max(65535),
  https_enabled: z.boolean(),
  dpi_prevention: z.boolean()
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

export const updateInstanceSchema = createInstanceSchema.omit({ name: true });

export type CreateInstanceFormValues = z.infer<typeof createInstanceSchema>;
export type CreateInstanceFormInput = z.input<typeof createInstanceSchema>;
export type UpdateInstanceFormValues = z.infer<typeof updateInstanceSchema>;
export type UpdateInstanceFormInput = z.input<typeof updateInstanceSchema>;
export type UserFormValues = z.infer<typeof userSchema>;
export type TestCredentialsValues = z.infer<typeof testCredentialsSchema>;
