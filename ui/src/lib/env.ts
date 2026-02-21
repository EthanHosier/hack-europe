import { z } from "zod";

const envSchema = z.object({
  VITE_MAPBOX_ACCESS_TOKEN: z.string().min(1).optional(),
});

const parsedEnv = envSchema.safeParse(import.meta.env);

if (!parsedEnv.success) {
  console.error("Invalid frontend env configuration", parsedEnv.error.flatten());
}

export const env = parsedEnv.success
  ? parsedEnv.data
  : {
      VITE_MAPBOX_ACCESS_TOKEN: undefined,
    };
