# Database Migration Instructions for MonthlyScheduleCache

This document contains the necessary `flask db` commands to update the database with the new `MonthlyScheduleCache` table.

As requested, these commands have not been run automatically. You will need to run them manually from your shell in the `backend` directory.

## Step 1: Generate the Migration Script

This command will scan the `models.py` file, detect the new `MonthlyScheduleCache` class, and generate a new migration script in the `migrations/versions` directory.

```bash
flask db migrate -m "Add MonthlyScheduleCache table"
```

## Step 2: Apply the Migration to the Database

This command will run the newly generated migration script, which will execute the `CREATE TABLE` SQL statement to add the `monthly_schedule_cache` table to your database.

```bash
flask db upgrade
```

After running these two commands, your database schema will be up-to-date with the new caching table.

---

# Database Migration Instructions for GuestProfile

This document contains the necessary `flask db` commands to update the database with the new `GuestProfile` table for the stateful guest user feature.

As requested, these commands have not been run automatically. You will need to run them manually from your shell in the `backend` directory.

## Step 1: Generate the Migration Script

This command will scan the `models.py` file, detect the new `GuestProfile` class, and generate a new migration script in the `migrations/versions` directory.

```bash
# Make sure your virtual environment is active
# From the 'backend' directory:
flask db migrate -m "Add GuestProfile model for stateful guest users"
```

## Step 2: Apply the Migration to the Database

This command will run the newly generated migration script, which will execute the `CREATE TABLE` SQL statement to add the `guest_profile` table to your database.

```bash
# From the 'backend' directory:
flask db upgrade
```

After running these two commands, your database schema will be up-to-date with the new guest profile table.
