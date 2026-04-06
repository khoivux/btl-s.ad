from django.core.management.base import BaseCommand
from app.services.data_processing import data_processor
import time

class Command(BaseCommand):
    help = 'Fetches interaction data using DataProcessor and exports to behavior_dataset.csv'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("[EXPORTER] Starting Data Collection Session..."))
        start_time = time.time()
        
        # Call processor
        interactions = data_processor.fetch_raw_interactions()
        count = len(interactions)
        self.stdout.write(self.style.SUCCESS(f"[EXPORTER] Success! Found {count} total interactions."))

        # Export to CSV
        dataset_path = "app/ai_core/behavior_dataset.csv"
        data_processor.save_to_csv(interactions, dataset_path)

        elapsed = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f"[EXPORTER] 🏆 Export completed in {elapsed:.2f}s!"))
