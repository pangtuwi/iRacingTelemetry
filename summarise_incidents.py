import csv
import sys
from collections import defaultdict

def summarise(input_file):
    counts = defaultdict(lambda: {'DriverName': '', 'IncidentCount': 0})

    with open(input_file, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cust_id = row['CustID']
            counts[cust_id]['DriverName'] = row['DriverName']
            counts[cust_id]['IncidentCount'] += 1

    output_file = input_file.replace('.csv', '_summary.csv')
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['CustID', 'DriverName', 'IncidentCount'])
        for cust_id, data in sorted(counts.items(), key=lambda x: -x[1]['IncidentCount']):
            writer.writerow([cust_id, data['DriverName'], data['IncidentCount']])

    print(f"Written to {output_file}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python summarise_incidents.py <incidents_csv>")
        sys.exit(1)
    summarise(sys.argv[1])
