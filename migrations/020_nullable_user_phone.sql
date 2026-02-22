-- Make phone column nullable on user table
ALTER TABLE "user"
  ALTER COLUMN phone DROP NOT NULL;
