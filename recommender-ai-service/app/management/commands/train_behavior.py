from django.core.management.base import BaseCommand
from app.ai_core.behavior_trainer import behavior_trainer
import time
import os
import pandas as pd

class Command(BaseCommand):
    help = 'Trains the behavior model using data from behavior_dataset.csv'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("[TRAINER] Starting AI Model Training Session..."))
        start_time = time.time()
        
        dataset_path = "app/ai_core/behavior_dataset.csv"
        
        # Check if CSV exists
        if not os.path.exists(dataset_path):
            self.stdout.write(self.style.ERROR(f"Error: Dataset file not found at {dataset_path}"))
            self.stdout.write(self.style.WARNING("Please run 'python manage.py export_behavior' first."))
            return

        # Load from CSV
        try:
            self.stdout.write(f"[TRAINER] Loading dataset from: {dataset_path}...")
            df = pd.read_csv(dataset_path)
            interactions = df.to_dict('records') # Converts to list of dicts with all 8 keys
            
            count = len(interactions)
            if count == 0:
                self.stdout.write(self.style.ERROR("Error: Dataset is empty!"))
                return
            
            self.stdout.write(self.style.SUCCESS(f"[TRAINER] Success! Loaded {count} interactions."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV: {e}"))
            return

        # Step 2: Training
        self.stdout.write(self.style.SUCCESS(f"[TRAINER] Step 1: Training Context-Aware Model with {count} records..."))
        success = behavior_trainer.train_epoch(interactions, epochs=10)
        
        if success:
            # Step 3: Saving
            self.stdout.write("[TRAINER] Step 2: Saving Model state to disk...")
            behavior_trainer.save()
            
            elapsed = time.time() - start_time
            self.stdout.write(self.style.SUCCESS(f"[TRAINER] 🏆 AI Brain updated successfully in {elapsed:.2f}s!"))
        else:
            self.stdout.write(self.style.ERROR("[TRAINER] ❌ Training failed. Check data format in CSV."))
