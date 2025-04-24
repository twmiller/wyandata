#!/usr/bin/env python3
"""
Script to completely reset the Django database and migrations
This will DELETE all data and migrations!
"""

import os
import shutil
import subprocess
from pathlib import Path

# Define the project root directory
BASE_DIR = Path(__file__).resolve().parent

def run_command(command, desc=None):
    """Run a shell command and print its output"""
    if desc:
        print(f"\n\033[1;34m>>> {desc}...\033[0m")
    print(f"\033[1;33m$ {command}\033[0m")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"\033[0;31m{result.stderr}\033[0m")
    return result.returncode

def main():
    # Confirm with user
    print("\033[1;31m!!!! WARNING !!!!\033[0m")
    print("This script will DELETE your entire database and ALL migrations.")
    print("ALL DATA WILL BE PERMANENTLY LOST!")
    confirm = input("\nType 'DELETE EVERYTHING' (all caps) to proceed: ")
    
    if confirm != "DELETE EVERYTHING":
        print("Operation cancelled.")
        return
    
    # Find all migration folders
    print("\n\033[1;34mFinding migration directories...\033[0m")
    apps_with_migrations = []
    for app_dir in [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]:
        migrations_dir = os.path.join(BASE_DIR, app_dir, 'migrations')
        if os.path.exists(migrations_dir):
            apps_with_migrations.append((app_dir, migrations_dir))
            print(f"Found migrations for app: {app_dir}")
    
    # Delete all migration files, keeping the __init__.py file
    print("\n\033[1;34mDeleting migration files...\033[0m")
    for app_name, migrations_dir in apps_with_migrations:
        for filename in os.listdir(migrations_dir):
            file_path = os.path.join(migrations_dir, filename)
            if filename != '__init__.py' and os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted: {file_path}")
    
    # Drop the database and recreate it
    if run_command("dropdb --if-exists wyandata", "Dropping database") == 0:
        print("\033[1;32m✓ Database dropped successfully\033[0m")
    
    if run_command("createdb wyandata -O wyanuser", "Creating new database") == 0:
        print("\033[1;32m✓ Database created successfully\033[0m")
    
    # Make new migrations
    if run_command("python manage.py makemigrations", "Creating new initial migrations") == 0:
        print("\033[1;32m✓ Created new migrations\033[0m")
    
    # Apply migrations
    if run_command("python manage.py migrate", "Applying migrations") == 0:
        print("\033[1;32m✓ Applied migrations successfully\033[0m")
    
    # Create superuser
    print("\n\033[1;34m>>> Creating a new superuser...\033[0m")
    os.system("python manage.py createsuperuser")
    
    print("\n\033[1;32m✓ Database reset complete! You're starting with a fresh database.\033[0m")

if __name__ == "__main__":
    main()
