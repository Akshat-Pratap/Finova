"""Finova — Database Seeder Script."""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from app.core.database import connect_db, get_db
    from app.services.workflow_controller import WorkflowController

    print("Connecting to MongoDB...")
    await connect_db()
    db = get_db()

    print("Running synthetic reconciliation (250 records)...")
    controller = WorkflowController(db)
    run, results, analytics = await controller.run_synthetic(num_records=250, seed=42)

    print(f"Seeded database:")
    print(f"  Run ID:       {run.run_id}")
    print(f"  Processed:    {run.records_valid}")
    print(f"  Matched:      {run.records_matched}")
    print(f"  Match rate:   {run.match_rate*100:.1f}%")
    print(f"  Exceptions:   {analytics.get('exception_count', 0)}")


if __name__ == "__main__":
    asyncio.run(main())
