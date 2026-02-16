# import pandas as pd

# df = pd.read_csv("dives_with_conditions.csv")
# print(df)
# print("Rows:", len(df))
# print(df.isna().sum())

# import pandas as pd
# df = pd.read_csv("dives_with_conditions.csv")
# print(df)
# print(df.isna().sum())



# import sqlite3, pandas as pd
# conn = sqlite3.connect("visibility.db")
# df = pd.read_sql_query("SELECT tide_height FROM conditions", conn)
# print(df.head(20))


# import sqlite3

# conn = sqlite3.connect("visibility.db")
# cursor = conn.cursor()

# def add_column_if_missing(table, column, coltype):
#     # Check if column exists
#     cursor.execute(f"PRAGMA table_info({table})")
#     columns = [row[1] for row in cursor.fetchall()]

#     if column not in columns:
#         print(f"Adding column {column} to {table}")
#         cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
#     else:
#         print(f"Column {column} already exists in {table}")

# # Add your new dive fields
# add_column_if_missing("dives", "max_depth_m", "REAL")
# add_column_if_missing("dives", "breath_hold_s", "REAL")

# conn.commit()
# conn.close()

# print("Done.")



import sqlite3, pandas as pd
conn = sqlite3.connect("visibility.db")
df = pd.read_sql_query("SELECT tide_height FROM conditions", conn)
print(df.head(20))


