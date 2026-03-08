import pandas as pd
import sqlite3

# Read Excel file
data = pd.read_excel("Students_data.xlsx")

# Connect to SQLite database
conn = sqlite3.connect("students.db")

# Convert Excel data to SQLite table
data.to_sql("students", conn, if_exists="replace", index=False)

# Close connection
conn.close()

print("Excel data imported into SQLite successfully")