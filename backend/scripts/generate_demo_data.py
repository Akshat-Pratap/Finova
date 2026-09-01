"""Finova — Generate Demo Data Script."""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.data_generator import generate_dataset, dataset_to_dicts


def main():
    num = int(sys.argv[1]) if len(sys.argv) > 1 else 250
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 42

    print(f"Generating {num} records (seed={seed})...")
    txns, invs, banks, settlements = generate_dataset(num_records=num, seed=seed)
    data = dataset_to_dicts(txns, invs, banks, settlements)

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "data", "synthetic")
    os.makedirs(out_dir, exist_ok=True)

    output_path = os.path.join(out_dir, f"demo_{num}_{seed}.json")
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Generated:")
    print(f"  Transactions:      {len(data['transactions'])}")
    print(f"  Invoices:          {len(data['invoices'])}")
    print(f"  Bank Transactions: {len(data['bank_transactions'])}")
    print(f"  Settlements:       {len(data['settlements'])}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    main()
