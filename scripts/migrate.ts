/**
 * Run raw SQL migrations from api/migrations/*.sql in order.
 * Uses SUPABASE_POSTGRES_URL from .env at project root.
 */
import { readFileSync, readdirSync } from "fs";
import { join } from "path";
import { config } from "dotenv";
import { Client } from "pg";

const root = process.cwd();
const migrationsDir = join(root, "migrations");

config({ path: join(root, ".env") });

const url = process.env.SUPABASE_POSTGRES_URL;
if (!url) {
  console.error(
    "SUPABASE_POSTGRES_URL is required; set it in .env at project root"
  );
  process.exit(1);
}

const client = new Client({ connectionString: url });

async function run() {
  await client.connect();

  await client.query(`
    CREATE TABLE IF NOT EXISTS _migrations (
      name TEXT PRIMARY KEY,
      run_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
  `);

  const files = readdirSync(migrationsDir)
    .filter((f) => f.endsWith(".sql"))
    .sort();

  for (const file of files) {
    const name = file;
    const { rows } = await client.query(
      "SELECT 1 FROM _migrations WHERE name = $1",
      [name]
    );
    if (rows.length > 0) {
      console.log("Skip (already applied):", name);
      continue;
    }

    const sql = readFileSync(join(migrationsDir, file), "utf-8");
    await client.query(sql);
    await client.query("INSERT INTO _migrations (name) VALUES ($1)", [name]);
    console.log("Applied:", name);
  }
}

run()
  .then(() => {
    client.end();
    process.exit(0);
  })
  .catch((err) => {
    console.error(err);
    client.end();
    process.exit(1);
  });
